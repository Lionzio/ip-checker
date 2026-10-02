"""Limite de taxa em memória (S10-01, FR-19): por conta e por IP.

- **Conta**: 30 verificações por minuto por conta da equipe (S13-02, C-04; antes eram 10 por
  ``X-Client-Id`` anônimo). A conta vem da sessão, resolvida pelo ``SessionMiddleware`` antes deste
  limite. Sem sessão, o "cliente" é o próprio IP, e a rota responde 401 logo depois.
- **IP**: 120 por minuto para IPs externos e 1.000 por minuto para as faixas do campus
  (``IPC_RATE_LIMIT_CAMPUS_CIDRS``), onde centenas de alunos saem por poucos IPs de NAT (P-04).
  IPv6 é limitado pelo prefixo /64.

A janela é deslizante: nunca passam mais que ``limite`` requisições em quaisquer 60 s seguidos,
como pede a US-17 (a 11ª em 1 min recebe 429). Uma requisição recusada não gasta o limite de
ninguém, para um cliente abusivo não esgotar o IP que divide com os colegas.

Privacidade (NFR-11): IP e conta existem só na memória deste processo, como hash com um sal
sorteado na subida, e somem até 2 min depois da última requisição. Nunca vão para o log.

O estado é local ao processo: vale porque há uma única instância da API (ADR-03).
"""

from __future__ import annotations

import hashlib
import ipaddress
import math
import secrets
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from ipc_api.errors import ErrorCode, error_response

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network
LimitScope = Literal["client", "ip", "capacity"]

WINDOW_S = 60.0
#: Intervalo entre varreduras que apagam as chaves sem requisições na janela.
SWEEP_INTERVAL_S = 10.0


def parse_networks(value: str) -> tuple[IPNetwork, ...]:
    """Converte ``"150.161.0.0/16, 2001:db8::/32"`` em redes; recusa valores inválidos na subida."""
    networks = []
    for item in value.split(","):
        text = item.strip()
        if not text:
            continue
        try:
            networks.append(ipaddress.ip_network(text, strict=True))
        except ValueError:
            raise ValueError(
                f"IPC_RATE_LIMIT_CAMPUS_CIDRS inválida: {text!r}. Use faixas como 150.161.0.0/16."
            ) from None
    return tuple(networks)


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    #: Por conta (S13-02). A correção em lote passa de 10 por minuto, o valor antigo por aluno.
    client_per_min: int = 30
    ip_per_min: int = 120
    campus_per_min: int = 1_000
    campus_networks: tuple[IPNetwork, ...] = (ipaddress.ip_network("150.161.0.0/16"),)
    #: Quantos proxies confiáveis há na frente da API. 0: o IP é o da conexão. 1 (Caddy no
    #: compose, proxy do Render): o último endereço do X-Forwarded-For, escrito pelo proxy.
    trusted_proxy_hops: int = 0
    #: Teto de chaves em memória. Cheio, clientes novos recebem 429 até a varredura liberar espaço.
    max_keys: int = 50_000


# ---------------------------------------------------------------------------------------------
# Janela deslizante
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Rejection:
    scope: LimitScope
    retry_after_s: int


