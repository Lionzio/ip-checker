"""Importação do Dikastis (Sprint 50; ADR-15 e ADR-19): o catálogo das listas e o token.

A extensão do navegador lê o Dikastis com a sessão do monitor e envia ao IP-Checker pelas rotas
``/api/v1/import/*`` (``routes/importing.py``), com um token pessoal (``service.py``). O servidor
nunca fala com o Dikastis. O catálogo guarda só o que existe no Dikastis (turmas, listas e
questões, com o enunciado e os casos de exemplo); nenhum dado de aluno.
"""
