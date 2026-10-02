"""Gabaritos de períodos anteriores (Q-14, S20): cada um deve ter zero violação na sua lista.

Os gabaritos são respostas oficiais e nunca entram neste repositório: ficam num repositório privado
separado, que a CI baixa com um token só de leitura para ``IPC_GABARITOS_DIR``. Organização:

    <IPC_GABARITOS_DIR>/
    ├── <período>/lista-<n>/<questão>.py      ex.: 2025.2/lista-2/q03.py
    └── excecoes.yaml                          opcional

Até as regras por questão (Sprint 24), um gabarito pode usar algo que só o enunciado libera. Nesse
caso, o ``excecoes.yaml`` diz quais regras o enunciado libera naquele arquivo, e por quê:

    "2025.2/lista-2/q03.py":
      regras: ["R-37"]
      motivo: "o enunciado pede zip() fora do for"

O resultado traz só o caminho do arquivo, a regra e a linha, nunca o código.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.ruleset import CompiledRuleset

EXCEPTIONS_FILE = "excecoes.yaml"
_LIST_DIR = re.compile(r"lista-([1-6])")
_RULE_ID = re.compile(r"R-\d{2}")


@dataclass(frozen=True, slots=True)
class Gabarito:
    #: Caminho relativo à raiz, sempre com "/", que também identifica o caso no pytest.
    path: str
    list_number: int
    file: Path


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
    result = analyze_source(source, list_number=gabarito.list_number, ruleset=ruleset)
    if result.syntax_error is not None:
        return [f"erro de sintaxe na linha {result.syntax_error.line}"]
    return [
        f"{violation.rule_id} linha {violation.line}"
        for violation in result.violations
        if violation.rule_id not in allowed
    ]
