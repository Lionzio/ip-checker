## O que muda

<!-- Uma ou duas frases. Cite a task (ex.: S28-01) e os IDs do blueprint (R-xx, FR-xx, NFR-xx). Um PR de
regras de questão usa o outro modelo: acrescente ?template=regras.md ao endereço do PR. -->

## Como foi testado

<!-- O que rodou (pytest, Vitest, e2e, banco de teste, carga) e o que foi conferido à mão. -->

## Checklist de autorrevisão (Definition of Done, seção 8)

**Código e testes**

- [ ] A CI está verde (ruff, mypy strict, import-linter, pytest com cobertura ≥ 90%, ESLint, tsc, Vitest, e2e).
- [ ] Nenhuma regra de permissão foi escrita fora de `rulesets/**`; todo `R-xx` citado existe no catálogo.
- [ ] Regra criada ou alterada tem casos golden (permitido na lista certa, proibido antes, evasão quando couber).
- [ ] Nada de `eval`, `exec`, `compile`, `__import__`, `pickle`, `subprocess` nem `yaml.load`; `import ast` só no motor.
- [ ] Mudou o caminho da requisição? A carga (`deploy/load/run_load.py` ou o workflow "Carga no piloto") não piorou o P95.

**Dados e segurança**

- [ ] Nenhum código de aluno, IP ou segredo aparece em logs, testes, commits ou neste PR.
- [ ] Gabaritos não foram adicionados a este repositório (Q-14).
- [ ] Mudou o que é guardado ou enviado a terceiros? O aviso de privacidade (`Privacy.tsx`) mudou junto.
- [ ] Migração nova tem `.up.sql` e `.down.sql` testados, só acrescenta, e nenhuma migração aplicada foi editada.
- [ ] Segredo novo existe só no ambiente da `api`, nunca no do `analyzer` nem no build da página.

**Contrato e documentação**

- [ ] Mudou a API? `docs/openapi.json` e `frontend/src/types/openapi.ts` foram regenerados.
- [ ] O `CHANGELOG.md` tem a entrega desta sprint, com as decisões de implementação.
- [ ] Premissa ou questão nova vai em `docs/decisoes.md`; decisão de arquitetura, num ADR em `docs/adr/`.
- [ ] READMEs, runbook, `deploy/*.md` e `docs/mapping-R-xx.md` foram atualizados quando necessário.
- [ ] Nenhum controle é descrito como ativo sem existir; o que falta está marcado [PLANEJADO].
