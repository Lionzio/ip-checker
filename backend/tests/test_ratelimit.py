"""Limite de taxa (S10-01, FR-19): janela deslizante, identificação do cliente e limites por IP.

Desde a S13-02, o cliente é a conta da sessão (resolvida antes pelo ``SessionMiddleware``) ou,
sem sessão, o IP.
"""

from __future__ import annotations

import ipaddress
import uuid
from typing import Any

import pytest

from ipc_api.ratelimit import (
    ClientIdentifier,
    RateLimitConfig,
    Rejection,
    SlidingWindowLimiter,
    client_ip,
    parse_networks,
)

ACCOUNT_A = uuid.UUID("0b5c1f6e-6f0a-4a57-9d0c-3f1f0a2b4c5d").bytes
ACCOUNT_B = uuid.UUID("9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d").bytes


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def limiter(clock: FakeClock) -> SlidingWindowLimiter:
    return SlidingWindowLimiter(clock=clock)


def hit(limiter: SlidingWindowLimiter, key: bytes = b"k", limit: int = 10) -> Rejection | None:
    return limiter.acquire([(key, limit, "client")])


# --- Janela deslizante -------------------------------------------------------------------------


def test_eleventh_request_in_a_burst_is_rejected(limiter: SlidingWindowLimiter) -> None:
    assert [hit(limiter) for _ in range(10)] == [None] * 10

    assert hit(limiter) == Rejection("client", 60)


def test_eleventh_request_spread_over_a_minute_is_rejected(
    limiter: SlidingWindowLimiter, clock: FakeClock
) -> None:
    # Um token bucket deixaria passar: em 54 s ele já repôs 9 fichas. A US-17 pede a recusa.
    for _ in range(10):
        assert hit(limiter) is None
        clock.advance(5.4)

    assert hit(limiter) == Rejection("client", 6)  # a 1ª requisição sai da janela em 6 s


def test_requests_are_accepted_again_as_the_window_slides(
    limiter: SlidingWindowLimiter, clock: FakeClock
) -> None:
    for _ in range(10):
        hit(limiter)
        clock.advance(1)
    assert hit(limiter) == Rejection("client", 50)

    clock.advance(50)  # 60 s depois da 1ª requisição

    assert hit(limiter) is None
    assert hit(limiter) == Rejection("client", 1)


def test_rejected_requests_do_not_extend_the_wait(
    limiter: SlidingWindowLimiter, clock: FakeClock
) -> None:
    for _ in range(10):
        hit(limiter)
    for _ in range(50):
        clock.advance(1)
        assert hit(limiter) is not None  # insistir não registra nada

    clock.advance(10)

    assert hit(limiter) is None


def test_retry_after_is_at_least_one_second(
    limiter: SlidingWindowLimiter, clock: FakeClock
) -> None:
    hit(limiter, limit=1)
    clock.advance(59.9)

    assert hit(limiter, limit=1) == Rejection("client", 1)


def test_keys_are_independent(limiter: SlidingWindowLimiter) -> None:
    for _ in range(10):
        hit(limiter, b"a")

    assert hit(limiter, b"a") is not None
    assert hit(limiter, b"b") is None


def test_all_keys_must_be_within_their_limits(limiter: SlidingWindowLimiter) -> None:
    def request(client: bytes) -> Rejection | None:
        return limiter.acquire([(b"ip", 3, "ip"), (client, 2, "client")])

    assert request(b"c1") is None
    assert request(b"c1") is None
    assert request(b"c1") == Rejection("client", 60)
    assert request(b"c2") is None  # a recusa do c1 não gastou o limite do IP
    assert request(b"c3") == Rejection("ip", 60)


def test_longest_wait_wins_when_both_limits_are_exceeded(
    limiter: SlidingWindowLimiter, clock: FakeClock
) -> None:
    limiter.acquire([(b"ip", 1, "ip")])
    clock.advance(30)
    limiter.acquire([(b"client", 1, "client")])
    clock.advance(10)

    # O IP libera em 20 s; o cliente, em 50 s.
    assert limiter.acquire([(b"ip", 1, "ip"), (b"client", 1, "client")]) == Rejection("client", 50)


