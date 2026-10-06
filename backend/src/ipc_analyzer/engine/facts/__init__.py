"""Extração de fatos da AST (5.2.3): cada construção do código vira um fato ``<tipo>:<nome>``.

- ``model``: o ``Fact`` e o mapa de posições;
- ``extractor``: a travessia iterativa, que emite os fatos e marca o cabeçalho do ``for``;
- ``callgraph``: o grafo de chamadas entre as funções do aluno, para a recursão (R-68, C-03).
"""

from __future__ import annotations

from ipc_analyzer.engine.facts.extractor import extract_facts
from ipc_analyzer.engine.facts.model import Fact

__all__ = ["Fact", "extract_facts"]
