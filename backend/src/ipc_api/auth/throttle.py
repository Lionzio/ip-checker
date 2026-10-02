"""Limite de tentativas de login (FR-25, NFR-22): contra força bruta e *credential stuffing*.

Conta só as falhas, numa janela deslizante de 15 min: depois de 5 falhas da mesma conta, a próxima
tentativa espera até a falha mais antiga sair da janela. Um segundo limite, mais alto, vale por IP
(maior ainda nas faixas do campus, onde a equipe sai por poucos IPs de NAT). Um login certo zera
as falhas da conta. As chaves ficam só em memória, como hash com sal do processo, como no limite
de taxa (P-11).
"""

from __future__ import annotations

import hashlib
import math
import secrets
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass

WINDOW_S = 15 * 60.0


@dataclass(frozen=True, slots=True)
class LoginThrottleConfig:
    #: Falhas por conta (ou por nome/e-mail digitado, se a conta não existir) em 15 min.
    account_failures: int = 5
    #: Falhas por IP em 15 min; no campus, o limite é maior.
    ip_failures: int = 30
    campus_ip_failures: int = 200
    max_keys: int = 50_000


class LoginThrottle:
    def __init__(
        self,
        max_keys: int = 50_000,
        window_s: float = WINDOW_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._failures: dict[bytes, deque[float]] = {}
        self._max_keys = max_keys
        self._window_s = window_s
        self._clock = clock
        self._salt = secrets.token_bytes(16)

    def key(self, kind: str, value: str | bytes) -> bytes:
        raw = value.encode() if isinstance(value, str) else value
        return kind.encode() + hashlib.blake2b(raw, key=self._salt, digest_size=16).digest()

    def _recent(self, key: bytes, now: float) -> deque[float] | None:
        events = self._failures.get(key)
        if events is None:
            return None
        horizon = now - self._window_s
        while events and events[0] <= horizon:
            events.popleft()
        if not events:
            del self._failures[key]
            return None
        return events

    def retry_after(self, limits: Sequence[tuple[bytes, int]]) -> int | None:
        """Segundos de espera se alguma chave já esgotou as falhas; ``None`` se pode tentar."""
        now = self._clock()
        wait = 0.0
        for key, limit in limits:
            events = self._recent(key, now)
            if events is not None and len(events) >= limit:
                wait = max(wait, events[len(events) - limit] + self._window_s - now)
        return max(1, math.ceil(wait)) if wait > 0 else None

    def fail(self, keys: Sequence[bytes]) -> None:
        now = self._clock()
        if len(self._failures) + len(keys) > self._max_keys:
            for key in list(self._failures):
                self._recent(key, now)
        for key in keys:
            if key in self._failures or len(self._failures) < self._max_keys:
                self._failures.setdefault(key, deque()).append(now)

    def clear(self, key: bytes) -> None:
        self._failures.pop(key, None)
