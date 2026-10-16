"""A carga do ruleset do disco (S31-09): o período ativo, as questões e as referências por IA."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType

import yaml
from pydantic import (
    ValidationError,
)

from ipc_analyzer.engine.guards import InputError
from ipc_analyzer.engine.parse import SyntaxProblem, parse_source

from .compile import (
    CompiledQuestion,
    CompiledRuleset,
    Reference,
    RulesetError,
    compile_question,
    compile_ruleset,
)
from .schema import Question, Ruleset

#: Arquivo do ruleset de um período, em ``rulesets/<período>/``.
BASE_FILE = "base.yaml"
#: Na raiz de ``rulesets/``, a única linha com o período ativo (``2026.2``). Trocar de período é
#: mudar só essa linha: o analisador, o ``ipc-rules`` e a CI apontam para a raiz (S31-09).
ACTIVE_FILE = "ATIVO"
PERIOD = re.compile(r"\d{4}\.[12]")
#: Quantos períodos o analisador carrega: o ativo e os 5 anteriores, 3 anos (ADR-12, Q-34).
WINDOW = 6
#: Pasta, na raiz ``rulesets/``, dos períodos encerrados (S43-04): nunca carregados.
RETIRED_DIR = "encerrados"
#: Pasta das regras por questão, ao lado do ``base.yaml`` (R-01, P-07).
QUESTIONS_DIR = "questions"
#: Pasta das soluções de referência geradas por IA, uma subpasta por questão (S29-02).
REFERENCES_DIR = "referencias"
#: Uma questão guarda poucas referências: 2 ou 3 assistentes, uma ou duas soluções cada (ADR-08).
MAX_REFERENCES_PER_QUESTION = 10


def active_period(root: Path) -> str:
    """O período ativo, lido do arquivo ``ATIVO`` da raiz ``rulesets/`` (S31-09)."""
    file = root / ACTIVE_FILE
    try:
        period = file.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise RulesetError(f"não foi possível ler o período ativo {file}: {exc}") from exc
    if not PERIOD.fullmatch(period):
        raise RulesetError(
            f"período ativo inválido em {file}: {period!r} (use o formato 2026.2, uma linha só)"
        )
    if not (root / period / BASE_FILE).is_file():
        raise RulesetError(f"período ativo {period} sem {root / period / BASE_FILE}")
    return period


def resolve_ruleset_path(path: Path) -> Path:
    """O ``base.yaml`` a carregar: aceita o próprio arquivo, a pasta de um período ou a raiz
    ``rulesets/``, que tem o arquivo ``ATIVO`` e aponta para o período ativo (S31-09)."""
    if not path.is_dir():
        return path
    if (path / ACTIVE_FILE).exists():
        return path / active_period(path) / BASE_FILE
    return path / BASE_FILE


def load_ruleset(path: Path) -> CompiledRuleset:
    """Lê, valida e compila o ruleset e as questões da pasta ``questions/`` ao lado dele.

    ``path`` é o ``base.yaml``, a pasta do período ou a raiz ``rulesets/`` (período ativo).
    Qualquer problema, num arquivo só que seja, vira ``RulesetError`` (fail-fast, FR-15).
    """
    path = resolve_ruleset_path(path)
    raw, data = _read_yaml(path, "o ruleset")
    try:
        ruleset = Ruleset.model_validate(data)
    except ValidationError as exc:
        raise RulesetError(_describe(exc, path, "ruleset inválido")) from exc
    folder_period = path.parent.name
    if PERIOD.fullmatch(folder_period) and folder_period != ruleset.period:
        raise RulesetError(
            f"ruleset inválido: {path}\n  - period: {ruleset.period} numa pasta do período "
            f"{folder_period}"
        )
    digest = hashlib.sha256(raw)
    questions: list[CompiledQuestion] = []
    folder = path.parent / QUESTIONS_DIR
    files = sorted(folder.glob("*.yaml")) if folder.is_dir() else []
    for file in files:
        question_raw, question_data = _read_yaml(file, "a questão")
        digest.update(b"\0" + file.name.encode() + b"\0" + question_raw)
        try:
            question = Question.model_validate(question_data)
        except ValidationError as exc:
            raise RulesetError(_describe(exc, file, "questão inválida")) from exc
        if file.stem != question.question_id:
            raise RulesetError(
                f"questão inválida: {file}\n  - question_id: {question.question_id} precisa "
                f"estar no arquivo {question.question_id}.yaml"
            )
        try:
            questions.append(compile_question(question, ruleset))
        except ValueError as exc:
            raise RulesetError(f"questão inválida: {file}\n  - {exc}") from exc
    compiled = compile_ruleset(ruleset, raw, questions)
    references = _load_references(path.parent / REFERENCES_DIR, compiled, digest)
    return replace(compiled, sha256=digest.hexdigest(), references=references)


class UnknownPeriod(Exception):  # noqa: N818 - é um estado, não um erro de programação
    """O período pedido não está entre os carregados (encerrado, futuro ou inexistente)."""

    def __init__(self, period: str, loaded: tuple[str, ...]) -> None:
        super().__init__(period)
        self.period = period
        self.loaded = loaded


@dataclass(frozen=True, slots=True)
class LoadedRulesets:
    """Os rulesets carregados (S43-01): o ativo e os anteriores da janela, do mais novo ao mais
    antigo. Sem período no pedido, vale o ativo, como antes."""

    active: str
    periods: Mapping[str, CompiledRuleset]

    def get(self, period: str | None = None) -> CompiledRuleset:
        """O ruleset do período; ``None`` é o ativo. Fora da janela, ``UnknownPeriod``."""
        ruleset = self.periods.get(self.active if period is None else period)
        if ruleset is None:
            raise UnknownPeriod(period or self.active, tuple(self.periods))
        return ruleset

    @property
    def active_ruleset(self) -> CompiledRuleset:
        return self.periods[self.active]


def load_rulesets(path: Path, window: int = WINDOW) -> LoadedRulesets:
    """Carrega o período ativo e os até ``window - 1`` anteriores presentes em ``rulesets/``.

    ``path`` é a raiz ``rulesets/`` (com o ``ATIVO``) ou, como em ``load_ruleset``, o ``base.yaml``
    ou a pasta de um período só: aí vem só ele. Os períodos posteriores ao ativo (em preparação,
    como o 2027.1 antes da troca) e a pasta ``encerrados/`` ficam de fora. Qualquer período
    inválido impede a subida (fail-fast, FR-15), como antes com o ativo.
    """
    if not (path.is_dir() and (path / ACTIVE_FILE).exists()):
        single = load_ruleset(path)
        return LoadedRulesets(
            single.ruleset.period, MappingProxyType({single.ruleset.period: single})
        )
    active = active_period(path)
    names = sorted(
        (
            entry.name
            for entry in path.iterdir()
            if entry.is_dir()
            and entry.name != RETIRED_DIR
            and PERIOD.fullmatch(entry.name)
            and entry.name <= active
            and (entry / BASE_FILE).is_file()
        ),
        reverse=True,
    )[:window]
    periods = {name: load_ruleset(path / name / BASE_FILE) for name in names}
    return LoadedRulesets(active, MappingProxyType(periods))


def _load_references(
    folder: Path, compiled: CompiledRuleset, digest: hashlib._Hash
) -> Mapping[str, tuple[Reference, ...]]:
    """Lê ``referencias/<questão>/*.py``: cada subpasta é uma questão cadastrada, e cada arquivo
    precisa ser Python válido dentro dos mesmos limites de uma submissão (S29-02)."""
    if not folder.is_dir():
        return MappingProxyType({})
    found: dict[str, tuple[Reference, ...]] = {}
    for question_folder in sorted(path for path in folder.iterdir() if path.is_dir()):
        question_id = question_folder.name
        if question_id not in compiled.questions:
            raise RulesetError(
                f"referências inválidas: {question_folder}\n  - a questão {question_id} não está "
                f"cadastrada em {QUESTIONS_DIR}/"
            )
        files = sorted(question_folder.glob("*.py"))
        if len(files) > MAX_REFERENCES_PER_QUESTION:
            raise RulesetError(
                f"referências inválidas: {question_folder}\n  - {len(files)} arquivos; o limite é "
                f"{MAX_REFERENCES_PER_QUESTION} por questão"
            )
        references = []
        for file in files:
            try:
                raw = file.read_bytes()
                source = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise RulesetError(f"não foi possível ler a referência {file}: {exc}") from exc
            try:
                parsed = parse_source(source, target=compiled.target_version)
            except InputError as exc:
                raise RulesetError(f"referência inválida: {file}\n  - {exc.message}") from exc
            if isinstance(parsed, SyntaxProblem):
                raise RulesetError(
                    f"referência inválida: {file}\n  - linha {parsed.line}: {parsed.message}"
                )
            name = f"{question_id}/{file.name}"
            digest.update(b"\0" + name.encode() + b"\0" + raw)
            references.append(Reference(question_id=question_id, label=file.stem, source=source))
        if references:
            found[question_id] = tuple(references)
    return MappingProxyType(found)


def _read_yaml(path: Path, what: str) -> tuple[bytes, dict[str, object]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RulesetError(f"não foi possível ler {what} {path}: {exc}") from exc
    try:
        # safe_load: o YAML nunca constrói objetos Python arbitrários.
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise RulesetError(f"YAML inválido em {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RulesetError(f"{what} {path} deve ser um mapeamento YAML no nível raiz")
    return raw, data


def _describe(exc: ValidationError, path: Path, title: str) -> str:
    lines = [f"{title}: {path}"]
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "<raiz>"
        lines.append(f"  - {location}: {error['msg']}")
    return "\n".join(lines)
