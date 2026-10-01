"""Guarda do NFR-09: o código-fonte do projeto nunca executa nem importa código de terceiros.

A varredura analisa a AST de cada arquivo em ``src/`` e falha se encontrar construções que
poderiam executar o código do aluno ou desserializar dados de forma insegura. O ruff (regras S)
cobre parte disso; este teste cobre também ``import ast`` fora do motor e ``yaml.load``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
ENGINE = SRC / "ipc_analyzer" / "engine"

FORBIDDEN_CALLS = frozenset({"eval", "exec", "compile", "__import__", "breakpoint"})
FORBIDDEN_MODULES = frozenset(
    {"pickle", "marshal", "shelve", "subprocess", "importlib", "runpy", "code", "codeop"}
)
UNSAFE_YAML = frozenset({"load", "load_all", "unsafe_load", "full_load", "unsafe_load_all"})


def find_violations(source: str, *, ast_allowed: bool) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                violations.append(f"linha {node.lineno}: chamada a {func.id}()")
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "yaml"
                and func.attr in UNSAFE_YAML
            ):
                violations.append(f"linha {node.lineno}: yaml.{func.attr}() (use yaml.safe_load)")
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module]
        else:
            continue
        for module in modules:
            root = module.split(".")[0]
            if root in FORBIDDEN_MODULES:
                violations.append(f"linha {node.lineno}: import de {module}")
            if root == "ast" and not ast_allowed:
                violations.append(f"linha {node.lineno}: import de ast fora do motor")
    return violations


def _source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_source_tree_is_not_empty() -> None:
    assert _source_files()


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: p.relative_to(SRC).as_posix())
def test_source_file_has_no_execution_paths(path: Path) -> None:
    source = path.read_text(encoding="utf-8")

    assert find_violations(source, ast_allowed=path.is_relative_to(ENGINE)) == []


@pytest.mark.parametrize(
    "snippet",
    [
        "eval('1')",
        "exec('x = 1')",
        "compile('1', 'f', 'eval')",
        "__import__('os')",
        "import pickle",
        "from subprocess import run",
        "import importlib.util",
        "import yaml\nyaml.load(data)",
        "import ast",
    ],
)
def test_guard_detects_forbidden_constructs(snippet: str) -> None:
    assert find_violations(snippet, ast_allowed=False)


def test_guard_allows_ast_inside_engine() -> None:
    assert find_violations("import ast\nimport yaml\nyaml.safe_load(b'')", ast_allowed=True) == []
