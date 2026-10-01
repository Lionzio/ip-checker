"""API pública do IP-Checker (S8-01): recebe o código do aluno e pede a análise ao ``analyzer``.

A API nunca analisa nem executa código: ela valida a entrada, chama o serviço interno por HTTP e
valida a resposta dele, que trata como vinda de um processo potencialmente contaminado (TB-3).
O contrato ``import-linter`` do ``pyproject.toml`` garante que este pacote não importa ``ast``
nem o ``ipc_analyzer``.
"""
