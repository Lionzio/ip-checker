"""Canário mensal no piloto (S35-04, NFR-11): o código verificado não pode ficar guardado no banco.

Planta uma marca única (``canario_<data>_<aleatório>``) num código verificado, comparado e usado
no feedback pela página, com a conta de verificação, e depois procura a marca em todas as colunas
das tabelas dos esquemas ``app`` e ``telemetry``, com a credencial de administrador. Qualquer
ocorrência é vazamento do código (sai com 1). A busca nos logs do Render é feita pelo painel
(decisão do autor, 11/10/2026: sem chave de API do Render): o script imprime a marca e o caminho.

Variáveis: ``PILOT_WEB_URL``, ``PILOT_LOGIN``, ``PILOT_PASSWORD`` e ``PILOT_DATABASE_ADMIN_URL``.
Nesta máquina, use ``scripts/canario-local.sh``, que as pede sem mostrá-las.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import sys
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import asyncpg
import httpx2

#: Uma consulta só, sem SQL montado com texto: o ``format`` do PostgreSQL cita os nomes (``%I``)
#: e a marca (``%L``), e o ``query_to_xml`` roda a contagem de cada coluna.
SEARCH = """
SELECT c.table_schema, c.table_name, c.column_name,
       (xpath('/row/n/text()', query_to_xml(format(
           'SELECT count(*) AS n FROM %I.%I WHERE %I::text LIKE %L',
           c.table_schema, c.table_name, c.column_name, '%' || $1 || '%'
       ), false, true, '')))[1]::text::int AS found
FROM information_schema.columns c
JOIN information_schema.tables t USING (table_schema, table_name)
WHERE c.table_schema IN ('app', 'telemetry') AND t.table_type = 'BASE TABLE'
ORDER BY 1, 2, 3
"""


def new_marker(now: datetime | None = None) -> str:
    moment = now or datetime.now(UTC)
    return f"canario_{moment:%Y%m%d}_{secrets.token_hex(4)}"


def planted_code(marker: str) -> str:
    """Um código da Lista 1 com a marca no comentário, num nome e num texto."""
    return f"# {marker}\n{marker} = int(input())\nif {marker} > 0:\n    print('{marker}')\n"


def plant(web: str, login: str, password: str, marker: str) -> None:
    """Verifica, compara e gera o feedback de um código com a marca, pela página."""
    parts = urlsplit(web)
    page = {"Origin": f"{parts.scheme}://{parts.netloc}"}
    code = planted_code(marker)
    with httpx2.Client(timeout=30, follow_redirects=False) as client:
        response = client.post(
            f"{web}/api/v1/auth/login", json={"login": login, "password": password}, headers=page
        )
        if response.status_code != 200:
            raise SystemExit(f"canário: o login falhou com {response.status_code}")
        try:
            calls = [
                ("/api/v1/validate", {"code": code, "list_number": 1}),
                ("/api/v1/similarity", {"code_a": code, "code_b": code}),
                (
                    "/api/v1/feedback",
                    {"code": code, "list_number": 1, "student_name": marker, "annotation": marker},
                ),
            ]
            for path, body in calls:
                answer = client.post(f"{web}{path}", json=body, headers=page)
                print(f"  {path}: {answer.status_code}")
        finally:
            client.post(f"{web}/api/v1/auth/logout", content=b"", headers=page)


async def search(dsn: str, marker: str) -> list[tuple[str, int]]:
    """As colunas em que a marca aparece, com quantas linhas; vazio quando não há nada."""
    connection: Any = await asyncpg.connect(dsn)
    try:
        rows = await connection.fetch(SEARCH, marker)
    finally:
        await connection.close()
    print(f"  {len(rows)} colunas conferidas nos esquemas app e telemetry")
    return [
        (f"{row['table_schema']}.{row['table_name']}.{row['column_name']}", row["found"])
        for row in rows
        if row["found"]
    ]


def main() -> int:
    names = ["PILOT_WEB_URL", "PILOT_LOGIN", "PILOT_PASSWORD", "PILOT_DATABASE_ADMIN_URL"]
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        print(f"canário: defina {', '.join(missing)}", file=sys.stderr)
        return 2
    marker = new_marker()
    print(f"Marca deste canário: {marker}")
    print("Plantando pela página...")
    plant(
        os.environ["PILOT_WEB_URL"].rstrip("/"),
        os.environ["PILOT_LOGIN"],
        os.environ["PILOT_PASSWORD"],
        marker,
    )
    print("Procurando no banco...")
    found = asyncio.run(search(os.environ["PILOT_DATABASE_ADMIN_URL"], marker))
    print()
    print(
        "Agora os logs, pelo painel: Render > ip-checker-api > Logs, busque a marca acima "
        "na última hora. O esperado é nenhuma linha."
    )
    if found:
        print("VAZAMENTO: a marca está no banco (NFR-11):", file=sys.stderr)
        for column, count in found:
            print(f"  {column}: {count} linha(s)", file=sys.stderr)
        return 1
    print("Banco: nenhuma ocorrência da marca (NFR-11).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
