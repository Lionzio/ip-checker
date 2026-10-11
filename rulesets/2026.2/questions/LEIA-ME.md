# Regras por questão do período 2026.2 (R-01)

Cada arquivo `L<lista>-Q<número>.yaml` desta pasta guarda o que o enunciado de uma questão permite
ou proíbe explicitamente. As regras da questão prevalecem sobre as da lista (C-02), e a questão
aparece no seletor da página assim que o ruleset é publicado.

Estão cadastradas a questão do ensaio do cadastro (L3-Q9, `docs/ensaio-cadastro.md`) e a L4-Q3,
a primeira questão real, cujo enunciado libera `eval()`. O passo a passo do cadastro, com um exemplo comentado,
está em [`RULES.md`](../../../RULES.md), na raiz do repositório. Antes de abrir o PR, rode:

```bash
cd backend
uv run ipc-rules validate ../rulesets/2026.2
```