def test_idle_keys_are_forgotten(limiter: SlidingWindowLimiter, clock: FakeClock) -> None:
    for index in range(100):
        hit(limiter, f"cliente-{index}".encode())
    assert len(limiter) == 100

    clock.advance(61)
    hit(limiter, b"novo")

    assert len(limiter) == 1  # só a chave nova; IPs e clientes antigos saíram da memória


def test_full_table_rejects_new_keys_until_space_is_freed(clock: FakeClock) -> None:
    limiter = SlidingWindowLimiter(max_keys=3, clock=clock)
    for key in (b"a", b"b", b"c"):
        assert hit(limiter, key) is None

    assert hit(limiter, b"d") == Rejection("capacity", 60)
    assert hit(limiter, b"a") is None  # quem já é conhecido continua atendido
    assert len(limiter) == 3

    clock.advance(61)

    assert hit(limiter, b"d") is None


# --- Faixas do campus --------------------------------------------------------------------------


def test_parse_networks() -> None:
    assert parse_networks("150.161.0.0/16, 2001:db8::/32,") == (
        ipaddress.ip_network("150.161.0.0/16"),
        ipaddress.ip_network("2001:db8::/32"),
    )
    assert parse_networks("") == ()


@pytest.mark.parametrize("value", ["150.161.0.0/33", "campus", "150.161.2.1/16"])
def test_invalid_networks_prevent_startup(value: str) -> None:
    with pytest.raises(ValueError, match="IPC_RATE_LIMIT_CAMPUS_CIDRS"):
        parse_networks(value)


# --- Quem é o cliente --------------------------------------------------------------------------


def scope(
    peer: str | None = "203.0.113.5",
    forwarded: list[str] | None = None,
    account: bytes | None = None,
) -> dict[str, Any]:
    headers = [(b"x-forwarded-for", value.encode()) for value in forwarded or []]
    state = {"account_id": account} if account is not None else {}
    return {
        "type": "http",
        "client": (peer, 40_000) if peer else None,
        "headers": headers,
        "state": state,
    }


def test_without_trusted_proxies_the_forwarded_header_is_ignored() -> None:
    assert str(client_ip(scope(forwarded=["150.161.2.10"]), 0)) == "203.0.113.5"


@pytest.mark.parametrize(
    ("forwarded", "expected"),
    [
        (["198.51.100.7"], "198.51.100.7"),
        (["150.161.2.10, 198.51.100.7"], "198.51.100.7"),  # o 1º endereço veio do cliente
        (["150.161.2.10", "198.51.100.7"], "198.51.100.7"),  # dois cabeçalhos
        ([" 198.51.100.7 "], "198.51.100.7"),
        (["::ffff:198.51.100.7"], "198.51.100.7"),
        (["2001:db8::1"], "2001:db8::1"),
        (["lixo"], "10.0.0.2"),  # ilegível: vale o IP da conexão
        (["198.51.100.7,"], "10.0.0.2"),  # última entrada vazia
        ([], "10.0.0.2"),  # o proxy não escreveu nada
    ],
)
def test_one_trusted_proxy_uses_the_last_forwarded_address(
    forwarded: list[str], expected: str
) -> None:
    assert str(client_ip(scope("10.0.0.2", forwarded), 1)) == expected


def test_two_trusted_proxies_skip_the_last_address() -> None:
    forwarded = ["1.1.1.1, 198.51.100.7, 10.0.0.9"]

    assert str(client_ip(scope("10.0.0.2", forwarded), 2)) == "198.51.100.7"


def test_a_shorter_proxy_path_uses_the_first_forwarded_address() -> None:
    # S30-03: no piloto, quem chama o Render direto passa por menos proxies que a página. Todas as
    # entradas são dos nossos proxies, e a primeira é o cliente; o IP da conexão é um proxy interno
    # que muda a cada requisição e deixaria o limite por IP sem efeito.
    render_only = ["198.51.100.7, 10.0.0.8, 10.0.0.9"]

    assert str(client_ip(scope("10.0.0.2", render_only), 4)) == "198.51.100.7"
    assert str(client_ip(scope("10.0.0.2", ["198.51.100.7"]), 2)) == "198.51.100.7"
    # Pela página, com o mesmo número de proxies configurado, vale a entrada da Vercel.
    page = ["1.1.1.1, 198.51.100.7, 203.0.113.9, 10.0.0.8, 10.0.0.9"]
    assert str(client_ip(scope("10.0.0.2", page), 4)) == "198.51.100.7"


