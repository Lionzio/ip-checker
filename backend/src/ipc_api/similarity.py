"""Faixas do painel de plágio (S17-02, FR-29).

A similaridade vem do analisador (ADR-05); a classificação fica aqui, em constantes. Ela usa o
valor exibido, com uma casa decimal, para que um 99,0% na tela nunca apareça como "Altas chances".
"""

from __future__ import annotations

from dataclasses import dataclass

from ipc_api.schemas import BandId


@dataclass(frozen=True, slots=True)
class Band:
    id: BandId
    label: str
    #: A faixa começa neste valor, inclusive.
    minimum: float


#: Da maior para a menor (FR-29).
BANDS = (
    Band("plagio", "Plágio", 99.0),
    Band("altas_chances", "Altas chances de plágio", 95.0),
    Band("requer_atencao", "Requer atenção", 90.0),
    Band("ligeiramente_suspeito", "Ligeiramente suspeito", 80.0),
    Band("sem_suspeitas", "Sem suspeitas", 0.0),
)

#: Abaixo disto (tokens normalizados no menor dos dois códigos), soluções independentes de
#: questões simples tendem a se parecer, e a página mostra um aviso a mais (ameaça 20).
SHORT_CODE_TOKENS = 60

NOTICE = (
    "A similaridade é um indício, não uma prova: a decisão final sobre plágio é sempre da equipe."
)


def displayed(percent: float) -> float:
    return round(percent, 1)


def classify(percent: float) -> Band:
    shown = displayed(percent)
    return next(band for band in BANDS if shown >= band.minimum)
