"""Gerador das soluções de referência por IA (S42-04, que era a S33-09; ADR-08, Q-35).

A partir **só do enunciado** de cada questão, pede soluções a cada IA da cadeia do "Aprimorar com
IA" (``IPC_LLM_CHAIN``, como gemini,groq) e grava uma por arquivo, com um cabeçalho de comentário
(IA, modelo e data). Nenhum código de aluno entra no pedido. Dois usos, de ``backend/``:

    # As referências do sinal 5, no repositório, para a equipe revisar por PR:
    uv run python -m ipc_api.referencias ../rulesets/2026.2 --enunciados ../../enunciados/2026.2 \\
        --env-file ../../chaves-ia.env

    # Soluções novas para a calibração (S42-02), fora do repositório, diferentes das referências:
    uv run python -m ipc_api.referencias ../rulesets/2026.2 --enunciados ../../enunciados/2026.2 \\
        --env-file ../../chaves-ia.env --para-calibracao ../../calibracao --por-ia 3

Os enunciados ficam fora do repositório, um arquivo por questão: ``L1-Q2.md`` (ou ``.txt``). As
chaves vêm do ambiente ou do ``--env-file`` e nunca aparecem na saída. Um arquivo que já existe é
pulado: rodar de novo retoma de onde parou (a cota das IAs gratuitas acaba no meio). A saída mostra
só os caminhos gravados e as falhas, nunca o código.

Fica no pacote da API, e não no ``ipc-rules``, porque o analisador é isolado e não chama a rede
(as fronteiras do ``lint-imports``). Pelo mesmo motivo, e porque nada no projeto compila nem executa
código (ADR-01, regra ``python-eval-exec`` do Semgrep), o gerador não confere a sintaxe: grava o
bloco ```python da resposta, e o ``ipc-rules validate`` recusa uma referência inválida (a
calibração conta uma solução com erro de sintaxe como recusada).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

from ipc_api.feedback.providers import (
    LlmSettings,
    Prompt,
    Provider,
    ProviderError,
    build_provider,
)

QUESTION = re.compile(r"^L(?P<list>[1-6])-Q[1-9]\d?$")
PERIOD = re.compile(r"^\d{4}\.[12]$")
STATEMENT_SUFFIXES = (".md", ".txt")
#: Um enunciado maior que isso não é um enunciado das listas. Era 20 KB até a Sprint 42.1, quando
#: os enunciados reais de 2026.2, vindos do catálogo (Sprint 50), chegaram a 25 KB (L4-Q5).
MAX_STATEMENT_BYTES = 40_000
#: O mesmo limite de uma submissão (50 KB): uma resposta maior não é uma solução das listas.
MAX_SOLUTION_BYTES = 51_200
#: As referências cabem no carregador: até 10 por questão (MAX_REFERENCES_PER_QUESTION).
MAX_PER_AI = 5
#: Resposta longa o bastante para um programa completo. Era 2.048 até a Sprint 42.1: os modelos que
#: raciocinam antes de responder (gpt-oss no Groq, Gemini) gastavam o limite no raciocínio e a
#: resposta vinha cortada, sem o bloco de código, nos enunciados maiores.
MAX_OUTPUT_TOKENS = 8_192
#: Depois de um 413 (pedido grande demais para o limite de tokens por minuto da IA, como os
#: 8 mil do Groq gratuito, que conta o teto da resposta), tenta de novo com estes tetos menores.
SMALLER_OUTPUT_TOKENS = (4_096, 2_048)
#: Uma resposta de até 8 mil tokens, com o raciocínio, leva mais que os 60 s de antes.
TIMEOUT_S = 120.0
#: Depois de um 429 (cota), espera e tenta de novo, até ``RETRIES`` vezes.
WAIT_S = 60.0
RETRIES = 3

SYSTEM = (
    "Você resolve questões de uma disciplina de Introdução à Programação em Python 3. Escreva um "
    "programa completo que lê da entrada padrão com input() e escreve na saída padrão com print(), "
    "exatamente no formato que o enunciado pede. Responda só com o código, num único bloco "
    "```python, sem explicações."
)
_FENCE = re.compile(r"```(?:python|py)?[ \t]*\r?\n(?P<code>.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Job:
    question: str
    list_number: int
    statement: str
    ai: str
    model: str
    number: int
    target: Path


@dataclass(slots=True)
class Report:
    written: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def read_env_file(path: Path) -> dict[str, str]:
    """``CHAVE=valor`` por linha, como o ``deploy/.env`` do compose; comentários e linhas vazias
    ficam de fora. Os valores nunca são mostrados."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def statements(folder: Path, only: str | None = None) -> dict[str, str]:
    """Os enunciados da pasta, por questão; ``only`` limita a uma."""
    found: dict[str, str] = {}
    for file in sorted(folder.iterdir()):
        if file.suffix not in STATEMENT_SUFFIXES or not QUESTION.fullmatch(file.stem):
            continue
        if only is not None and file.stem != only:
            continue
        if file.stat().st_size > MAX_STATEMENT_BYTES:
            raise ValueError(f"{file.name}: enunciado acima de {MAX_STATEMENT_BYTES} bytes")
        text = file.read_text(encoding="utf-8-sig").strip()
        if text:
            found[file.stem] = text
    return found


