"""Gera o contrato OpenAPI versionado em ``docs/openapi.json`` (DoD, Documentação).

O teste ``test_openapi_contract_is_up_to_date`` falha quando o arquivo fica para trás. Para
regenerar, a partir de ``backend/``::

    uv run python -m ipc_api.openapi ../docs/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ipc_api.app import create_app
from ipc_api.settings import ApiSettings


def build() -> dict[str, Any]:
    return create_app(ApiSettings()).openapi()


def render() -> str:
    return json.dumps(build(), indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("uso: python -m ipc_api.openapi <arquivo de saída>\n")
        return 2
    Path(argv[0]).write_text(render(), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
