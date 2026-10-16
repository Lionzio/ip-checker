"""Gabaritos de períodos anteriores (Q-14, S20): cada um deve ter zero violação na sua lista.

Os gabaritos são respostas oficiais e nunca entram neste repositório: ficam num repositório privado
separado, que a CI baixa com um token só de leitura para ``IPC_GABARITOS_DIR``. Organização:

    <IPC_GABARITOS_DIR>/
    ├── <período>/lista-<n>/<questão>.py      ex.: 2025.2/lista-2/q03.py
    └── excecoes.yaml                          opcional

Cada gabarito é analisado com o ruleset do seu período, ``rulesets/<período>/`` ou
``rulesets/encerrados/<período>/`` (S31-11, ADR-12), quando a pasta existe; senão, com o do período
ativo. No repositório dos gabaritos, um período encerrado pode ir para ``encerrados/<período>/``:
a API não o carrega, e a CI continua a conferi-lo com as regras dele (S43-05).

Um gabarito pode usar algo que só o enunciado libera: desde a Sprint 24, um gabarito cujo nome é
a questão (``2026.2/lista-3/L3-Q2.py``) é analisado com as regras dela, cadastradas em
``rulesets/<período>/questions/`` do mesmo período (R-01). Como a numeração reinicia a cada período
(P-07), um período sem pasta não tem questões cadastradas; para ele, o ``excecoes.yaml`` diz quais
regras o enunciado libera naquele arquivo, e por quê:

    "2025.2/lista-2/q03.py":
      regras: ["R-37"]
      motivo: "o enunciado pede zip() fora do for"

O resultado traz só o caminho do arquivo, a regra e a linha, nunca o código.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.ruleset import (
    BASE_FILE,
    QUESTION_ID,
    RETIRED_DIR,
    CompiledRuleset,
    load_ruleset,
)

EXCEPTIONS_FILE = "excecoes.yaml"
_LIST_DIR = re.compile(r"lista-([1-6])")
_RULE_ID = re.compile(r"R-\d{2}")
_PERIOD = re.compile(r"\d{4}\.[12]")


@dataclass(frozen=True, slots=True)
class Gabarito:
    #: Caminho relativo à raiz, sempre com "/", que também identifica o caso no pytest.
    path: str
    list_number: int
    file: Path

    @property
    def period(self) -> str | None:
        parts = self.path.split("/")
        # Um período encerrado (S43-05): encerrados/2023.1/lista-1/L1-Q1.py é de 2023.1.
        first = parts[1] if parts[0] == RETIRED_DIR and len(parts) > 1 else parts[0]
        return first if _PERIOD.fullmatch(first) else None

    @property
    def question_id(self) -> str | None:
        """A questão, quando o nome do arquivo é a numeração oficial (``L3-Q2.py``)."""
        return self.file.stem if QUESTION_ID.fullmatch(self.file.stem) else None


@dataclass(slots=True)
class PeriodRulesets:
    """O ruleset de cada período, carregado uma vez (S31-11): o de ``<rulesets>/<período>/`` ou o
    de ``<rulesets>/encerrados/<período>/`` (S43-05) se a pasta existe; senão, o ``active``."""

    rulesets: Path
    active: CompiledRuleset
    _loaded: dict[str, CompiledRuleset] = field(default_factory=dict)

    def for_gabarito(self, gabarito: Gabarito) -> CompiledRuleset:
        period = gabarito.period
        if period is None or period == self.active.ruleset.period:
            return self.active
        if period not in self._loaded:
            bases = (self.rulesets / period, self.rulesets / RETIRED_DIR / period)
            base = next((b / BASE_FILE for b in bases if (b / BASE_FILE).is_file()), None)
            self._loaded[period] = load_ruleset(base) if base is not None else self.active
        return self._loaded[period]


def discover(root: Path) -> tuple[list[Gabarito], list[str]]:
    """Os gabaritos encontrados e os arquivos ``.py`` fora de uma pasta ``lista-<n>``."""
    found: list[Gabarito] = []
    misplaced: list[str] = []
    for file in sorted(root.rglob("*.py")):
        relative = file.relative_to(root).as_posix()
        lists = [
            m.group(1)
            for part in file.parent.relative_to(root).parts
            if (m := _LIST_DIR.fullmatch(part))
        ]
        if len(lists) != 1:
            misplaced.append(relative)
            continue
        found.append(Gabarito(relative, int(lists[0]), file))
    return found, misplaced


def load_exceptions(root: Path) -> dict[str, frozenset[str]]:
    """Regras liberadas pelo enunciado, por arquivo; o arquivo de exceções é opcional."""
    path = root / EXCEPTIONS_FILE
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{EXCEPTIONS_FILE}: esperava um mapa de arquivo para regras e motivo")
    exceptions: dict[str, frozenset[str]] = {}
    for name, entry in data.items():
        if not isinstance(entry, dict) or set(entry) != {"regras", "motivo"}:
            raise ValueError(f"{EXCEPTIONS_FILE}: {name!r} precisa de 'regras' e 'motivo'")
        rules, reason = entry["regras"], entry["motivo"]
        if not isinstance(rules, list) or not rules:
            raise ValueError(f"{EXCEPTIONS_FILE}: {name!r} precisa de pelo menos uma regra")
        if not all(isinstance(rule, str) and _RULE_ID.fullmatch(rule) for rule in rules):
            raise ValueError(f"{EXCEPTIONS_FILE}: {name!r} tem uma regra fora do formato R-xx")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{EXCEPTIONS_FILE}: {name!r} precisa de um motivo")
        exceptions[str(name)] = frozenset(rules)
    return exceptions


def unexpected(
    gabarito: Gabarito, ruleset: CompiledRuleset, allowed: frozenset[str] = frozenset()
) -> list[str]:
    """O que o motor aponta no gabarito, fora das regras que o enunciado libera; vazio se passa."""
    source = gabarito.file.read_text(encoding="utf-8-sig")
    question = gabarito.question_id
    same_period = gabarito.period == ruleset.ruleset.period
    result = analyze_source(
        source,
        list_number=gabarito.list_number,
        ruleset=ruleset,
        question_id=question if same_period and question in ruleset.questions else None,
    )
    if result.syntax_error is not None:
        return [f"erro de sintaxe na linha {result.syntax_error.line}"]
    return [
        f"{violation.rule_id} linha {violation.line}"
        for violation in result.violations
        if violation.rule_id not in allowed
    ]
