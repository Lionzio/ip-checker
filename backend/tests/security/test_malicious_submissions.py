"""Submissões maliciosas contra o analyzer em contêiner (S7-01, DoD seção 8, itens 2 a 12).

Cada teste manda ao endpoint interno, a partir de outro contêiner da rede interna, o tipo de
entrada que um aluno mal-intencionado (ou só azarado) poderia enviar, e confere três coisas:
a resposta é a esperada, nunca é um 5xx genérico (o ``Client`` falha em qualquer 5xx) e chega a
tempo. O último teste confere que, depois de tudo, o serviço segue saudável.

Os tempos são medidos dentro da rede interna, sem o custo do ``docker exec``. Itens 1 e 13 a 15
dependem da API, do proxy e da telemetria e entram nas Sprints 9 a 14.
"""

from __future__ import annotations

import json
import re

import pytest

from security.harness import (
    WORKERS,
    Answer,
    Client,
    analyze_request,
    analyzer_logs,
    probe,
    processes,
    raw_request,
    requires_docker,
    workers,
)

pytestmark = requires_docker

LISTS = range(1, 7)
#: Fecho que dá a um código da Lista 1 o assunto obrigatório da lista (R-02).
IF_X = "if x:\n    print(x)\n"


def _code(answer: Answer) -> tuple[int, str | None]:
    return answer.status, answer.error_code


# ---------------------------------------------------------------------------------------------
# Itens 2 e 3: entradas inválidas viram 422 INVALID_INPUT, nunca 5xx
# ---------------------------------------------------------------------------------------------


def test_line_limit_is_enforced(client: Client) -> None:
    at_limit, over_limit = client.send(
        [analyze_request("x = 1\n" * 1_000), analyze_request("x = 1\n" * 1_001)]
    )

    assert at_limit.status == 200
    assert _code(over_limit) == (422, "INVALID_INPUT")
    assert "1.001 linhas" in over_limit.body["error"]["message"]


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
        b'{"code": "x = 1", "list_number": 0}',
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
        "lista-0",
    ],
)
def test_malformed_inputs_are_invalid_input(client: Client, request_body: bytes) -> None:
    (answer,) = client.send([raw_request(request_body)])

    assert _code(answer) == (422, "INVALID_INPUT")


# ---------------------------------------------------------------------------------------------
# Itens 4 a 6: entradas patológicas param nos limites, rápido
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "(" * 1_000 + ")" * 1_000,
        "x = " + "[" * 1_000 + "]" * 1_000,
        "x = " + "{" * 1_000 + "}" * 1_000,
        "x = " + "not " * 1_000 + "y",
        "x = " + "-" * 1_000 + "1",
        "x = " + "1+" * 24_999 + "1",
    ],
    ids=[
        "1000-parenteses",
        "1000-colchetes",
        "1000-chaves",
        "1000-not",
        "1000-sinais",
        "25k-somas",
    ],
)
def test_pathological_nesting_hits_the_analysis_limit(client: Client, code: str) -> None:
    answer = client.analyze(code)

    assert _code(answer) == (422, "ANALYSIS_LIMIT")
    assert answer.elapsed_ms <= 2_500


def test_widest_input_within_50kb_is_analyzed_in_time(client: Client) -> None:
    # Calibração da S5-01: ~53 mil nós em 50 KB, a entrada mais larga que cabe nos limites.
    code = ("a = " + ",".join("bcdefghijklmnopqrstuvwxy") + "\n") * 980

    answer = client.analyze(code)

    assert answer.status == 200
    assert answer.body["truncated"] is True  # 980 tuplas, cada uma uma violação; corte em 200
    assert answer.elapsed_ms < 2_000


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        ('x = "' + "a" * 51_150 + '"\n' + IF_X, "valid"),
        ("x = " + "f'{" * 10 + "1" + "}'" * 10 + "\n" + IF_X, "valid"),
        # A conversão !r faz parte da f-string (R-31); ver "Casos a observar" no mapeamento.
        ('x = f"' + "{x!r:>{y}}" * 4_000 + '"\n' + IF_X, "valid"),
        ("x = " + 'f"{' * 200 + "1" + '}"' * 200 + "\n", "syntax_error"),
    ],
    ids=["literal-50kb", "f-string-10-niveis", "f-string-larga", "f-string-200-niveis"],
)
def test_large_literals_and_nested_f_strings_answer_in_time(
    client: Client, code: str, expected_status: str
) -> None:
    answer = client.analyze(code)

    assert answer.status == 200
    assert answer.body["status"] == expected_status
    assert answer.elapsed_ms < 2_500


def test_deep_f_string_nesting_is_limited(client: Client) -> None:
    answer = client.analyze("x = " + 'f"{' * 100 + "1" + '}"' * 100 + "\n")

    assert _code(answer) == (422, "ANALYSIS_LIMIT")
    assert answer.elapsed_ms < 2_500


