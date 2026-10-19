"""Gabaritos pelo painel (Sprint 51; ADR-17): até dois por questão, "Notion" e "IP CC".

O banco é a fonte da verdade. A chefia cola o gabarito na tela "Gabaritos"; ao salvar, o
analisador o confere com as regras do período e da questão, e as violações ficam registradas. A
cópia em memória que a verificação e o plágio usam (``ipc_api.gabaritos.Gabaritos``) é atualizada
a cada escrita. O código de um gabarito só vai à chefia e ao desenvolvedor; nunca a um monitor, a
um log ou à telemetria (NFR-27).

Partes: ``models`` (os dados), ``store`` (o contrato e a versão em memória), ``postgres`` (o banco),
``service`` (as regras) e ``deps`` (as dependências do FastAPI); as rotas ficam em
``routes/gabaritos.py``.
"""
