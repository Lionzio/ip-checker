"""O harness dos gabaritos (S20), com soluções sintéticas escritas para o teste, nunca reais."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import BASE_RULESET
from ipc_analyzer.engine.ruleset import CompiledRuleset, load_ruleset
from official_answers.harness import (
    EXCEPTIONS_FILE,
    PeriodRulesets,
    discover,
    load_exceptions,
    unexpected,
)

SOLUTIONS = {
    "2025.2/lista-1/q01.py": "n = int(input())\nif n % 2 == 0:\n    print('par')\n",
    "2025.2/lista-2/q01.py": "a = input()\nb = input()\nfor x, y in zip(a, b):\n    print(x, y)\n",
    "2025.2/lista-2/q02.py": (
        "a = input()\nb = input()\nz = zip(a, b)\nfor par in z:\n    print(par)\n"
    ),
    "2025.2/lista-2/q03.py": "for i in range(3)\n    print(i)\n",
    "2025.2/lista-2/q04.py": "\ufefffor i in range(3):\r\n    print(i)\r\n",
}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    for name, code in SOLUTIONS.items():
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(code.encode("utf-8"))
    return tmp_path


def test_discover_reads_the_list_from_the_folder(root: Path) -> None:
    (root / "solto.py").write_text("x = 1\n", encoding="utf-8")
    (root / "lista-1" / "lista-2").mkdir(parents=True)
    (root / "lista-1" / "lista-2" / "q.py").write_text("x = 1\n", encoding="utf-8")

    gabaritos, misplaced = discover(root)

    assert [(g.path, g.list_number) for g in gabaritos] == [
        ("2025.2/lista-1/q01.py", 1),
        ("2025.2/lista-2/q01.py", 2),
        ("2025.2/lista-2/q02.py", 2),
        ("2025.2/lista-2/q03.py", 2),
        ("2025.2/lista-2/q04.py", 2),
    ]
    assert misplaced == ["lista-1/lista-2/q.py", "solto.py"]


def test_unexpected_reports_rule_and_line_only(root: Path, base_ruleset: CompiledRuleset) -> None:
    gabaritos = {g.path: g for g in discover(root)[0]}

    assert unexpected(gabaritos["2025.2/lista-1/q01.py"], base_ruleset) == []
    assert unexpected(gabaritos["2025.2/lista-2/q01.py"], base_ruleset) == []
    assert unexpected(gabaritos["2025.2/lista-2/q02.py"], base_ruleset) == ["R-37 linha 3"]
    assert unexpected(gabaritos["2025.2/lista-2/q03.py"], base_ruleset) == [
        "erro de sintaxe na linha 1"
    ]
    # BOM e quebras de linha do Windows não atrapalham.
    assert unexpected(gabaritos["2025.2/lista-2/q04.py"], base_ruleset) == []


def test_rules_released_by_the_statement_are_accepted(
    root: Path, base_ruleset: CompiledRuleset
) -> None:
    name = "2025.2/lista-2/q02.py"
    (root / EXCEPTIONS_FILE).write_text(
        f'"{name}":\n  regras: ["R-37"]\n  motivo: "o enunciado pede zip() fora do for"\n',
        encoding="utf-8",
    )
    gabaritos = {g.path: g for g in discover(root)[0]}

    exceptions = load_exceptions(root)

    assert exceptions == {name: frozenset({"R-37"})}
    assert unexpected(gabaritos[name], base_ruleset, exceptions[name]) == []


def test_without_exceptions_file_nothing_is_released(root: Path) -> None:
    assert load_exceptions(root) == {}


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("- a.py\n", "mapa"),
        ('"a.py": ["R-37"]\n', "regras' e 'motivo"),
        ('"a.py":\n  regras: []\n  motivo: "x"\n', "pelo menos uma regra"),
        ('"a.py":\n  regras: ["zip"]\n  motivo: "x"\n', "formato R-xx"),
        ('"a.py":\n  regras: ["R-37"]\n  motivo: " "\n', "motivo"),
    ],
    ids=["lista", "sem-campos", "vazia", "id-invalido", "sem-motivo"],
)
def test_malformed_exceptions_are_refused(tmp_path: Path, content: str, message: str) -> None:
    (tmp_path / EXCEPTIONS_FILE).write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_exceptions(tmp_path)


def test_a_gabarito_of_the_active_period_uses_its_registered_question(tmp_path: Path) -> None:
    # Ruleset com a questão L2-Q3, que libera zip() fora do for (o que só o enunciado permite).
    rules = tmp_path / "rulesets"
    (rules / "questions").mkdir(parents=True)
    shutil.copy(BASE_RULESET, rules / "base.yaml")
    (rules / "questions" / "L2-Q3.yaml").write_text(
        "question_id: L2-Q3\nlist: 2\ntitle: Pares\nsource: o enunciado pede zip() fora do for\n"
        "allow_facts: ['builtin:zip']\n",
        encoding="utf-8",
    )
    ruleset = load_ruleset(rules / "base.yaml")
    code = "a = input()\nb = input()\nz = zip(a, b)\nfor par in z:\n    print(par)\n"
    answers = tmp_path / "gabaritos"
    for name in ("2026.2/lista-2/L2-Q3.py", "2025.2/lista-2/L2-Q3.py", "2026.2/lista-2/q03.py"):
        (answers / name).parent.mkdir(parents=True, exist_ok=True)
        (answers / name).write_text(code, encoding="utf-8")
    found = {g.path: g for g in discover(answers)[0]}

    # Só o do período ativo, com o nome da questão, usa a regra dela (P-07).
    assert unexpected(found["2026.2/lista-2/L2-Q3.py"], ruleset) == []
    assert unexpected(found["2025.2/lista-2/L2-Q3.py"], ruleset) == ["R-37 linha 3"]
    assert unexpected(found["2026.2/lista-2/q03.py"], ruleset) == ["R-37 linha 3"]


def test_a_gabarito_of_an_earlier_period_uses_the_questions_of_its_period(
    tmp_path: Path, base_ruleset: CompiledRuleset
) -> None:
    # S31-11: rulesets/2025.2/ com a L2-Q3 de 2025.2, que libera zip() fora do for. O período
    # ativo (2026.2) não tem essa questão; 2024.2 não tem pasta e cai no ruleset ativo.
    rules = tmp_path / "rulesets"
    (rules / "2025.2" / "questions").mkdir(parents=True)
    text = BASE_RULESET.read_text(encoding="utf-8")
    old = base_ruleset.ruleset
    text = text.replace(f'period: "{old.period}"', 'period: "2025.2"', 1)
    text = text.replace(f'ruleset_version: "{old.ruleset_version}"', 'ruleset_version: "2025.2.0"')
    (rules / "2025.2" / "base.yaml").write_text(text, encoding="utf-8")
    (rules / "2025.2" / "questions" / "L2-Q3.yaml").write_text(
        "question_id: L2-Q3\nlist: 2\ntitle: Pares\nsource: o enunciado pede zip() fora do for\n"
        "allow_facts: ['builtin:zip']\n",
        encoding="utf-8",
    )
    code = "a = input()\nb = input()\nz = zip(a, b)\nfor par in z:\n    print(par)\n"
    answers = tmp_path / "gabaritos"
    names = ("2025.2/lista-2/L2-Q3.py", "2024.2/lista-2/L2-Q3.py", f"{old.period}/lista-2/L2-Q3.py")
    for name in names:
        (answers / name).parent.mkdir(parents=True, exist_ok=True)
        (answers / name).write_text(code, encoding="utf-8")
    found = {g.path: g for g in discover(answers)[0]}
    periods = PeriodRulesets(rules, base_ruleset)

    earlier = periods.for_gabarito(found["2025.2/lista-2/L2-Q3.py"])
    assert earlier.ruleset.period == "2025.2"
    assert periods.for_gabarito(found["2025.2/lista-2/L2-Q3.py"]) is earlier, "carrega uma vez"
    assert unexpected(found["2025.2/lista-2/L2-Q3.py"], earlier) == []
    for name in names[1:]:
        ruleset = periods.for_gabarito(found[name])
        assert ruleset is base_ruleset
        assert unexpected(found[name], ruleset) == ["R-37 linha 3"]


def test_a_retired_period_keeps_its_own_rules(
    tmp_path: Path, base_ruleset: CompiledRuleset
) -> None:
    # S43-05: rulesets/encerrados/2023.1/ (o ipc-rules retire-period) e o gabarito tanto na raiz
    # quanto em encerrados/ do repositório dos gabaritos continuam com as regras de 2023.1.
    rules = tmp_path / "rulesets"
    (rules / "encerrados" / "2023.1" / "questions").mkdir(parents=True)
    text = BASE_RULESET.read_text(encoding="utf-8")
    old = base_ruleset.ruleset
    text = text.replace(f'period: "{old.period}"', 'period: "2023.1"', 1)
    text = text.replace(f'ruleset_version: "{old.ruleset_version}"', 'ruleset_version: "2023.1.0"')
    (rules / "encerrados" / "2023.1" / "base.yaml").write_text(text, encoding="utf-8")
    answers = tmp_path / "gabaritos"
    names = ("2023.1/lista-1/L1-Q1.py", "encerrados/2023.1/lista-1/L1-Q2.py")
    for name in names:
        (answers / name).parent.mkdir(parents=True, exist_ok=True)
        (answers / name).write_text("print(1)\n", encoding="utf-8")
    found = {g.path: g for g in discover(answers)[0]}
    periods = PeriodRulesets(rules, base_ruleset)

    for name in names:
        assert found[name].period == "2023.1"
        assert periods.for_gabarito(found[name]).ruleset.period == "2023.1"