def prompt_for(job: Job, total: int) -> Prompt:
    """Só o enunciado, delimitado; a variação pede abordagens diferentes entre as soluções."""
    variation = (
        f"Esta é a solução {job.number} de {total}: escreva-a do seu jeito, sem copiar uma "
        "solução anterior.\n\n"
        if total > 1
        else ""
    )
    user = (
        f"{variation}Questão {job.question} (Lista {job.list_number}). Enunciado entre as marcas:\n"
        f"<<<ENUNCIADO\n{job.statement}\nENUNCIADO>>>"
    )
    return Prompt(system=SYSTEM, user=user, max_output_tokens=MAX_OUTPUT_TOKENS)


def extract_code(text: str) -> str | None:
    """O código do primeiro bloco ```python da resposta; ``None`` sem o bloco, com ele vazio ou
    acima de 50 KB. A sintaxe fica para o ``ipc-rules validate``."""
    match = _FENCE.search(text)
    if match is None:
        return None
    code = match.group("code").strip("\n")
    if not code.strip() or len(code.encode()) > MAX_SOLUTION_BYTES:
        return None
    return code + "\n"


def header(job: Job, when: datetime) -> str:
    return (
        f"# Solução gerada por IA (S42-04, ADR-08): {job.ai}, modelo {job.model}, "
        f"{when:%d/%m/%Y}.\n"
        f"# Só a partir do enunciado da {job.question}, sem nenhum código de aluno. Revise antes "
        "do merge.\n"
    )


def plan(
    period_dir: Path,
    texts: Mapping[str, str],
    ais: Sequence[tuple[str, str]],
    per_ai: int,
    calibration: Path | None,
) -> list[Job]:
    """Os arquivos a gerar: em ``referencias/<questão>/<ia>-<n>.py`` ou, para a calibração, em
    ``<pasta>/<período>/lista-<n>/<questão>-<ia>-<n>.py`` (o formato do ``ipc-rules calibrate``)."""
    jobs = []
    for question, statement in texts.items():
        match = QUESTION.fullmatch(question)
        assert match is not None  # noqa: S101 - statements() só devolve questões no formato
        list_number = int(match.group("list"))
        for ai, model in ais:
            for number in range(1, per_ai + 1):
                if calibration is None:
                    target = period_dir / "referencias" / question / f"{ai}-{number}.py"
                else:
                    folder = calibration / period_dir.name / f"lista-{list_number}"
                    target = folder / f"{question}-{ai}-{number}.py"
                jobs.append(Job(question, list_number, statement, ai, model, number, target))
    return jobs


