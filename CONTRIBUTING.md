# Como contribuir

Para quem vai mexer no código, nas regras ou na documentação do IP-Checker. Quem está chegando
começa pelo [`docs/onboarding.md`](docs/onboarding.md), que sobe o ambiente do zero.

## Que tipo de mudança é

| Mudança | Por onde | Quem aprova |
|---|---|---|
| Regras de uma questão (`rulesets/<período>/questions/`) | [`RULES.md`](RULES.md), com o modelo de PR de regras | Monitor-chefe ou professor (conferido por quem faz o merge; Q-22) |
| Regras de uma lista (`rulesets/<período>/base.yaml`) | Só a partir do documento de permissões; [`rulesets/README.md`](rulesets/README.md) | Professor |
| Código, testes, deploy e documentação | Este arquivo | O desenvolvedor, com a CI verde |

Nenhuma regra de permissão é escrita em código: o motor só lê `rulesets/**` (ADR-02).

## Branches e PRs

- A `develop` é a branch principal. Cada mudança nasce numa branch a partir dela
  (`feature/S28-01-carga`, `fix/...`, `docs/...`) e volta por PR.
- O PR usa o modelo (`.github/pull_request_template.md`): o que muda, com o ID da task e dos itens
  do blueprint, e o checklist de autorrevisão.
- O merge é *squash*, com a CI verde. Um PR que só muda arquivos `.md` não roda os testes (a CI
  decide sozinha; S28-04).
- A `main` só avança por *fast-forward* da `develop`, com o `scripts/release.sh`, que também cria a
  tag `sprint-NN` e o GitHub Release. Cada push na `main` faz o deploy do piloto depois da CI.

## Antes de abrir o PR

No `backend/`:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports && uv run pytest
```

No `frontend/`:

```bash
npm run lint && npm run typecheck && npm test && npm run build
```

Se mudou a API, regenere o contrato e os tipos (o job do frontend confere):

```bash
cd backend && uv run python -m ipc_api.openapi ../docs/openapi.json && cd ../frontend && npm run gen:api
```

O e2e completo (compose + Playwright) está no [onboarding](docs/onboarding.md), passo 5.

## Regras da casa

- **O código do aluno nunca roda e nunca é guardado.** Nada de `eval`, `exec`, `compile`,
  `__import__`, `pickle` ou `subprocess` sobre dados de requisição; `import ast` só no motor. A
  guarda de código (`backend/tests/test_code_guards.py`) e o ruff barram na CI.
- **Nada de código de aluno, IP ou segredo** em logs, testes, commits, *issues* ou PRs. Gabaritos
  oficiais ficam no repositório privado deles (Q-14).
- **Migrações só acrescentam** e sempre têm `.up.sql` e `.down.sql` testados. Uma migração aplicada
  nunca é editada: o `migrate` confere o SHA-256 de cada uma e recusa a que mudou (S28-04).
- **Português do Brasil** em mensagens, documentação e textos da página; código e nomes de
  variáveis podem ficar em inglês, como o resto do projeto.
- **Decisões:** uma premissa ou questão nova vai para [`docs/decisoes.md`](docs/decisoes.md); uma
  decisão de arquitetura, para um ADR em [`docs/adr/`](docs/adr/). O que cada sprint entregou vai
  para o [`CHANGELOG.md`](CHANGELOG.md).
- **Dados pessoais:** se mudar o que é guardado ou enviado a terceiros, o aviso de privacidade
  (`frontend/src/pages/Privacy.tsx`) muda junto.

Segurança: veja o [`SECURITY.md`](SECURITY.md) antes de relatar uma falha.
