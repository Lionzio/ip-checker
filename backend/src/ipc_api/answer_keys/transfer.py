"""Import e export dos gabaritos entre uma pasta e o banco (Sprint 51, S51-05; ADR-17).

``importar`` leva os gabaritos de uma pasta ``<período>/lista-<n>/L<n>-Q<m>.py`` (o repositório
antigo, ``ip-checker-gabaritos``) para o banco, como "Notion" e com a origem "importado". É
idempotente: um gabarito igual ao do banco não muda nada; um diferente reescreve e entra na
auditoria. As regras acionadas ficam vazias: estes gabaritos já passam no harness "zero violação"
da CI, e a API não pode rodar o analisador aqui (as fronteiras do ``lint-imports``). A tela os
mostra como "importado", e salvar de novo pelo painel os confere.

``exportar`` gera a mesma árvore a partir do banco, um arquivo por questão (o Notion quando há,
senão o IP CC), para o harness da CI. Ele recusa escrever dentro do repositório do IP-Checker:
um gabarito no histórico do Git não sai mais (P-13, ADR-10).

Rodados pelo autor, com a credencial de administrador digitada no terminal::

    IPC_DATABASE_ADMIN_URL=postgresql://... python -m ipc_api.answer_keys.transfer importar \\
        ../../ip-checker-gabaritos --periodo 2026.2
    IPC_DATABASE_ADMIN_URL=postgresql://... python -m ipc_api.answer_keys.transfer exportar \\
        ../../gabaritos-exportados

A saída traz só contagens, nunca código, caminho de gabarito ou credencial.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ipc_api.answer_keys.models import GABARITO_KINDS, QUESTION_ID, StoredGabarito
from ipc_api.answer_keys.store import Actor, GabaritoStore
from ipc_api.gabaritos import GabaritoLoadError, read_folder

#: A raiz do repositório do IP-Checker (backend/src/ipc_api/answer_keys/transfer.py).
REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(slots=True)
class ImportCounts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


async def import_folder(
    store: GabaritoStore,
    folder: Path,
    *,
    period: str | None = None,
    now: datetime | None = None,
) -> ImportCounts:
    """Os gabaritos da pasta entram no banco como "Notion", origem "importado"."""
    counts = ImportCounts()
    moment = now or datetime.now(UTC)
    for (item_period, question_id), code in sorted(read_folder(folder).items()):
        if period is not None and item_period != period:
            continue
        current = await store.get(item_period, question_id, "notion")
        if current is not None and current.code == code:
            counts.unchanged += 1
            continue
        await store.save(
            period=item_period,
            question_id=question_id,
            kind="notion",
            source="importado",
            code=code,
            violations=(),
            actor=Actor(None, None),
            now=moment,
        )
        if current is None:
            counts.created += 1
        else:
            counts.updated += 1
    return counts


def preferred(items: Sequence[StoredGabarito]) -> dict[tuple[str, str], StoredGabarito]:
    """Um gabarito por questão: o Notion quando há, senão o IP CC."""
    chosen: dict[tuple[str, str], StoredGabarito] = {}
    for item in sorted(items, key=lambda g: GABARITO_KINDS.index(g.kind)):
        chosen.setdefault((item.period, item.question_id), item)
    return chosen


def inside_repository(destination: Path) -> bool:
    resolved = destination.resolve()
    return resolved == REPO_ROOT or REPO_ROOT in resolved.parents


async def export_tree(store: GabaritoStore, destination: Path, *, period: str | None = None) -> int:
    """Grava ``<destino>/<período>/lista-<n>/L<n>-Q<m>.py``; devolve quantos arquivos."""
    if inside_repository(destination):
        raise ValueError(
            "o destino fica dentro do repositório do IP-Checker: os gabaritos nunca entram nele"
        )
    written = 0
    for (item_period, question_id), item in sorted(preferred(await store.all()).items()):
        if period is not None and item_period != period:
            continue
        match = QUESTION_ID.fullmatch(question_id)
        if match is None:
            continue
        folder = destination / item_period / f"lista-{match.group('list')}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{question_id}.py").write_text(item.code, encoding="utf-8", newline="\n")
        written += 1
    return written


async def _run(command: str, url: str, path: Path, period: str | None) -> str:
    from ipc_api.accounts.postgres import PostgresAccountStore
    from ipc_api.answer_keys.postgres import PostgresGabaritoStore

    accounts = await PostgresAccountStore.connect(url)
    try:
        store = PostgresGabaritoStore(accounts)
        if command == "importar":
            counts = await import_folder(store, path, period=period)
            return (
                f"gabaritos importados: {counts.created} novos, {counts.updated} alterados, "
                f"{counts.unchanged} iguais"
            )
        return f"gabaritos exportados: {await export_tree(store, path, period=period)}"
    finally:
        await accounts.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ipc_api.answer_keys.transfer",
        description="Leva os gabaritos de uma pasta para o banco, ou do banco para uma pasta.",
    )
    parser.add_argument("comando", choices=["importar", "exportar"])
    parser.add_argument("pasta", type=Path, help="a pasta <período>/lista-<n>/L<n>-Q<m>.py")
    parser.add_argument("--periodo", help="só este período, como 2026.2")
    args = parser.parse_args(argv)
    url = os.environ.get("IPC_DATABASE_ADMIN_URL", "")
    if not url:
        print(
            "Defina IPC_DATABASE_ADMIN_URL (credencial de administrador do banco).",
            file=sys.stderr,
        )
        return 2
    try:
        print(asyncio.run(_run(args.comando, url, args.pasta, args.periodo)))
    except (GabaritoLoadError, ValueError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
