"""Limite de taxa atacado de fora, pela borda (S10-03, FR-19, ameaça 9).

Os mesmos critérios dos testes da API (``tests/test_api_rate_limit.py``), agora com a pilha real:
o IP que a API usa é o que o Caddy escreve no ``X-Forwarded-For``, e nada que o cliente mande
nesse cabeçalho muda o limite. Todos os pedidos saem de um único contêiner, ou seja, de um único
IP externo (limite de 120 por minuto).

Este módulo roda depois de ``test_api_limits`` e esgota o limite do IP do cliente público: nenhum
teste posterior pode depender de ``POST /api/v1/validate`` a partir dele.
"""

from __future__ import annotations

from security.harness import (
    Answer,
    Client,
    new_client_id,
    requires_docker,
    service_logs,
    validate_request,
)

pytestmark = requires_docker

CODE = "x = 1\n"
#: Endereços da faixa da UFPE (150.161.0.0/16), que um atacante forjaria para ganhar o limite
#: de 1.000 por minuto do campus.
FORGED_CAMPUS = "150.161.77."


def _statuses(answers: list[Answer]) -> list[int]:
    return [answer.status for answer in answers]


def _assert_rate_limited(answer: Answer) -> None:
    assert (answer.status, answer.error_code) == (429, "RATE_LIMITED")
    retry_after = answer.body["error"]["retry_after_s"]
    assert 1 <= retry_after <= 60
    assert answer.headers["retry-after"] == str(retry_after)  # o cabeçalho atravessa a borda
    assert "x-request-id" in answer.headers


def test_eleventh_request_of_a_session_is_rate_limited(public: Client) -> None:
    student = {"X-Client-Id": new_client_id()}

    answers = public.send([validate_request(CODE, headers=student) for _ in range(11)])

    assert _statuses(answers) == [200] * 10 + [429]
    _assert_rate_limited(answers[10])
    assert answers[10].body["error"]["message"] == "Você fez muitas verificações em pouco tempo."

    # Outro aluno, atrás do mesmo IP, segue sendo atendido.
    (colleague,) = public.send([validate_request(CODE)])
    assert colleague.status == 200


def test_forged_forwarded_for_does_not_create_new_identities(public: Client) -> None:
    # Sem X-Client-Id válido, o cliente é o IP. Se a borda aceitasse o X-Forwarded-For do cliente,
    # cada requisição abaixo pareceria vir de um IP diferente e nenhuma seria recusada.
    requests = [
        validate_request(
            CODE, headers={"X-Client-Id": "", "X-Forwarded-For": f"{FORGED_CAMPUS}{index}"}
        )
        for index in range(11)
    ]

    answers = public.send(requests)

    assert _statuses(answers) == [200] * 10 + [429]
    _assert_rate_limited(answers[10])


def test_one_external_ip_cannot_exceed_120_per_minute(public: Client) -> None:
    # 150 "alunos" diferentes de um mesmo IP externo, todos fingindo estar no campus.
    requests = [
        validate_request(CODE, headers={"X-Forwarded-For": f"{FORGED_CAMPUS}{index % 250}"})
        for index in range(150)
    ]

    answers = public.send(requests, concurrency=20)

    accepted = [answer for answer in answers if answer.status == 200]
    refused = [answer for answer in answers if answer.status != 200]
    # As requisições dos testes anteriores, no mesmo minuto, também contam para o IP.
    assert len(accepted) <= 120
    assert len(refused) >= 30
    for answer in refused:
        _assert_rate_limited(answer)
    assert refused[0].body["error"]["message"] == (
        "Muitas verificações vieram da sua rede em pouco tempo."
    )


def test_only_validation_is_limited_and_nothing_identifying_is_logged(public: Client) -> None:
    student = new_client_id()
    limited, lists, ready, health = public.send(
        [
            validate_request(CODE, headers={"X-Client-Id": student}),
            {"method": "GET", "path": "/api/v1/lists"},
            {"method": "GET", "path": "/ready"},
            {"method": "GET", "path": "/health"},
        ]
    )

    # Com o limite do IP esgotado, a página ainda carrega e o monitoramento ainda enxerga o serviço.
    assert limited.status == 429
    assert (lists.status, ready.status, health.status) == (200, 200, 200)

    logs = service_logs("web", "api", "analyzer")
    assert '"outcome": "RATE_LIMITED"' in logs
    assert '"rate_limit": "ip"' in logs
    assert '"rate_limit": "client"' in logs
    assert student not in logs
    assert FORGED_CAMPUS not in logs
