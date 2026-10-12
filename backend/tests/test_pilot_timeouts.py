"""Prazos da análise no piloto (S36-06, ADR-03).

No plano gratuito do Render (0,1 CPU), a análise leva cerca de 60 ms por KB: a entrada de 50 KB do
benchmark passa de 3 s, acima do prazo padrão de 2 s, e recebia 422 ``ANALYSIS_LIMIT`` (medido em
12/10/2026 com ``tests/pilot/test_large_input.py``). O ``supervisord.conf`` do piloto dá ao
analisador um prazo maior, com folga de pelo menos o dobro da maior entrada, e à API um prazo de
espera 1 s maior que o do analisador, para que a API nunca desista antes da resposta do analisador.
"""

from __future__ import annotations

import re

from conftest import REPO_ROOT
from ipc_api.settings import ANALYZER_MARGIN_S

CONF = REPO_ROOT / "deploy" / "render" / "supervisord.conf"
#: A maior entrada legítima medida no piloto, em segundos: 50 KB levou de 3,3 a 3,8 s depois do
#: deploy da sprint-36 (12/10/2026; antes, 3,1 s era só uma extrapolação de 10 a 30 KB).
LARGEST_INPUT_S = 3.8
#: O prazo da página para a verificação (``frontend/src/hooks/useValidateCode.ts``).
PAGE_TIMEOUT_S = 10.0


def _program(name: str) -> str:
    text = CONF.read_text(encoding="utf-8")
    match = re.search(rf"^\[program:{name}\]\n(.*?)(?=^\[|\Z)", text, flags=re.S | re.M)
    assert match is not None, f"programa {name} ausente do supervisord.conf"
    return match.group(1)


def _number(pattern: str, text: str) -> float:
    match = re.search(pattern, text)
    assert match is not None, pattern
    return float(match.group(1))


def test_the_pilot_analyzer_has_room_for_the_largest_input() -> None:
    analyzer = _number(r"\bIPC_TIMEOUT_S=(\d+(?:\.\d+)?)", _program("analyzer"))
    assert analyzer >= 2 * LARGEST_INPUT_S


def test_the_api_waits_for_the_analyzer_and_the_page_waits_for_the_api() -> None:
    analyzer = _number(r"\bIPC_TIMEOUT_S=(\d+(?:\.\d+)?)", _program("analyzer"))
    api = _number(r'IPC_ANALYZER_TIMEOUT_S="(\d+(?:\.\d+)?)"', _program("api"))
    assert api == analyzer + ANALYZER_MARGIN_S
    assert api < PAGE_TIMEOUT_S