def test_unparseable_peer_has_no_ip() -> None:
    assert client_ip(scope("testclient"), 0) is None
    assert client_ip(scope(None), 0) is None


def limits_of(identifier: ClientIdentifier, **kwargs: Any) -> dict[str, tuple[bytes, int]]:
    return {name: (key, limit) for key, limit, name in identifier.limits(scope(**kwargs))}


@pytest.fixture
def identifier() -> ClientIdentifier:
    return ClientIdentifier(RateLimitConfig())


@pytest.mark.parametrize(
    ("peer", "limit"),
    [
        ("150.161.2.10", 1_000),
        ("150.161.0.0", 1_000),
        ("150.161.255.255", 1_000),
        ("::ffff:150.161.70.1", 1_000),
        ("150.160.255.255", 120),
        ("150.162.0.0", 120),
        ("203.0.113.5", 120),
        ("2001:db8::1", 120),
        ("testclient", 120),
    ],
)
def test_campus_addresses_have_their_own_limit(
    identifier: ClientIdentifier, peer: str, limit: int
) -> None:
    assert limits_of(identifier, peer=peer)["ip"][1] == limit
    assert limits_of(identifier, peer=peer)["client"][1] == 30


def test_ipv6_campus_networks_are_supported() -> None:
    identifier = ClientIdentifier(RateLimitConfig(campus_networks=parse_networks("2001:db8::/32")))

    assert limits_of(identifier, peer="2001:db8:1::5")["ip"][1] == 1_000
    assert limits_of(identifier, peer="150.161.2.10")["ip"][1] == 120


def test_ipv6_is_limited_by_its_64_prefix(identifier: ClientIdentifier) -> None:
    first = limits_of(identifier, peer="2001:db8:0:1::1")["ip"][0]

    assert limits_of(identifier, peer="2001:db8:0:1:ffff::9")["ip"][0] == first
    assert limits_of(identifier, peer="2001:db8:0:2::1")["ip"][0] != first


def test_client_key_comes_from_the_session_account(identifier: ClientIdentifier) -> None:
    a = limits_of(identifier, account=ACCOUNT_A)["client"][0]

    assert limits_of(identifier, account=ACCOUNT_A, peer="198.51.100.1")["client"][0] == a
    assert limits_of(identifier, account=ACCOUNT_B)["client"][0] != a


def test_x_client_id_no_longer_identifies_anyone(identifier: ClientIdentifier) -> None:
    # Sem sessão, o cabeçalho antigo da página não rende uma chave própria: vale o IP.
    request = scope()
    request["headers"].append((b"x-client-id", b"0b5c1f6e-6f0a-4a57-9d0c-3f1f0a2b4c5d"))
    keys = {name: key for key, _, name in identifier.limits(request)}

    assert keys["client"] == limits_of(identifier)["client"][0]


def test_without_a_session_the_client_is_the_ip(identifier: ClientIdentifier) -> None:
    anonymous = limits_of(identifier)["client"][0]

    assert limits_of(identifier, peer="198.51.100.1")["client"][0] != anonymous
    assert limits_of(identifier, account=ACCOUNT_A)["client"][0] != anonymous


def test_keys_are_opaque_and_salted_per_process() -> None:
    first, second = ClientIdentifier(RateLimitConfig()), ClientIdentifier(RateLimitConfig())
    keys = limits_of(first, peer="203.0.113.5", account=ACCOUNT_A)

    for key, _ in keys.values():
        assert len(key) == 17
        assert ipaddress.ip_address("203.0.113.5").packed not in key
        assert b"203.0.113.5" not in key
        assert ACCOUNT_A not in key
    assert limits_of(second, peer="203.0.113.5", account=ACCOUNT_A)["ip"][0] != keys["ip"][0]
    assert keys["ip"][0] != keys["client"][0]
