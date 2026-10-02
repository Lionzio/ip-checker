"""Fixtures da suíte de segurança: um compose e dois clientes para a sessão inteira."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest

from security.harness import (
    CLIENT,
    EDGE_NETWORK,
    FRESH_CLIENT,
    IMAGE,
    NETWORK,
    PUBLIC_CLIENT,
    WEB_URL,
    Client,
    SessionPool,
    compose,
    docker,
    use_sessions,
)

SERVICES = ("web", "api", "analyzer", "db")


@pytest.fixture(scope="session")
def stack() -> Iterator[dict[str, str]]:
    """Sobe o ``deploy/compose.yaml`` real num projeto próprio e devolve o id de cada contêiner."""
    try:
        compose("up", "--build", "--detach", "--wait", "--wait-timeout", "180", timeout=900)
        ids = {service: compose("ps", "--quiet", service).strip() for service in SERVICES}
        use_sessions(SessionPool(ids["db"]))
        yield ids
    finally:
        compose("down", "--volumes", "--remove-orphans", timeout=120)


@pytest.fixture(scope="session")
def analyzer(stack: dict[str, str]) -> str:
    return stack["analyzer"]


def _client_container(name: str, network: str) -> str:
    """Contêiner cliente endurecido, ligado a uma única rede."""
    docker("rm", "--force", name, check=False)
    return docker(
        "run",
        "--detach",
        "--name",
        name,
        "--network",
        network,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        "64",
        "--entrypoint",
        "sleep",
        IMAGE,
        "infinity",
    ).strip()


@pytest.fixture(scope="session")
def client(analyzer: str) -> Iterator[Client]:
    """Cliente só na rede interna, no papel da ``api``: ataca o analyzer diretamente."""
    container = _client_container(CLIENT, NETWORK)
    try:
        yield Client(container)
    finally:
        docker("rm", "--force", container, check=False)


@pytest.fixture(scope="session")
def public(stack: dict[str, str]) -> Iterator[Client]:
    """Cliente só na rede da borda, no papel do navegador: tudo passa pelo Caddy."""
    container = _client_container(PUBLIC_CLIENT, EDGE_NETWORK)
    try:
        yield Client(container, base=WEB_URL)
    finally:
        docker("rm", "--force", container, check=False)


@pytest.fixture(scope="session")
def _fresh_clients(stack: dict[str, str]) -> Iterator[list[str]]:
    created: list[str] = []
    try:
        yield created
    finally:
        for container in created:
            docker("rm", "--force", container, check=False)


@pytest.fixture
def fresh_client(_fresh_clients: list[str]) -> Client:
    """Um cliente da borda novo para cada teste (S16-03, S17-02), com outro IP e, portanto,
    o próprio limite de 30 requisições anônimas por minuto (login e registro). Os contêineres só
    saem no fim da sessão: removido antes, o IP de um voltaria para o seguinte."""
    container = _client_container(f"{FRESH_CLIENT}-{uuid.uuid4().hex[:8]}", EDGE_NETWORK)
    _fresh_clients.append(container)
    return Client(container, base=WEB_URL)
