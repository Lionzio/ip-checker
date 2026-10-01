"""Fixtures da suíte de segurança: um único analyzer e um único cliente para a sessão inteira."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from security.harness import CLIENT, IMAGE, NETWORK, Client, compose, docker


@pytest.fixture(scope="session")
def analyzer() -> Iterator[str]:
    """Sobe o ``deploy/compose.yaml`` real num projeto próprio e devolve o id do contêiner."""
    try:
        # Só o analyzer: a suíte ataca o serviço interno (a API pública entra na S9-03).
        compose(
            "up", "--build", "--detach", "--wait", "--wait-timeout", "120", "analyzer", timeout=600
        )
        yield compose("ps", "--quiet", "analyzer").strip()
    finally:
        compose("down", "--volumes", "--remove-orphans", timeout=120)


@pytest.fixture(scope="session")
def client(analyzer: str) -> Iterator[Client]:
    """Contêiner cliente só na rede interna, também endurecido, no papel da futura ``api``."""
    docker("rm", "--force", CLIENT, check=False)
    container = docker(
        "run",
        "--detach",
        "--name",
        CLIENT,
        "--network",
        NETWORK,
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
    try:
        yield Client(container)
    finally:
        docker("rm", "--force", container, check=False)