async def generate(
    jobs: Sequence[Job],
    providers: Mapping[str, Provider],
    per_ai: int,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    wait_s: float = WAIT_S,
) -> Report:
    report = Report()
    exhausted: set[str] = set()
    for job in jobs:
        if job.target.exists():
            report.skipped.append(job.target)
            continue
        if job.ai in exhausted:
            report.failed.append(f"{job.question} {job.ai}-{job.number}: cota esgotada")
            continue
        text = None
        prompt = prompt_for(job, per_ai)
        smaller = list(SMALLER_OUTPUT_TOKENS)
        attempt = 0
        while True:
            try:
                text = await providers[job.ai].generate(prompt, timeout_s=TIMEOUT_S)
                break
            except ProviderError as exc:
                if exc.status == 413 and smaller:
                    prompt = replace(prompt, max_output_tokens=smaller.pop(0))
                    continue
                if exc.status == 429 and attempt < RETRIES:
                    attempt += 1
                    await sleep(wait_s)
                    continue
                if exc.status == 429:
                    exhausted.add(job.ai)
                report.failed.append(f"{job.question} {job.ai}-{job.number}: {exc}")
                break
        if text is None:
            continue
        code = extract_code(text)
        if code is None:
            report.failed.append(f"{job.question} {job.ai}-{job.number}: sem bloco de código")
            continue
        job.target.parent.mkdir(parents=True, exist_ok=True)
        job.target.write_text(header(job, now()) + code, encoding="utf-8", newline="\n")
        report.written.append(job.target)
    return report


def main(argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ipc_api.referencias",
        description="Gera soluções de referência por IA a partir só dos enunciados (S42-04).",
    )
    parser.add_argument("period", type=Path, help="a pasta do período, como ../rulesets/2026.2")
    parser.add_argument(
        "--enunciados", type=Path, required=True, help="pasta com L<n>-Q<m>.md, fora do repositório"
    )
    parser.add_argument("--questao", help="só esta questão, como L1-Q2")
    parser.add_argument("--env-file", type=Path, help="arquivo com IPC_LLM_CHAIN e as chaves")
    parser.add_argument(
        "--por-ia", type=int, default=2, help=f"soluções por IA (1 a {MAX_PER_AI}; padrão: 2)"
    )
    parser.add_argument(
        "--para-calibracao",
        type=Path,
        help="grava soluções novas para a calibração nesta pasta, fora do repositório",
    )
    args = parser.parse_args(argv)
    period_dir: Path = args.period
    if not PERIOD.fullmatch(period_dir.name) or not (period_dir / "base.yaml").is_file():
        return _fail(f"{period_dir.as_posix()} não é a pasta de um período (falta o base.yaml)")
    if not 1 <= args.por_ia <= MAX_PER_AI:
        return _fail(f"--por-ia vai de 1 a {MAX_PER_AI}")
    if args.questao is not None and not QUESTION.fullmatch(args.questao):
        return _fail(f"questão inválida: {args.questao!r} (use o formato L1-Q2)")
    if not args.enunciados.is_dir():
        return _fail(f"{args.enunciados.as_posix()} não é uma pasta de enunciados")
    env = dict(environ if environ is not None else os.environ)
    if args.env_file is not None:
        if not args.env_file.is_file():
            return _fail(f"{args.env_file.as_posix()} não existe")
        env = {**read_env_file(args.env_file), **env}
    try:
        settings = LlmSettings.from_env(env)
        texts = statements(args.enunciados, args.questao)
    except ValueError as exc:
        return _fail(str(exc))
    configured = settings.configured
    if not configured:
        return _fail(
            "nenhuma IA configurada: defina IPC_LLM_CHAIN e as variáveis de cada IA "
            "(IPC_LLM_GEMINI_PROVIDER, ..._MODEL, ..._API_KEY) no ambiente ou no --env-file"
        )
    if not texts:
        return _fail(f"nenhum enunciado em {args.enunciados.as_posix()} (use L1-Q2.md)")
    providers: dict[str, Provider] = {}
    for name, config in configured:
        provider = build_provider(config)
        if provider is not None:
            providers[name] = provider
    ais = [(name, config.model or config.provider or "?") for name, config in configured]
    jobs = plan(period_dir, texts, ais, args.por_ia, args.para_calibracao)
    report = asyncio.run(generate(jobs, providers, args.por_ia))
    for path in report.written:
        print(f"gravado: {path.as_posix()}")
    print(
        f"{len(report.written)} gravados, {len(report.skipped)} já existiam, "
        f"{len(report.failed)} falharam ({len(texts)} questões, {len(providers)} IAs)"
    )
    for line in report.failed:
        print(f"  falhou: {line}")
    if report.failed:
        print("rode de novo para retomar: os arquivos gravados são pulados")
    return 1 if report.failed else 0


def _fail(message: str) -> int:
    print(f"erro: {message}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
