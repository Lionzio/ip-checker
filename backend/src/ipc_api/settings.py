"""Configuração da API, lida de variáveis de ambiente ``IPC_*``."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

KIB = 1024


def parse_lists(value: str) -> frozenset[int]:
    """Converte ``"1,2"`` em ``{1, 2}``; recusa listas fora de 1 a 6 (falha ao subir, FR-15)."""
    try:
        lists = frozenset(int(item) for item in value.split(",") if item.strip())
    except ValueError:
        lists = frozenset()
    if not lists or not lists <= set(range(1, 7)):
        raise ValueError(f"IPC_ENABLED_LISTS inválida: {value!r}. Use números de 1 a 6, como 1,2.")
    return lists


@dataclass(frozen=True, slots=True)
class ApiSettings:
    analyzer_url: str = "http://127.0.0.1:8001"
    #: Listas liberadas para os alunos (ENABLED_LISTS). O MVP libera só a Lista 1.
    enabled_lists: frozenset[int] = field(default_factory=lambda: frozenset({1}))
    #: Tempo máximo de uma chamada ao analyzer: 2 s de análise mais a ida e a volta.
    analyzer_timeout_s: float = 3.0
    #: Corpo máximo aceito antes de ler a requisição. Nas Fases 0 e 2 o Caddy também aplica esse
    #: limite; na Fase 1 (Render) não há Caddy, e a API é a primeira barreira (DoD, item 1).
    max_body_bytes: int = 128 * KIB
    #: Logs JSON no stdout (S9-01). Ligado por padrão; desligar só para depurar localmente.
    json_logs: bool = True

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> ApiSettings:
        env = os.environ if environ is None else environ
        defaults = cls()
        lists = env.get("IPC_ENABLED_LISTS")
        return cls(
            analyzer_url=env.get("IPC_ANALYZER_URL", defaults.analyzer_url),
            enabled_lists=parse_lists(lists) if lists is not None else defaults.enabled_lists,
            analyzer_timeout_s=float(
                env.get("IPC_ANALYZER_TIMEOUT_S", defaults.analyzer_timeout_s)
            ),
            max_body_bytes=int(env.get("IPC_MAX_BODY_BYTES", defaults.max_body_bytes)),
            json_logs=env.get("IPC_JSON_LOGS", "1") != "0",
        )
