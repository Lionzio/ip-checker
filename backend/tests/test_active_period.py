"""O período ativo num lugar só (S31-09) e a criação de um período novo (S31-10).

Trocar de período é mudar a linha de ``rulesets/ATIVO``: nenhum arquivo de configuração (deploy,
imagens, CI, scripts, padrão do analisador) pode repetir o período.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import BASE_RULESET, REPO_ROOT, RULESETS
from ipc_analyzer.cli import main
from ipc_analyzer.engine.ruleset import (
    ACTIVE_FILE,
    PERIOD,
    RulesetError,
    active_period,
    load_ruleset,
    resolve_ruleset_path,
)

GOLDEN = Path(__file__).parent / "golden"

#: Onde o período apareceria se a troca exigisse mudar código ou configuração.
CONFIGURATION = [
    "backend/Dockerfile",
    "deploy/render/Dockerfile",
    "deploy/render/supervisord.conf",
    "deploy/compose.yaml",
    "render.yaml",
    "backend/src/ipc_analyzer/service/settings.py",
    *sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / ".github" / "workflows").glob("*.yml")
    ),
    *sorted(path.relative_to(REPO_ROOT).as_posix() for path in (REPO_ROOT / "scripts").glob("*")),
]


@pytest.fixture
def rulesets(tmp_path: Path) -> Path:
    """Uma cópia de ``rulesets/`` com o período ativo e o arquivo ``ATIVO``."""
    root = tmp_path / "rulesets"
    period = active_period(RULESETS)
    (root / period / "questions").mkdir(parents=True)
    shutil.copy(BASE_RULESET, root / period / "base.yaml")
    (root / ACTIVE_FILE).write_text(f"{period}\n", encoding="utf-8")
    return root


# --- S31-09: o período ativo -------------------------------------------------------------------


def test_the_repository_names_one_valid_active_period() -> None:
    period = active_period(RULESETS)

    assert PERIOD.fullmatch(period)
    assert RULESETS / period / "base.yaml" == BASE_RULESET
    assert load_ruleset(RULESETS).ruleset.period == period


PERIODS = sorted(p.name for p in RULESETS.iterdir() if p.is_dir() and PERIOD.fullmatch(p.name))


@pytest.mark.parametrize("period", PERIODS)
def test_every_period_in_the_repository_loads(period: str) -> None:
    """Um período preparado antes de ser ativado (S35-09) já precisa carregar como o analisador."""
    ruleset = load_ruleset(RULESETS / period)

    assert ruleset.ruleset.period == period
    assert ruleset.version.startswith(f"{period}.")


def test_2027_1_keeps_the_2026_2_permissions() -> None:
    """P-22: as permissões de 2027.1 são as de 2026.2 até o documento novo dizer outra coisa.

    Quando uma permissão de 2027.1 mudar (por PR, com a fonte), este teste sai junto.
    """
    if "2027.1" not in PERIODS:
        pytest.skip("o período 2027.1 ainda não foi criado")

    def rules(period: str) -> str:
        text = (RULESETS / period / "base.yaml").read_text(encoding="utf-8")
        return text.replace(period, "<período>").split("ruleset_version:", 1)[1].split("\n", 1)[1]

    assert rules("2027.1") == rules("2026.2")


@pytest.mark.parametrize("relative", CONFIGURATION)
def test_configuration_does_not_repeat_the_active_period(relative: str) -> None:
    file = REPO_ROOT / relative
    if not file.is_file():
        pytest.skip(f"{relative} não existe")

    assert active_period(RULESETS) not in file.read_text(encoding="utf-8")


def test_the_root_the_period_folder_and_the_file_load_the_same_ruleset(rulesets: Path) -> None:
    period = active_period(rulesets)
    base = rulesets / period / "base.yaml"

    assert resolve_ruleset_path(rulesets) == base
    assert resolve_ruleset_path(rulesets / period) == base
    assert resolve_ruleset_path(base) == base
    assert load_ruleset(rulesets).sha256 == load_ruleset(base).sha256


def test_switching_the_active_period_is_one_line(rulesets: Path) -> None:
    assert main(["new-period", "2027.1", "--rulesets", str(rulesets)]) == 0
    (rulesets / ACTIVE_FILE).write_text("2027.1\n", encoding="utf-8")

    assert load_ruleset(rulesets).ruleset.period == "2027.1"


@pytest.mark.parametrize(
    ("content", "message"),
    [("2027\n", "período ativo inválido"), ("2026.2\n2027.1\n", "período ativo inválido")],
    ids=["formato", "duas-linhas"],
)
def test_an_invalid_active_file_fails_fast(rulesets: Path, content: str, message: str) -> None:
    (rulesets / ACTIVE_FILE).write_text(content, encoding="utf-8")

    with pytest.raises(RulesetError, match=message):
        load_ruleset(rulesets)


def test_an_active_period_without_folder_fails_fast(rulesets: Path) -> None:
    (rulesets / ACTIVE_FILE).write_text("2030.1\n", encoding="utf-8")

    with pytest.raises(RulesetError, match=r"período ativo 2030\.1 sem"):
        load_ruleset(rulesets)


def test_a_ruleset_in_another_period_folder_is_refused(rulesets: Path) -> None:
    wrong = rulesets / "2027.1"
    shutil.copytree(rulesets / active_period(rulesets), wrong)

    with pytest.raises(RulesetError, match=r"numa pasta do período 2027\.1"):
        load_ruleset(wrong)


def test_validate_accepts_the_rulesets_root(
    rulesets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate", str(rulesets), "--golden", str(GOLDEN)]) == 0
    assert "casos golden: " in capsys.readouterr().out


# --- S31-10: ipc-rules new-period --------------------------------------------------------------


def test_new_period_copies_the_rules_with_a_new_period_and_no_questions(
    rulesets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = active_period(rulesets)
    (rulesets / source / "questions" / "LEIA-ME.md").write_text(
        f"# Questões de {source}\n\nCadastrada a L2-Q3.\n", encoding="utf-8"
    )
    (rulesets / source / "questions" / "L2-Q3.yaml").write_text(
        "question_id: L2-Q3\nlist: 2\ntitle: Pares\nsource: enunciado\n"
        "allow_facts: ['builtin:zip']\n",
        encoding="utf-8",
    )

    assert main(["new-period", "2027.1", "--from", source, "--rulesets", str(rulesets)]) == 0

    created = load_ruleset(rulesets / "2027.1")
    original = load_ruleset(rulesets / source)
    assert created.ruleset.period == "2027.1"
    assert created.ruleset.ruleset_version == "2027.1.0"
    assert created.ruleset.rules == original.ruleset.rules
    assert created.ruleset.requirements == original.ruleset.requirements
    # A numeração das questões reinicia a cada período (P-07).
    assert created.questions == {}
    assert (rulesets / "2027.1" / "questions").is_dir()
    # O LEIA-ME do período novo não lista as questões do de origem (S43-05).
    readme = (rulesets / "2027.1" / "questions" / "LEIA-ME.md").read_text(encoding="utf-8")
    assert "ipc-rules validate ../rulesets/2027.1" in readme
    assert "L2-Q3" not in readme
    assert source not in readme
    assert (rulesets / "2027.1" / "referencias").is_dir()
    assert active_period(rulesets) == source, "criar um período não o ativa"
    out = capsys.readouterr().out
    assert "período 2027.1 criado" in out
    assert "ruleset 2027.1.0" in out


def test_new_period_comes_from_the_active_period_by_default(rulesets: Path) -> None:
    assert main(["new-period", "2027.1", "--rulesets", str(rulesets)]) == 0
    assert load_ruleset(rulesets / "2027.1").ruleset.period == "2027.1"


def test_new_period_never_overwrites(rulesets: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (rulesets / "2027.1").mkdir()

    assert main(["new-period", "2027.1", "--rulesets", str(rulesets)]) == 1
    assert "já existe" in capsys.readouterr().err
    assert list((rulesets / "2027.1").iterdir()) == []


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["2027.3"], "período inválido"),
        (["2027.1", "--from", "2026"], "período de origem inválido"),
        (["2026.2", "--from", "2026.2"], "diferente do de origem"),
    ],
    ids=["formato", "origem", "mesmo-periodo"],
)
def test_new_period_refuses_bad_periods(
    rulesets: Path, capsys: pytest.CaptureFixture[str], args: list[str], message: str
) -> None:
    assert main(["new-period", *args, "--rulesets", str(rulesets)]) == 2
    assert message in capsys.readouterr().err


def test_new_period_from_a_missing_period_fails(
    rulesets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["new-period", "2027.1", "--from", "2020.1", "--rulesets", str(rulesets)]) == 1
    assert "não foi possível ler" in capsys.readouterr().err
    assert not (rulesets / "2027.1").exists()


def test_an_invalid_new_period_is_removed(
    rulesets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = rulesets / active_period(rulesets) / "base.yaml"
    source.write_text(
        source.read_text(encoding="utf-8").replace("since_list: 3", "since_list: 9", 1),
        encoding="utf-8",
    )

    assert main(["new-period", "2027.1", "--rulesets", str(rulesets)]) == 1
    assert "ruleset inválido" in capsys.readouterr().err
    assert not (rulesets / "2027.1").exists()
