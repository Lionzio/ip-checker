## O que muda

<!-- Uma ou duas frases. Cite a task (ex.: S1-02) e os IDs do blueprint (R-xx, FR-xx, NFR-xx). -->

## Checklist de autorrevisão (Definition of Done, seção 8)

- [ ] A CI está verde (ruff, mypy strict, pytest com cobertura ≥ 90% no motor).
- [ ] Nenhuma regra de permissão foi escrita fora de `rulesets/**`; todo `R-xx` citado existe no catálogo.
- [ ] Regra criada ou alterada tem casos golden (permitido na lista certa, proibido antes, evasão quando couber).
- [ ] Nada de `eval`, `exec`, `compile`, `__import__`, `pickle`, `subprocess` nem `yaml.load`; `import ast` só no motor.
- [ ] Nenhum código de aluno, IP ou segredo aparece em logs, testes ou commits.
- [ ] Gabaritos não foram adicionados a este repositório (Q-14).
- [ ] Documentação atualizada quando necessário (`docs/mapping-R-xx.md`, READMEs, blueprint).
