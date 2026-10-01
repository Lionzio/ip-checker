"""Configuração da API, lida de variáveis de ambiente ``IPC_*``."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from ipc_api.admission import AdmissionConfig
from ipc_api.edge import parse_origins
from ipc_api.ratelimit import RateLimitConfig, parse_networks

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
    #: Limite de taxa por cliente anônimo e por IP (S10-01, FR-19).
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    #: Controle de admissão das chamadas ao analyzer (S10-01, NFR-05).
    admission: AdmissionConfig = field(default_factory=AdmissionConfig)
    #: Origens da página que podem chamar a API pelo navegador (CORS). Vazio nas Fases 0 e 2,
    #: em que página e API têm a mesma origem; no piloto, o endereço da página na Vercel.
    cors_origins: tuple[str, ...] = ()
    #: Cabeçalho HSTS nas respostas (piloto: a API é servida em HTTPS pelo Render).
    hsts: bool = False
    #: Versão implantada (commit), mostrada em /ready para o pipeline saber que o deploy entrou.
    release: str | None = None

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
            rate_limit=_rate_limit_from_env(env),
            admission=_admission_from_env(env),
            cors_origins=parse_origins(env.get("IPC_CORS_ORIGINS", "")),
            hsts=env.get("IPC_HSTS", "0") == "1",
            # O Render informa o commit implantado em RENDER_GIT_COMMIT.
            release=env.get("IPC_RELEASE") or env.get("RENDER_GIT_COMMIT") or None,
        )


def _rate_limit_from_env(env: Mapping[str, str]) -> RateLimitConfig:
    defaults = RateLimitConfig()
    cidrs = env.get("IPC_RATE_LIMIT_CAMPUS_CIDRS")
    return RateLimitConfig(
        client_per_min=int(env.get("IPC_RATE_LIMIT_CLIENT_PER_MIN", defaults.client_per_min)),
        ip_per_min=int(env.get("IPC_RATE_LIMIT_IP_PER_MIN", defaults.ip_per_min)),
        campus_per_min=int(env.get("IPC_RATE_LIMIT_CAMPUS_PER_MIN", defaults.campus_per_min)),
        campus_networks=parse_networks(cidrs) if cidrs is not None else defaults.campus_networks,
        trusted_proxy_hops=int(env.get("IPC_TRUSTED_PROXY_HOPS", defaults.trusted_proxy_hops)),
        max_keys=int(env.get("IPC_RATE_LIMIT_MAX_KEYS", defaults.max_keys)),
    )


def _admission_from_env(env: Mapping[str, str]) -> AdmissionConfig:
    defaults = AdmissionConfig()
    return AdmissionConfig(
        capacity=int(env.get("IPC_ADMISSION_CAPACITY", defaults.capacity)),
        max_waiting=int(env.get("IPC_ADMISSION_MAX_WAITING", defaults.max_waiting)),
        max_wait_s=float(env.get("IPC_ADMISSION_MAX_WAIT_S", defaults.max_wait_s)),
    )
