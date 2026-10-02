"""A API pública sob ataque, pela borda (S9-03, DoD seção 8, itens 1, 3, 4 e 13).

Tudo parte de um contêiner na ``edge_net``, como um navegador: Caddy, depois ``api``, depois
``analyzer``. O ``Client`` reprova qualquer 5xx. O último teste confere ``/ready`` depois dos
ataques; o estado do analyzer ao fim da sessão inteira fica com ``test_malicious_submissions``.
"""

from __future__ import annotations

import json
import re

import pytest

from security.harness import (
    Answer,
    Client,
    docker,
    probe,
    raw_request,
    requires_docker,
    service_logs,
    validate_request,
)

pytestmark = requires_docker

VALIDATE = "/api/v1/validate"
CANARY = "CANARIO9B1E"
FAKE_IP = "203.0.113.99"


def _code(answer: Answer) -> tuple[int, str | None]:
    return answer.status, answer.error_code


def _api_requests() -> int:
    """Quantas requisições a API registrou até agora (S9-01: uma linha JSON por requisição)."""
    return service_logs("api").count('"event": "request"')


# ---------------------------------------------------------------------------------------------
# Item 1: tamanho
# ---------------------------------------------------------------------------------------------


def test_code_above_51200_bytes_is_refused_by_the_api(public: Client) -> None:
    at_limit, over_limit = public.send(
        [validate_request("#" + "a" * 51_199), validate_request("#" + "a" * 51_200)]
    )

    assert at_limit.status == 200
    assert _code(over_limit) == (413, "PAYLOAD_TOO_LARGE")
    assert "51.200 bytes" in over_limit.body["error"]["message"]
    assert "x-request-id" in over_limit.headers  # quem respondeu foi a API


#: Manda só os cabeçalhos e o começo de um corpo grande e espera a resposta. Se a borda esperasse
#: o resto do corpo, a leitura terminaria por tempo esgotado, sem status.
EARLY_REJECTION_PROBE = r"""
import json, socket, sys
host, port, mode, marker = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
CRLF = b"\r\n"
start = ('{"code": "' + marker + "#").encode()
lines = [b"POST /api/v1/validate HTTP/1.1", b"Host: web", b"Content-Type: application/json"]
if mode == "declared":
    lines.append(b"Content-Length: 200033")
    first = start
else:
    lines.append(b"Transfer-Encoding: chunked")
    first = format(len(start), "x").encode() + CRLF + start + CRLF
data = b""
with socket.create_connection((host, port), timeout=5) as sock:
    sock.sendall(CRLF.join(lines) + CRLF + CRLF + first)  # o resto do corpo nunca é enviado
    while True:
        try:
            chunk = sock.recv(65536)
        except OSError:
            break
        if not chunk:
            break
        data += chunk
        if CRLF + CRLF in data and data.split(CRLF + CRLF, 1)[1].rstrip().endswith(b"}"):
            break
head, _, body = data.partition(CRLF + CRLF)
head_lines = head.decode("latin-1").split("\r\n")
status = int(head_lines[0].split()[1]) if head_lines[0] else 0
pairs = (line.split(":", 1) for line in head_lines[1:] if ":" in line)
headers = {name.strip().lower(): value.strip() for name, value in pairs}
print(json.dumps({"status": status, "headers": headers, "body": body.decode("utf-8", "replace")}))
"""


@pytest.mark.parametrize(
    ("mode", "status", "code"),
    [("declared", 413, "PAYLOAD_TOO_LARGE"), ("chunked", 411, "INVALID_INPUT")],
    ids=["content-length-200kb", "sem-content-length"],
)
def test_body_above_128kib_is_refused_before_being_read(
    public: Client, mode: str, status: int, code: str
) -> None:
    before = _api_requests()

    answer = probe(public.container, EARLY_REJECTION_PROBE, "web", "8080", mode, CANARY)

    # A borda responde só com os cabeçalhos e o começo do corpo, sem esperar o resto.
    assert answer["status"] == status
    assert json.loads(answer["body"])["error"]["code"] == code
    assert answer["headers"]["content-type"] == "application/json"
    assert "x-request-id" not in answer["headers"]  # resposta da borda, não da API
    assert _api_requests() == before  # e a API nunca recebeu a requisição