class SlidingWindowLimiter:
    """Registro das requisições aceitas nos últimos 60 s, por chave."""

    def __init__(
        self,
        max_keys: int = 50_000,
        window_s: float = WINDOW_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._events: dict[bytes, deque[float]] = {}
        self._max_keys = max_keys
        self._window_s = window_s
        self._clock = clock
        self._next_sweep = clock() + SWEEP_INTERVAL_S

    def __len__(self) -> int:
        return len(self._events)

    def acquire(self, limits: Sequence[tuple[bytes, int, LimitScope]]) -> Rejection | None:
        """Registra a requisição se todas as chaves estiverem dentro do limite.

        Devolve ``None`` quando aceita. Quando recusa, nada é registrado, e a espera é o tempo
        até a requisição mais antiga que ocupa a vaga sair da janela.
        """
        now = self._clock()
        self._sweep(now)
        horizon = now - self._window_s
        worst: tuple[float, LimitScope] | None = None
        for key, limit, scope in limits:
            events = self._events.get(key)
            if events is None:
                continue
            while events and events[0] <= horizon:
                events.popleft()
            if len(events) >= limit:
                wait = events[len(events) - limit] + self._window_s - now
                if worst is None or wait > worst[0]:
                    worst = (wait, scope)
        if worst is not None:
            return Rejection(worst[1], self._seconds(worst[0]))

        new_keys = sum(1 for key, _, _ in limits if key not in self._events)
        if len(self._events) + new_keys > self._max_keys:
            self._sweep(now, force=True)
            if len(self._events) + new_keys > self._max_keys:
                return Rejection("capacity", self._seconds(self._window_s))
        for key, _, _ in limits:
            self._events.setdefault(key, deque()).append(now)
        return None

    def _seconds(self, wait: float) -> int:
        return max(1, min(math.ceil(wait), math.ceil(self._window_s)))

    def _sweep(self, now: float, *, force: bool = False) -> None:
        """Apaga as chaves cuja última requisição já saiu da janela (TTL de IPs e clientes)."""
        if not force and now < self._next_sweep:
            return
        self._next_sweep = now + SWEEP_INTERVAL_S
        horizon = now - self._window_s
        for key in [key for key, events in self._events.items() if events[-1] <= horizon]:
            del self._events[key]


# ---------------------------------------------------------------------------------------------
# Quem é o cliente
# ---------------------------------------------------------------------------------------------


def _parse_ip(value: str | None) -> IPAddress | None:
    if not value:
        return None
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def client_ip(scope: Scope, trusted_proxy_hops: int) -> IPAddress | None:
    """IP do cliente: o da conexão ou, atrás de proxies confiáveis, o que o proxy escreveu.

    Só as últimas ``trusted_proxy_hops`` entradas do ``X-Forwarded-For`` foram escritas por
    proxies nossos; tudo o que vem antes foi enviado pelo cliente e é ignorado.
    """
    peer = scope.get("client")
    peer_ip = _parse_ip(peer[0]) if peer else None
    if trusted_proxy_hops <= 0:
        return peer_ip
    forwarded = [
        part
        for value in Headers(scope=scope).getlist("x-forwarded-for")
        for part in value.split(",")
    ]
    if len(forwarded) < trusted_proxy_hops:
        return peer_ip
    return _parse_ip(forwarded[-trusted_proxy_hops]) or peer_ip


class ClientIdentifier:
    """Transforma IP e conta em chaves opacas e escolhe o limite de cada uma."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        # Sal por processo: as chaves em memória não revelam o IP nem o identificador.
        self._salt = secrets.token_bytes(16)

    def _key(self, kind: bytes, value: bytes) -> bytes:
        return kind + hashlib.blake2b(value, key=self._salt, digest_size=16).digest()

    def _is_campus(self, address: IPAddress) -> bool:
        return any(
            address.version == network.version and address in network
            for network in self._config.campus_networks
        )

    def limits(self, scope: Scope) -> list[tuple[bytes, int, LimitScope]]:
        config = self._config
        address = client_ip(scope, config.trusted_proxy_hops)
        if address is None:
            # Sem IP reconhecível (não acontece atrás do uvicorn): todos dividem uma chave.
            ip_value, ip_limit = b"desconhecido", config.ip_per_min
        else:
            ip_limit = config.campus_per_min if self._is_campus(address) else config.ip_per_min
            if isinstance(address, ipaddress.IPv6Address):
                # Um assinante IPv6 recebe um /64 inteiro: o limite vale para o prefixo.
                ip_value = ipaddress.ip_network((address, 64), strict=False).network_address.packed
            else:
                ip_value = address.packed
        ip_key = self._key(b"i", ip_value)

        account_id = scope.get("state", {}).get("account_id")
        # Sem sessão, o cliente é o IP: sair da conta não rende um limite maior.
        client_key = self._key(b"c", account_id if account_id else ip_value)
        return [(ip_key, ip_limit, "ip"), (client_key, config.client_per_min, "client")]


# ---------------------------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------------------------

#: Rotas limitadas: a que custa uma análise e as de conta que valem um ataque (login, registro,
#: verificação, reenvio e troca de senha); o bloqueio por falhas fica em ``auth/throttle.py``.
#: /health e /ready ficam livres para o monitoramento.
LIMITED_ROUTES = frozenset(
    {
        ("POST", "/api/v1/validate"),
        # Plágio (S17-02): também ocupa um worker do analisador, e divide o limite da conta.
        ("POST", "/api/v1/similarity"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/register"),
        ("POST", "/api/v1/auth/verify"),
        ("POST", "/api/v1/auth/verify/resend"),
        ("POST", "/api/v1/profile/password"),
        # Google (S16-01): cada início abre um fluxo na memória; o limite por IP o protege.
        ("GET", "/api/v1/auth/google/start"),
        ("GET", "/api/v1/auth/google/callback"),
        ("POST", "/api/v1/auth/google/complete"),
    }
)

_MESSAGES: dict[LimitScope, str] = {
    "client": "Você fez muitas requisições em pouco tempo.",
    "ip": "Muitas requisições vieram da sua rede em pouco tempo.",
    "capacity": "O serviço recebeu requisições demais em pouco tempo.",
}


class RateLimitMiddleware:
    """Responde 429 ``RATE_LIMITED`` antes de ler o corpo da requisição (5.2.2, passo 3)."""

    def __init__(
        self, app: ASGIApp, config: RateLimitConfig, limiter: SlidingWindowLimiter
    ) -> None:
        self.app = app
        self.limiter = limiter
        self.identifier = ClientIdentifier(config)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or (scope["method"], scope["path"]) not in LIMITED_ROUTES:
            await self.app(scope, receive, send)
            return

        rejection = self.limiter.acquire(self.identifier.limits(scope))
        if rejection is None:
            await self.app(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        state["outcome"] = ErrorCode.RATE_LIMITED
        state["rate_limit"] = rejection.scope
        # A recusa acontece antes do roteamento; o caminho é um dos de LIMITED_ROUTES.
        state["route_path"] = scope["path"]
        # O tempo de espera vai só em retry_after_s e no Retry-After: a página mostra uma
        # contagem regressiva, e um número fixo no texto ficaria desatualizado.
        response = error_response(
            429,
            ErrorCode.RATE_LIMITED,
            _MESSAGES[rejection.scope],
            retry_after_s=rejection.retry_after_s,
        )
        await response(scope, receive, send)