# ---------------------------------------------------------------------------------------------
# Item 7: código que nunca termina recebe resposta em < 100 ms, porque nada é executado
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "list_number"),
    [
        ("while True:\n    pass\n", 2),
        ("while True:\n    x = 1\n", 2),
        ("def f():\n    return f()\n\n\nf()\n", 6),
        ("x = 10 ** 10 ** 10\n", 1),
    ],
    ids=["while-true-pass", "while-true", "recursao-infinita", "potencia-gigante"],
)
def test_endless_code_is_never_executed(client: Client, code: str, list_number: int) -> None:
    # Melhor de 3: o critério mede o trabalho do analisador, não o ruído do agendador do runner.
    # Se o código fosse executado, as três tentativas esperariam o timeout de 2 s.
    answers = client.send([analyze_request(code, list_number)] * 3)

    assert {answer.status for answer in answers} == {200}
    assert min(answer.elapsed_ms for answer in answers) < 100


# ---------------------------------------------------------------------------------------------
# Item 8: tentativas de execução remota geram violações e o canário nunca é criado
# ---------------------------------------------------------------------------------------------

CANARY = "/tmp/canary"  # dentro do contêiner do analyzer

RCE_ATTEMPTS = {
    "import-os-system": (
        f'__import__("os").system("touch {CANARY}")\n',
        {(1, "builtin:__import__"), (1, "method:system")},
    ),
    "open": (f'open("{CANARY}", "w")\n', {(1, "builtin:open")}),
    "open-write": (
        f'open("{CANARY}", "w").write("x")\n',
        {(1, "builtin:open"), (1, "method:write")},
    ),
    "eval": ('eval("1")\n', {(1, "builtin:eval")}),
    "exec": ('exec("x = 1")\n', {(1, "builtin:exec")}),
    "compile": ('compile("1", "f", "eval")\n', {(1, "builtin:compile")}),
    "breakpoint": ("breakpoint()\n", {(1, "builtin:breakpoint")}),
    "getattr-builtins": ('getattr(__builtins__, "eval")\n', {(1, "builtin:getattr")}),
    "subclasses": (
        "().__class__.__mro__[1].__subclasses__()\n",
        {(1, "method:__class__"), (1, "method:__mro__"), (1, "method:__subclasses__")},
    ),
    "import-os": (f'import os\nos.system("touch {CANARY}")\n', {(1, "node:Import")}),
    "globals": ('globals()["__builtins__"]\n', {(1, "builtin:globals")}),
    "vars": ('vars()["eval"]\n', {(1, "builtin:vars")}),
}


@pytest.mark.parametrize("attempt", RCE_ATTEMPTS, ids=list(RCE_ATTEMPTS))
def test_remote_code_execution_attempts_are_violations_in_every_list(
    client: Client, analyzer: str, attempt: str
) -> None:
    code, expected = RCE_ATTEMPTS[attempt]

    answers = client.send([analyze_request(code, number) for number in LISTS])

    for number, answer in zip(LISTS, answers, strict=True):
        assert answer.status == 200, number
        assert answer.body["status"] == "invalid", number
        assert expected <= answer.flagged, (number, answer.flagged)
    assert (
        probe(analyzer, f"import json, os; print(json.dumps(os.path.exists('{CANARY}')))") is False
    )


# ---------------------------------------------------------------------------------------------
# Item 9: tentativas de evasão do motor geram as violações esperadas
# ---------------------------------------------------------------------------------------------

