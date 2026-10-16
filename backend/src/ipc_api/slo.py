"""Alertas de latência e de erro (S21-02; US-19, NFR-15).

A API guarda, só na memória, a latência e o status das requisições dos últimos 5 minutos (sem
conta, IP nem corpo) e responde em ``GET /health/slo``: 200 quando está tudo bem e 503 quando o
P95 do ``POST /api/v1/validate`` passa de 200 ms (NFR-01) ou mais de 1% das respostas são 5xx.
O UptimeRobot consulta esse endereço a cada 5 minutos e manda o e-mail de alerta, como já faz com
o ``/ready``; assim não é preciso outra conta externa (o Grafana Cloud de C8 continua opcional).

Com pouco tráfego, um único caso lento ou um único erro não deve virar alerta: abaixo de
``min_requests`` requisições na janela, a resposta é sempre 200.
"""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

#: A rota cuja latência o NFR-01 mede.
LATENCY_PATH = "/api/v1/validate"
#: Rotas de operação não entram na conta: o próprio monitoramento não pode mascarar o tráfego.
_IGNORED_PATHS = frozenset({"/health", "/ready", "/health/slo"})

Reason = Literal["latencia", "erros"]

#: Dias depois do fim aproximado do semestre do ATIVO (julho ou dezembro) a partir dos quais o
#: /health/slo avisa que ele parece defasado (S43-04). Só aviso: trocar o período é decisão da
#: coordenação (S31-09), nunca automática.
STALE_AFTER_DAYS = 60


def active_looks_stale(period: str, today: date) -> bool:
    """O período ativo (2026.2) já devia ter acabado: 60 dias depois de 31/07 (.1) ou 31/12 (.2)."""
    year, half = period.split(".")
    end = date(int(year), 7, 31) if half == "1" else date(int(year), 12, 31)
    return today > end + timedelta(days=STALE_AFTER_DAYS)


@dataclass(frozen=True, slots=True)
class SloConfig:
    window_s: float = 300.0
    p95_ms: float = 200.0
    error_rate_pct: float = 1.0
    min_requests: int = 20
    #: Teto de amostras guardadas; a 500 verificações por minuto, a janela tem cerca de 2.500.
    max_samples: int = 50_000

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> SloConfig:
        defaults = cls()
        return cls(
            window_s=float(env.get("IPC_SLO_WINDOW_S", defaults.window_s)),
            p95_ms=float(env.get("IPC_SLO_P95_MS", defaults.p95_ms)),
            error_rate_pct=float(env.get("IPC_SLO_ERROR_RATE_PCT", defaults.error_rate_pct)),
            min_requests=int(env.get("IPC_SLO_MIN_REQUESTS", defaults.min_requests)),
            max_samples=int(env.get("IPC_SLO_MAX_SAMPLES", defaults.max_samples)),
        )


@dataclass(frozen=True, slots=True)
class SloReport:
    healthy: bool
    requests: int
    validations: int
    p95_ms: float | None
    error_rate_pct: float
    reasons: tuple[Reason, ...]


class SloMonitor:
    def __init__(
        self, config: SloConfig | None = None, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._config = config or SloConfig()
        self._clock = clock
        # (instante, latência em ms ou None quando não é /validate, foi 5xx)
        self._samples: deque[tuple[float, float | None, bool]] = deque(
            maxlen=self._config.max_samples
        )

    def observe(self, path: str, status: int, latency_ms: float) -> None:
        if path in _IGNORED_PATHS:
            return
        latency = latency_ms if path == LATENCY_PATH and status < 500 else None
        self._samples.append((self._clock(), latency, status >= 500))

    def report(self) -> SloReport:
        config = self._config
        cutoff = self._clock() - config.window_s
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()
        requests = len(self._samples)
        errors = sum(1 for _, _, failed in self._samples if failed)
        latencies = sorted(latency for _, latency, _ in self._samples if latency is not None)
        p95 = _percentile(latencies, 95)
        error_rate = 100.0 * errors / requests if requests else 0.0
        reasons: list[Reason] = []
        if p95 is not None and len(latencies) >= config.min_requests and p95 > config.p95_ms:
            reasons.append("latencia")
        if requests >= config.min_requests and error_rate > config.error_rate_pct:
            reasons.append("erros")
        return SloReport(
            healthy=not reasons,
            requests=requests,
            validations=len(latencies),
            p95_ms=None if p95 is None else round(p95, 1),
            error_rate_pct=round(error_rate, 2),
            reasons=tuple(reasons),
        )


def _percentile(ordered: list[float], percent: int) -> float | None:
    """Percentil pelo método do posto mais próximo, sobre uma lista já ordenada."""
    if not ordered:
        return None
    rank = math.ceil(percent / 100 * len(ordered))
    return ordered[max(rank, 1) - 1]
