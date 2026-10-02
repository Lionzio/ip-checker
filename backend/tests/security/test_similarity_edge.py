"""Painel de plágio atacado pela borda (S17-02; DoD, seção 8, item 22).

As entradas dos itens 1 a 8, em qualquer um dos dois códigos, recebem resposta controlada pela
pilha real (Caddy, API e analyzer em contêiner): nenhum 5xx (o ``Client`` falha em qualquer um),
dentro do tempo e sem efeito colateral. Cada requisição vem de uma sessão nova, por um cliente
com IP próprio, para o limite de taxa não interferir.
"""

from __future__ import annotations

import base64
from typing import Any

import pytest

from security.harness import (
    Client,
    new_session,
    probe,
    requires_docker,
    session_header,
)

pytestmark = requires_docker

CANARY = "/tmp/canary-plagio"  # dentro do contêiner do analyzer
PLAIN = "nota = float(input())\nif nota >= 7:\n    print('aprovado')\n"


def _pair(code: str, side: str) -> dict[str, str]:
    return {"code_a": code, "code_b": PLAIN} if side == "a" else {"code_a": PLAIN, "code_b": code}


def _request(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": "POST",
        "path": "/api/v1/similarity",
        "json": body,
        "headers": session_header(new_session()),
    }


ATTACKS = {
    # Item 1: 51.201 bytes.
    "50kb-mais-um": ("#" + "a" * 51_200, 413, "PAYLOAD_TOO_LARGE"),
    # Item 2: 1.001 linhas.
    "1001-linhas": ("x = 1\n" * 1_001, 422, "INVALID_INPUT"),
    # Item 3: byte nulo e caracteres de controle.
    "byte-nulo": ("x = '\x00'\n", 422, "INVALID_INPUT"),
    "controle": ("x = 1\x1b\n", 422, "INVALID_INPUT"),
    # Item 4: aninhamento patológico.
    "parenteses": ("(" * 1_000 + ")" * 1_000, 422, "ANALYSIS_LIMIT"),
    "not-aninhado": ("x = " + "not " * 1_000 + "True\n", 422, "ANALYSIS_LIMIT"),
    # Item 5: cadeia de 25 mil termos.
    "cadeia-de-somas": ("x = " + "+".join(["1"] * 25_000) + "\n", 422, "ANALYSIS_LIMIT"),
    # Item 6: literal de 50 KB.
    "literal-50kb": ("x = '" + "a" * 50_000 + "'\n", 200, None),
    # Item 7: código que nunca termina, se fosse executado.
    "laco-infinito": ("while True:\n    pass\n", 200, None),
    "recursao": ("def f():\n    return f()\nf()\n", 200, None),
}


@pytest.mark.parametrize("side", ["a", "b"])
@pytest.mark.parametrize("attack", ATTACKS, ids=list(ATTACKS))
def test_malicious_inputs_in_either_code_get_a_controlled_answer(
    fresh_client: Client, attack: str, side: str
) -> None:
    code, status, error = ATTACKS[attack]

    (answer,) = fresh_client.send([_request(_pair(code, side))])

    assert (answer.status, answer.error_code) == (status, error), answer.body
    assert answer.elapsed_ms < 2_500
    if error is not None and status == 422:
        assert answer.body["error"]["message"].startswith(f"Código {side.upper()}: ")
    if status == 200:
        assert answer.body["status"] == "compared"


def test_invalid_utf8_bodies_are_invalid_input(fresh_client: Client) -> None:
    body = b'{"code_a": "x = 1", "code_b": "\xff\xfe"}'
    request = {
        "method": "POST",
        "path": "/api/v1/similarity",
        "raw": base64.b64encode(body).decode(),
        "headers": session_header(new_session()),
    }

    (answer,) = fresh_client.send([request])

    assert (answer.status, answer.error_code) == (422, "INVALID_INPUT")


RCE = [
    f'__import__("os").system("touch {CANARY}")\n',
    f'open("{CANARY}", "w").write("x")\n',
    f'import os\nos.system("touch {CANARY}")\n',
    f"exec(\"open('{CANARY}', 'w')\")\n",
]


def test_code_execution_attempts_are_compared_and_never_run(
    fresh_client: Client, stack: dict[str, str]
) -> None:
    requests = [_request(_pair(code, side)) for code in RCE for side in ("a", "b")]
    requests.append(_request({"code_a": RCE[0], "code_b": RCE[1]}))

    answers = fresh_client.send(requests)

    assert [answer.status for answer in answers] == [200] * len(requests)
    assert all(answer.body["status"] == "compared" for answer in answers)
    exists = f"import json, os; print(json.dumps(os.path.exists('{CANARY}')))"
    assert probe(stack["analyzer"], exists) is False


def test_a_renamed_copy_is_plagiarism_through_the_edge(fresh_client: Client) -> None:
    copy = PLAIN.replace("nota", "media")

    (answer,) = fresh_client.send([_request({"code_a": PLAIN, "code_b": copy})])

    assert answer.status == 200
    assert (answer.body["similarity"], answer.body["band"]["label"]) == (100.0, "Plágio")
    assert answer.body["notice"].startswith("A similaridade é um indício")
