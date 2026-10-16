"""O gerador das soluções de referência por IA (S42-04, ADR-08), com um provedor falso, sem rede.

Nada aqui chama uma IA de verdade: o pedido leva só o enunciado, o arquivo sai com o cabeçalho e o
código, e a cota esgotada (429) é retomada na rodada seguinte.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from conftest import BASE_RULESET
from ipc_api.feedback.providers import FakeProvider, Prompt, ProviderError
from ipc_api.referencias import (
    Job,
    extract_code,
    generate,
    main,
    plan,
    read_env_file,
    statements,
)

STATEMENT = "Leia dois inteiros, um por linha, e mostre a soma deles."
ANSWER = "Aqui está:\n```python\na = int(input())\nb = int(input())\nprint(a + b)\n```\n"
#: As variáveis de uma IA falsa na cadeia, como o deploy/.env teria com as de verdade.
FAKE_ENV = {"IPC_LLM_CHAIN": "falsa", "IPC_LLM_FALSA_PROVIDER": "fake"}


@pytest.fixture
def period(tmp_path: Path) -> Path:
    folder = tmp_path / "rulesets" / "2026.2"
    folder.mkdir(parents=True)
    (folder / "base.yaml").write_bytes(BASE_RULESET.read_bytes())
    return folder


@pytest.fixture
def texts(tmp_path: Path) -> Path:
    folder = tmp_path / "enunciados"
    folder.mkdir()
    (folder / "L1-Q2.md").write_text(STATEMENT, encoding="utf-8")
    (folder / "L3-Q1.txt").write_text("Mostre os números de 1 a n.", encoding="utf-8")
    (folder / "LEIA-ME.md").write_text("não é uma questão", encoding="utf-8")
    return folder


def test_the_code_comes_from_the_python_block() -> None:
    assert extract_code(ANSWER) == "a = int(input())\nb = int(input())\nprint(a + b)\n"
    assert extract_code("```\nprint(1)\n```") == "print(1)\n"
    # Sem o bloco pedido, nada é gravado; a sintaxe fica para o ipc-rules validate.
    assert extract_code("print(1)") is None
    assert extract_code("Não sei resolver.") is None
    assert extract_code("```python\n\n```") is None


def test_the_env_file_is_read_without_quotes_or_comments(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        '# comentário\nIPC_LLM_CHAIN=gemini,groq\nIPC_LLM_GEMINI_MODEL="gemini-x"\n\nSEM_IGUAL\n',
        encoding="utf-8",
    )

    assert read_env_file(env) == {
        "IPC_LLM_CHAIN": "gemini,groq",
        "IPC_LLM_GEMINI_MODEL": "gemini-x",
    }


def test_only_question_files_are_statements(texts: Path) -> None:
    assert sorted(statements(texts)) == ["L1-Q2", "L3-Q1"]
    assert list(statements(texts, "L1-Q2")) == ["L1-Q2"]


def test_references_go_to_the_period_and_calibration_outside(period: Path, tmp_path: Path) -> None:
    ais = [("gemini", "m1"), ("groq", "m2")]

    references = plan(period, {"L1-Q2": STATEMENT}, ais, 2, None)
    calibration = plan(period, {"L1-Q2": STATEMENT}, ais, 1, tmp_path / "calibracao")

    assert [job.target.relative_to(period).as_posix() for job in references] == [
        "referencias/L1-Q2/gemini-1.py",
        "referencias/L1-Q2/gemini-2.py",
        "referencias/L1-Q2/groq-1.py",
        "referencias/L1-Q2/groq-2.py",
    ]
    assert [job.target.relative_to(tmp_path).as_posix() for job in calibration] == [
        "calibracao/2026.2/lista-1/L1-Q2-gemini-1.py",
        "calibracao/2026.2/lista-1/L1-Q2-groq-1.py",
    ]


def test_the_prompt_carries_only_the_statement_and_the_file_has_the_header(
    period: Path,
) -> None:
    provider = FakeProvider(lambda _prompt: ANSWER)
    jobs = plan(period, {"L1-Q2": STATEMENT}, [("falsa", "modelo-x")], 2, None)
    when = datetime(2026, 10, 16, tzinfo=UTC)

    report = asyncio.run(generate(jobs, {"falsa": provider}, 2, now=lambda: when))

    assert len(report.written) == 2
    prompt: Prompt = provider.prompts[0]
    assert STATEMENT in prompt.user
    assert "solução 1 de 2" in prompt.user
    assert "aluno" not in prompt.user.lower()
    text = jobs[0].target.read_text(encoding="utf-8")
    assert text.startswith(
        "# Solução gerada por IA (S42-04, ADR-08): falsa, modelo modelo-x, 16/10"
    )
    assert text.endswith("print(a + b)\n")


def test_a_second_run_resumes_and_skips_what_exists(period: Path) -> None:
    jobs = plan(period, {"L1-Q2": STATEMENT}, [("falsa", "m")], 1, None)
    asyncio.run(generate(jobs, {"falsa": FakeProvider(lambda _p: ANSWER)}, 1))
    again = FakeProvider(lambda _p: ANSWER)

    report = asyncio.run(generate(jobs, {"falsa": again}, 1))

    assert report.skipped == [jobs[0].target]
    assert again.prompts == []


def test_quota_waits_retries_and_then_gives_up_on_that_ai(period: Path) -> None:
    calls: list[str] = []

    def quota(_prompt: Prompt) -> str:
        calls.append("x")
        raise ProviderError("HTTP 429", status=429)

    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        waits.append(seconds)

    jobs = plan(period, {"L1-Q2": STATEMENT}, [("falsa", "m")], 2, None)
    report = asyncio.run(generate(jobs, {"falsa": FakeProvider(quota)}, 2, sleep=sleep))

    assert report.written == []
    assert len(calls) == 4  # a primeira tentativa e 3 de novo; depois, a IA fica de fora
    assert waits == [60.0, 60.0, 60.0]
    assert [line.split(":")[1].strip() for line in report.failed] == [
        "HTTP 429",
        "cota esgotada",
    ]


def test_an_answer_without_a_code_block_is_not_written(period: Path) -> None:
    jobs = plan(period, {"L1-Q2": STATEMENT}, [("falsa", "m")], 1, None)

    report = asyncio.run(generate(jobs, {"falsa": FakeProvider(lambda _p: "Não sei.")}, 1))

    assert report.written == []
    assert report.failed == ["L1-Q2 falsa-1: sem bloco de código"]
    assert not jobs[0].target.exists()


def test_the_command_writes_through_the_chain(
    period: Path, texts: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # O provedor "fake" devolve um texto de feedback, que não é Python: o comando reporta a falha
    # e sai com 1, sem gravar nada e sem mostrar o texto.
    code = main([str(period), "--enunciados", str(texts), "--questao", "L1-Q2"], FAKE_ENV)

    out = capsys.readouterr().out
    assert code == 1
    assert "0 gravados, 0 já existiam, 2 falharam (1 questões, 1 IAs)" in out
    assert "Gostei" not in out


def test_the_keys_never_appear_and_missing_ai_is_explained(
    period: Path, texts: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "chave-secreta-que-nunca-aparece"
    env = tmp_path / ".env"
    env.write_text(f"IPC_LLM_CHAIN=\nIPC_LLM_GROQ_API_KEY={secret}\n", encoding="utf-8")

    code = main([str(period), "--enunciados", str(texts), "--env-file", str(env)], {})

    captured = capsys.readouterr()
    assert code == 2
    assert "nenhuma IA configurada" in captured.err
    assert secret not in captured.out + captured.err


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--por-ia", "6"], "--por-ia vai de 1 a 5"),
        (["--questao", "L7-Q1"], "questão inválida"),
    ],
)
def test_bad_arguments_are_refused(
    period: Path,
    texts: Path,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
    message: str,
) -> None:
    assert main([str(period), "--enunciados", str(texts), *args], FAKE_ENV) == 2
    assert message in capsys.readouterr().err


def test_a_folder_that_is_not_a_period_is_refused(
    tmp_path: Path, texts: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path), "--enunciados", str(texts)], FAKE_ENV) == 2
    assert "não é a pasta de um período" in capsys.readouterr().err


def test_a_job_knows_its_list(period: Path) -> None:
    (job,) = plan(period, {"L3-Q1": "x"}, [("falsa", "m")], 1, None)
    assert isinstance(job, Job)
    assert job.list_number == 3
