"""Gabaritos oficiais na memória da API (ADR-11, NFR-27; S32-02, revisto na Sprint 51).

Desde a Sprint 51 (ADR-17), o banco é a fonte da verdade: a chefia cadastra os gabaritos pela tela
"Gabaritos" (``ipc_api.answer_keys``), e a API os carrega do banco ao subir e a cada escrita. A
API não baixa mais nada do GitHub: ``IPC_GABARITOS_REPO`` e ``IPC_GABARITOS_TOKEN`` são ignoradas,
com um aviso no log, até saírem do Render. ``IPC_GABARITOS_DIR`` continua lendo uma pasta local com
a organização ``<período>/lista-<n>/L<n>-Q<m>.py``: no desenvolvimento, no compose do e2e e no
import dos gabaritos para o banco (``python -m ipc_api.answer_keys.transfer``).

Os gabaritos ficam **só na memória do processo** e no banco: nunca em disco, na imagem, no log, na
telemetria ou numa resposta ao monitor. Sem gabarito nenhum, a comparação fica desligada, a página
avisa e o resto da API segue normal: ``/ready`` não depende dos gabaritos. Os logs dizem só quantos
entraram, ou o tipo da falha, nunca um caminho, um trecho ou uma credencial.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

PATH = re.compile(
    r"^(?P<period>\d{4}\.[12])/lista-(?P<list>[1-6])/(?P<question>L(?P=list)-Q[1-9]\d?)\.py$"
)
#: O mesmo limite de uma submissão (50 KB).
MAX_FILE_BYTES = 51_200
MAX_TOTAL_BYTES = 5 * 1024 * 1024
MAX_FILES = 1_000

Status = Literal["disabled", "loading", "loaded", "failed"]

#: As variáveis do repositório de gabaritos, lidas até a Sprint 50 (ADR-10).
LEGACY_VARIABLES = ("IPC_GABARITOS_REPO", "IPC_GABARITOS_TOKEN", "IPC_GABARITOS_BRANCH")


@dataclass(frozen=True, slots=True)
class GabaritosConfig:
    local_dir: Path | None = None
    #: Alerta de possível vazamento no plágio (ADR-11, item 5): A com B, A com o gabarito e B com o
    #: gabarito acima disto [PREMISSA: 95%, calibrado na S33-02] ...
    alert_percent: float = 95.0
    #: ... e os dois códigos com pelo menos estes tokens normalizados [PREMISSA: o mesmo limite do
    #: aviso de código curto do plágio].
    alert_min_tokens: int = 60
    #: Alguma variável do repositório antigo ainda está definida (no Render, até o autor tirar).
    legacy_variables: bool = False

    @property
    def enabled(self) -> bool:
        return self.local_dir is not None

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> GabaritosConfig:
        defaults = cls()
        local = env.get("IPC_GABARITOS_DIR") or None
        return cls(
            local_dir=Path(local) if local else None,
            alert_percent=float(env.get("IPC_GABARITO_ALERT_PERCENT", defaults.alert_percent)),
            alert_min_tokens=int(
                env.get("IPC_GABARITO_ALERT_MIN_TOKENS", defaults.alert_min_tokens)
            ),
            legacy_variables=any(env.get(name) for name in LEGACY_VARIABLES),
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


async def load(config: GabaritosConfig, target: Gabaritos) -> None:
    """Carrega a pasta local em ``target``; nunca levanta exceção (a API sobe de qualquer jeito)."""
    if config.legacy_variables:
        logger.warning(
            "IPC_GABARITOS_REPO e IPC_GABARITOS_TOKEN não são mais lidas (Sprint 51): os gabaritos "
            "vêm do banco; tire as variáveis do Render e revogue o token (runbook)"
        )
    if not config.enabled:
        target.status = "disabled"
        return
    target.status = "loading"
    try:
        items = read_folder(config.local_dir)  # type: ignore[arg-type]
    except GabaritoLoadError as exc:
        target.status = "failed"
        logger.warning("gabaritos indisponíveis: %s", exc)
        return
    target.replace(items)
    logger.info("gabaritos carregados: %d", len(items))


def read_folder(root: Path) -> dict[tuple[str, str], str]:
    """Os gabaritos de uma pasta ``<período>/lista-<n>/L<n>-Q<m>.py``, com os limites de sempre:
    o carregamento local e o import para o banco (Sprint 51) leem do mesmo jeito."""
    if not root.is_dir():
        raise GabaritoLoadError("a pasta dos gabaritos não existe")
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
    if len(accepted) > MAX_FILES:
        raise GabaritoLoadError(f"mais de {MAX_FILES} gabaritos")
    return _index(accepted)


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
