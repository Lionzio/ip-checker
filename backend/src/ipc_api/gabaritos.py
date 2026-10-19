"""Gabaritos oficiais na memória da API (ADR-11, NFR-27; S32-02).

Ao subir, a API baixa os gabaritos do repositório privado (ADR-10) pela API do GitHub, por HTTPS,
com uma credencial só de leitura restrita a esse repositório (``IPC_GABARITOS_REPO`` e
``IPC_GABARITOS_TOKEN``), e os guarda **só na memória do processo**: nunca em disco, na imagem, no
log, na telemetria ou numa resposta. No desenvolvimento, ``IPC_GABARITOS_DIR`` lê uma pasta local
com a mesma organização (o clone do repositório, ou gabaritos sintéticos nos testes).

Só entram arquivos ``<período>/lista-<n>/L<n>-Q<m>.py``, com limites por arquivo e no total. Sem
configuração, ou com qualquer falha, a comparação fica desligada, a página avisa e o resto da API
segue normal: ``/ready`` não depende dos gabaritos. Os logs dizem só quantos arquivos entraram, ou o
tipo da falha, nunca um caminho, um trecho ou a credencial.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import httpx2

logger = logging.getLogger(__name__)

PATH = re.compile(
    r"^(?P<period>\d{4}\.[12])/lista-(?P<list>[1-6])/(?P<question>L(?P=list)-Q[1-9]\d?)\.py$"
)
#: O mesmo limite de uma submissão (50 KB).
MAX_FILE_BYTES = 51_200
MAX_TOTAL_BYTES = 5 * 1024 * 1024
MAX_FILES = 1_000
#: Downloads de arquivos ao mesmo tempo.
CONCURRENCY = 8

Status = Literal["disabled", "loading", "loaded", "failed"]


@dataclass(frozen=True, slots=True)
class GabaritosConfig:
    repo: str | None = None
    token: str | None = field(default=None, repr=False)
    branch: str = "main"
    local_dir: Path | None = None
    api_url: str = "https://api.github.com"
    timeout_s: float = 20.0
    #: Alerta de possível vazamento no plágio (ADR-11, item 5): A com B, A com o gabarito e B com o
    #: gabarito acima disto [PREMISSA: 95%, calibrado na S33-02] ...
    alert_percent: float = 95.0
    #: ... e os dois códigos com pelo menos estes tokens normalizados [PREMISSA: o mesmo limite do
    #: aviso de código curto do plágio].
    alert_min_tokens: int = 60

    @property
    def enabled(self) -> bool:
        return self.local_dir is not None or (bool(self.repo) and bool(self.token))

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> GabaritosConfig:
        defaults = cls()
        repo = env.get("IPC_GABARITOS_REPO") or None
        if repo is not None and not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            raise ValueError(f"IPC_GABARITOS_REPO inválida: {repo!r}. Use dono/repositório.")
        local = env.get("IPC_GABARITOS_DIR") or None
        return cls(
            repo=repo,
            token=env.get("IPC_GABARITOS_TOKEN") or None,
            branch=env.get("IPC_GABARITOS_BRANCH") or defaults.branch,
            local_dir=Path(local) if local else None,
            alert_percent=float(env.get("IPC_GABARITO_ALERT_PERCENT", defaults.alert_percent)),
            alert_min_tokens=int(
                env.get("IPC_GABARITO_ALERT_MIN_TOKENS", defaults.alert_min_tokens)
            ),
        )


class GabaritoLoadError(Exception):
    """Falha ao carregar; a mensagem nunca traz conteúdo, caminho de gabarito nem credencial."""


#: Os tipos de gabarito, na ordem de preferência quando só um vale (Sprint 51, ADR-17).
KIND_PREFERENCE = ("notion", "ip_cc")


@dataclass(slots=True)
class Gabaritos:
    """Os gabaritos carregados, por período e questão. Começa vazio ("loading" ou "disabled").

    Desde a Sprint 51, cada questão tem até dois gabaritos, "notion" e "ip_cc" (``pair``); ``get``
    devolve o preferido, para quem compara com um só. O repositório antigo entra como "notion".
    """

    status: Status = "disabled"
    _items: dict[tuple[str, str], str] = field(default_factory=dict, repr=False)
    _kinds: dict[tuple[str, str], dict[str, str]] = field(default_factory=dict, repr=False)

    @property
    def count(self) -> int:
        return len(self._items)

    def get(self, period: str, question_id: str) -> str | None:
        return self._items.get((period, question_id))

    def questions(self, period: str) -> dict[int, list[str]]:
        """As questões do período que têm gabarito, por lista, na ordem da numeração."""
        found: dict[int, list[str]] = {}
        for item_period, question in self._items:
            if item_period == period:
                found.setdefault(int(question[1]), []).append(question)
        return {
            number: sorted(ids, key=lambda q: int(q.split("Q")[1]))
            for number, ids in sorted(found.items())
        }

    def pair(self, period: str, question_id: str) -> tuple[tuple[str, str], ...]:
        """Os gabaritos da questão, como ``(tipo, código)``, o Notion antes do IP CC."""
        key = (period, question_id)
        kinds = self._kinds.get(key)
        if kinds is None:
            code = self._items.get(key)
            return () if code is None else (("notion", code),)
        return tuple((kind, kinds[kind]) for kind in KIND_PREFERENCE if kind in kinds)

    def put(self, period: str, question_id: str, kind: str, code: str) -> None:
        """Um gabarito salvo pelo painel (Sprint 51): a verificação seguinte já o usa."""
        key = (period, question_id)
        self._kinds.setdefault(key, dict(self.pair(period, question_id)))[kind] = code
        self._refresh(key)
        self.status = "loaded"

    def remove(self, period: str, question_id: str, kind: str) -> None:
        key = (period, question_id)
        self._kinds.setdefault(key, dict(self.pair(period, question_id))).pop(kind, None)
        self._refresh(key)

    def _refresh(self, key: tuple[str, str]) -> None:
        kinds = self._kinds.get(key) or {}
        preferred = next((kinds[k] for k in KIND_PREFERENCE if k in kinds), None)
        if preferred is None:
            self._items.pop(key, None)
            self._kinds.pop(key, None)
        else:
            self._items[key] = preferred

    def replace(self, items: dict[tuple[str, str], str]) -> None:
        self._items = items
        self._kinds = {}
        self.status = "loaded"


async def load(
    config: GabaritosConfig,
    target: Gabaritos,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> None:
    """Carrega os gabaritos em ``target``; nunca levanta exceção (a API sobe de qualquer jeito)."""
    if not config.enabled:
        target.status = "disabled"
        return
    target.status = "loading"
    try:
        if config.local_dir is not None:
            items = _from_dir(config.local_dir)
        else:
            items = await _from_github(config, transport)
    except GabaritoLoadError as exc:
        target.status = "failed"
        logger.warning("gabaritos indisponíveis: %s", exc)
        return
    target.replace(items)
    logger.info("gabaritos carregados: %d", len(items))


def _from_dir(root: Path) -> dict[tuple[str, str], str]:
    if not root.is_dir():
        raise GabaritoLoadError("IPC_GABARITOS_DIR não é uma pasta")
    accepted: list[tuple[str, bytes]] = []
    for file in sorted(root.rglob("*.py")):
        relative = file.relative_to(root).as_posix()
        if PATH.fullmatch(relative) is None:
            continue
        try:
            raw = file.read_bytes()
        except OSError:
            raise GabaritoLoadError("não foi possível ler a pasta dos gabaritos") from None
        accepted.append((relative, raw))
    return _index(accepted)


async def _from_github(
    config: GabaritosConfig, transport: httpx2.AsyncBaseTransport | None
) -> dict[tuple[str, str], str]:
    headers = {
        "Authorization": f"Bearer {config.token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx2.AsyncClient(
        base_url=config.api_url,
        headers=headers,
        timeout=httpx2.Timeout(config.timeout_s),
        transport=transport,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        tree = await _json(client, f"/repos/{config.repo}/git/trees/{config.branch}?recursive=1")
        entries = tree.get("tree") if isinstance(tree, dict) else None
        if not isinstance(entries, list):
            raise GabaritoLoadError("resposta inesperada do GitHub (árvore)")
        wanted = [
            (str(entry["path"]), str(entry["sha"]))
            for entry in entries
            if isinstance(entry, dict)
            and entry.get("type") == "blob"
            and isinstance(entry.get("path"), str)
            and PATH.fullmatch(entry["path"]) is not None
            and int(entry.get("size") or 0) <= MAX_FILE_BYTES
        ]
        if len(wanted) > MAX_FILES:
            raise GabaritoLoadError(f"mais de {MAX_FILES} gabaritos")
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def blob(path: str, sha: str) -> tuple[str, bytes]:
            async with semaphore:
                data = await _json(client, f"/repos/{config.repo}/git/blobs/{sha}")
            if not isinstance(data, dict) or data.get("encoding") != "base64":
                raise GabaritoLoadError("resposta inesperada do GitHub (arquivo)")
            try:
                return path, base64.b64decode(str(data.get("content", "")))
            except (binascii.Error, ValueError):
                raise GabaritoLoadError("arquivo do GitHub em base64 inválido") from None

        accepted = await asyncio.gather(*(blob(path, sha) for path, sha in wanted))
    return _index(list(accepted))


async def _json(client: httpx2.AsyncClient, path: str) -> Any:
    try:
        response = await client.get(path)
    except httpx2.HTTPError as exc:
        raise GabaritoLoadError(f"falha ao falar com o GitHub: {type(exc).__name__}") from None
    if response.status_code != 200:
        raise GabaritoLoadError(f"o GitHub respondeu {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise GabaritoLoadError("resposta do GitHub que não é JSON") from None


def _index(files: list[tuple[str, bytes]]) -> dict[tuple[str, str], str]:
    items: dict[tuple[str, str], str] = {}
    total = 0
    for path, raw in files:
        match = PATH.fullmatch(path)
        if match is None or len(raw) > MAX_FILE_BYTES:
            continue
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise GabaritoLoadError("os gabaritos passam do limite total")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue
        items[(match["period"], match["question"])] = text
    return items