# ---------------------------------------------------------------------------------------------
# Item 3: entradas malformadas viram 422 INVALID_INPUT, nunca 5xx
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "request_body",
    [
        json.dumps({"code": "x = 1\x00\n", "list_number": 1}).encode(),
        json.dumps({"code": "x = 1\x01\n", "list_number": 1}).encode(),
        json.dumps({"code": "x = 1\x1b[2J\n", "list_number": 1}).encode(),
        json.dumps({"code": "x = 1\x7f\n", "list_number": 1}).encode(),
        b'{"code": "x = \\ud800", "list_number": 1}',
        b'{"code": "x = \xff\xfe", "list_number": 1}',
        b'{"code": "x = \xc3", "list_number": 1}',
        b'{"code": "x = 1"',
        b"",
        b"[]",
        b'{"code": 1, "list_number": 1}',
        b'{"code": "x = 1", "list_number": "1"}',
        b'{"code": "x = 1", "list_number": true}',
        b'{"code": "x = 1", "list_number": 1, "question_id": "../../etc"}',
        b'{"code": "x = 1", "list_number": 1, "extra": 1}',
    ],
    ids=[
        "nulo",
        "controle-01",
        "escape-de-terminal",
        "del",
        "surrogate-sozinho",
        "utf8-invalido",
        "utf8-truncado",
        "json-quebrado",
        "corpo-vazio",
        "json-de-lista",
        "code-numerico",
        "lista-texto",
        "lista-booleana",
        "questao-com-barra",
        "campo-extra",
    ],
)
def test_malformed_inputs_are_invalid_input(public: Client, request_body: bytes) -> None:
    (answer,) = public.send([raw_request(request_body, VALIDATE)])

    assert _code(answer) == (422, "INVALID_INPUT")


# ---------------------------------------------------------------------------------------------
# Item 4: aninhamento patológico para no limite, rápido
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "(" * 1_000 + ")" * 1_000,
        "x = " + "[" * 1_000 + "]" * 1_000,
        "x = " + "not " * 1_000 + "y",
    ],
    ids=["1000-parenteses", "1000-colchetes", "1000-not"],
)
def test_pathological_nesting_hits_the_analysis_limit(public: Client, code: str) -> None:
    (answer,) = public.send([validate_request(code)])

    assert _code(answer) == (422, "ANALYSIS_LIMIT")
    assert answer.elapsed_ms <= 2_500


# ---------------------------------------------------------------------------------------------
# Item 13: o código não fica em log nem em disco (NFR-11)
# ---------------------------------------------------------------------------------------------

#: Procura o marcador nas áreas graváveis dos contêineres (todas em memória).
FS_PROBE = r"""
import json, os, sys
marker = sys.argv[1].encode()
found = []
for root in sys.argv[2:]:
    for folder, _, files in os.walk(root):
        for name in files:
            path = os.path.join(folder, name)
            try:
                with open(path, "rb") as handle:
                    if marker in handle.read():
                        found.append(path)
            except OSError:
                pass
print(json.dumps(found))
"""


def test_privacy_canary_leaves_no_trace(public: Client, stack: dict[str, str]) -> None:
    headers = {
        "X-Forwarded-For": FAKE_IP,
        "X-Real-IP": FAKE_IP,
        "User-Agent": f"{CANARY}-navegador",
        "X-Request-Id": CANARY,
        "Referer": f"http://{CANARY}.example/",
    }
    requests = [
        validate_request(f"# {CANARY}\nx = '{CANARY}'\n", headers=headers),
        validate_request(f"y = input().{CANARY}()\n", headers=headers),
        validate_request(f"{CANARY} = (\n", headers=headers),
        validate_request("(" * 1_000 + CANARY + ")" * 1_000, headers=headers),
        validate_request(f"x = '{CANARY}'\n", list_number=3, headers=headers),
        validate_request(f"# {CANARY}" + "a" * 51_200, headers=headers),
        {"method": "GET", "path": f"/api/v1/{CANARY}?q={CANARY}", "headers": headers},
        {"method": "GET", "path": f"/{CANARY}", "headers": headers},
    ]

    answers = public.send(requests)

    assert CANARY in json.dumps(answers[1].body)  # o relatório volta ao aluno com o marcador...
    logs = service_logs("web", "api", "analyzer")
    assert logs.count(CANARY) == 0  # ...mas nenhum serviço o registra
    assert logs.count(FAKE_IP) == 0
    client_ip = docker(
        "inspect",
        "--format",
        "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
        public.container,
    ).strip()
    assert client_ip
    assert client_ip not in logs
    assert not re.search(r'"remote_ip"|"client_ip"', logs)

    # Disco: a raiz de todos os contêineres é só leitura, e as áreas em memória não guardam nada.
    # O único item do docker diff é o init montado pelo Docker (init: true), não uma escrita.
    init_mount = {"C /usr", "C /usr/sbin", "A /usr/sbin/docker-init"}
    for service, container in stack.items():
        assert set(docker("diff", container).splitlines()) <= init_mount, service
    assert probe(stack["analyzer"], FS_PROBE, CANARY, "/tmp", "/dev/shm") == []
    assert probe(stack["api"], FS_PROBE, CANARY, "/tmp", "/dev/shm") == []
    # Banco (Sprint 13): nenhuma tabela guarda o código, a URL ou os cabeçalhos (DoD, item 13).
    dump = docker(
        "exec", stack["db"], "pg_dump", "-U", "postgres", "-d", "ipchecker", "--data-only"
    )
    assert "app.session" in dump
    assert dump.count(CANARY) == 0
    assert dump.count(FAKE_IP) == 0


def test_ready_after_the_attacks(public: Client) -> None:
    """Tem de ser o último teste do módulo: a borda, a API e o analyzer seguem prontos."""
    (ready,) = public.send([{"method": "GET", "path": "/ready"}])

    assert ready.status == 200
    assert ready.body["status"] == "ready"