#: (código, lista, construções que precisam aparecer como violação). As listas escolhidas são
#: aquelas em que a construção é proibida; as categorias exatas ficam no corpus golden.
EVASIONS = {
    "metodo-por-variavel": ("s = input()\nf = s.split\nf()\n", 1, {(2, "method:split")}),
    "getattr-de-metodo": ('s = input()\ngetattr(s, "split")()\n', 1, {(2, "builtin:getattr")}),
    "classe-por-type": ('C = type("C", (), {})\n', 6, {(1, "builtin:type")}),
    "set-com-estrela": ("x = input()\ny = {*x}\n", 1, {(2, "node:Set"), (2, "node:Starred")}),
    "lista-com-estrela": ("a = input()\nb = [*a]\n", 1, {(2, "node:Starred")}),
    "print-com-estrela": ("a = input()\nprint(*a)\n", 2, {(2, "call:star_args")}),
    "print-com-kwargs": ("d = input()\nprint(**d)\n", 2, {(2, "kwarg:**")}),
    "parametro-kwargs": ("def f(**kw):\n    return 1\n", 6, {(1, "param:kwarg")}),
    "dict-com-kwargs": ("a = {1: 2}\nb = {**a}\n", 6, {(2, "derived:dict_unpack")}),
    "lambda-na-l4": ("f = lambda x: x\n", 4, {(1, "node:Lambda")}),
    "dict-literal-na-l4": ("d = {}\n", 4, {(1, "node:Dict")}),
    "dict-builtin-na-l4": ("d = dict()\n", 4, {(1, "builtin:dict")}),
    "walrus": ("if (n := 1) > 0:\n    print(n)\n", 2, {(1, "node:NamedExpr")}),
    "match": ("x = 1\nmatch x:\n    case 1:\n        print(x)\n", 6, {(2, "node:Match")}),
    "decorador-do-aluno": (
        "def d(f):\n    return f\n\n\n@d\ndef g():\n    return 1\n",
        6,
        {(5, "derived:decorator")},
    ),
    "async-def": ("async def f():\n    return 1\n", 6, {(1, "node:AsyncFunctionDef")}),
    "async-for": (
        "async def f(a):\n    async for x in a:\n        print(x)\n",
        6,
        {(2, "node:AsyncFor")},
    ),
    "yield": ("def f():\n    yield 1\n", 6, {(2, "node:Yield")}),
    "assert": ("x = 1\nassert x == 1\n", 6, {(2, "node:Assert")}),
    "with": ('with open("a") as f:\n    print(f)\n', 6, {(1, "node:With")}),
    "raise": ("raise ValueError\n", 6, {(1, "node:Raise")}),
    "nonlocal": (
        "def f():\n    x = 1\n    def g():\n        nonlocal x\n        x = 2\n"
        "    g()\n    return x\n",
        6,
        {(4, "node:Nonlocal")},
    ),
    "global": ("x = 1\ndef f():\n    global x\n    x = 2\n", 6, {(3, "node:Global")}),
    "eval-antes-de-sombrear": ('x = eval("1")\neval = 2\n', 1, {(1, "builtin:eval")}),
}


@pytest.mark.parametrize("evasion", EVASIONS, ids=list(EVASIONS))
def test_evasion_attempts_are_caught(client: Client, evasion: str) -> None:
    code, list_number, expected = EVASIONS[evasion]

    answer = client.analyze(code, list_number)

    assert answer.status == 200
    assert answer.body["status"] == "invalid"
    assert expected <= answer.flagged, answer.flagged


@pytest.mark.parametrize(
    ("code", "list_number"),
    [
        ("max = int(input())\nif max > 0:\n    print(max)\n", 1),
        ("len = 3\nfor i in range(len):\n    print(i)\n", 2),
        ("input = 5\nif input > 1:\n    print(input + 1)\n", 1),
    ],
    ids=["max-sombreado", "len-sombreado", "input-sombreado"],
)
def test_shadowed_builtins_are_not_false_positives(
    client: Client, code: str, list_number: int
) -> None:
    answer = client.analyze(code, list_number)

    assert answer.status == 200
    assert answer.body["status"] == "valid", answer.body["violations"]


# ---------------------------------------------------------------------------------------------
# Item 10: requisições concorrentes nunca recebem dados umas das outras
# ---------------------------------------------------------------------------------------------


def test_concurrent_requests_never_mix_results(client: Client) -> None:
    requests = []
    for index in range(60):
        padding = "x = 1\n" * (index % 7)
        if index % 10 == 9:
            # Algumas param no limite: a resposta de erro também não pode trazer dados de outra.
            code = f"# marcador_{index}\n" + "(" * 1_000 + ")" * 1_000
        else:
            code = f"{padding}y = input().marcador_{index}()\n"
        requests.append(analyze_request(code, 1 + index % 2))

    answers = client.send(requests, concurrency=20)

    for index, answer in enumerate(answers):
        markers = re.findall(r"marcador_\d+", json.dumps(answer.body))
        if index % 10 == 9:
            assert _code(answer) == (422, "ANALYSIS_LIMIT")
            assert markers == []
            continue
        assert answer.body["list_number"] == 1 + index % 2
        # A exigência R-02 (sem if) também aparece na Lista 1; o marcador vem à parte.
        (violation,) = [v for v in answer.body["violations"] if v["category"] != "EXIGENCIA"]
        assert violation["construct"] == f"method:marcador_{index}"
        assert violation["line"] == index % 7 + 1
        assert set(markers) == {f"marcador_{index}"}


# ---------------------------------------------------------------------------------------------
# Item 12: depois de tudo, o serviço está saudável, sem worker zumbi nem preso
# ---------------------------------------------------------------------------------------------


def test_service_is_healthy_after_the_attacks(client: Client, analyzer: str) -> None:
    """Tem de ser o último teste da sessão: confere o estado deixado por todos os anteriores."""
    health, quick = client.send(
        [{"method": "GET", "path": "/internal/health"}, analyze_request("x = 1\n" + IF_X)]
    )

    assert health.status == 200
    assert health.body["status"] == "ok"
    assert quick.body["status"] == "valid"
    assert quick.elapsed_ms < 500

    running = processes(analyzer)
    assert [p for p in running if p["state"] == "Z"] == []
    assert len(workers(running)) == WORKERS

    logs = analyzer_logs()
    for forbidden in ("Traceback", "RecursionError", '" 500'):
        assert forbidden not in logs, forbidden
