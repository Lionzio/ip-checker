# Sprint 41 — Fase 2: imagens no GHCR, deploy pelo servidor do CIn e staging (bloqueada)

Do blueprint até 15/10/2026, seção 7.15 (plano de polimento de 11/10/2026); o plano comum está no [README](README.md).

**Prioridade (P-24, 15/10/2026):** a última da fila, depois de todas as outras sprints. A entrada no servidor do CIn depende da apresentação e da validação com monitores, monitores-chefe, professores, coordenadores e diretores; o piloto de 2027.1 deve rodar no Render e na Vercel, e a transição vem depois.

Era a Sprint 36 do plano de 07/10/2026, renumerada em 11/10/2026 (as tasks S36-01 a S36-04 passaram a S41-01 a S41-04).

**Objetivo:** preparar a Fase 2 da ADR-03, só se a P-09 for atingida e a Q-12 for respondida pelo suporte de TI do CIn: imagens publicadas no GHCR por digest, deploy *pull-based* no servidor do CIn e um ambiente de staging.

**Missão, persona e execução:** a missão é preparar a Fase 2 no servidor do CIn, só se a P-09 for atingida e a Q-12 respondida. As personas são o monitor-mantenedor e o suporte de TI do CIn (US-20, US-23). Execução: as decisões S41-01 e S41-02 primeiro; só então o GHCR e o deploy (S41-03, S41-04).

**Premissas:** P-09 (critérios de eficácia), Q-12 (requisitos do CIn), ADR-03 (Fase 2).

**Histórias:** US-20 e US-23 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S41-01 | US-23 | Decisão | Migrar ou não para o servidor do CIn, com o relatório de eficácia de 2027.1 (P-09, `docs/eficacia.md`) | `docs/eficacia.md`, ADR-03 | Coordenação | — | Fim de 2027.1 | Desbloqueio: decisão registrada na P-09 |
| S41-02 | US-20 | Externa | Q-12: o suporte de TI do CIn responde Docker, porta 443, subdomínio e TLS, saída para o PostgreSQL gerenciado e quem administra o sistema | `docs/decisoes.md` (Q-12) | TI do CIn | — | S41-01 | Desbloqueio: Q-12 respondida por escrito |
| S41-03 | US-20 | Engenharia | Publicar as imagens no GHCR com a tag igual ao SHA e referenciá-las por digest no compose | `.github/workflows/ci.yml`, `deploy/compose.yaml` | Autor | 2 | S41-01 | `docker compose pull` com digests; o item do GHCR da seção 8 sem [PLANEJADO] |
| S41-04 | US-20 | Engenharia | Deploy *pull-based* no servidor do CIn e ambiente de staging, com o mesmo `/ready` e as verificações de `tests/pilot` apontadas para lá | `deploy/` (novo roteiro), `.github/workflows/deploy.yml` | Autor | 3 | S41-02, S41-03 | Staging e produção verdes nas verificações; rollback ≤ 5 min ensaiado no servidor |

**ADRs:** atualiza o ADR-03 (Fase 2).

**Critérios de aceite:**
1. As imagens são publicadas por digest.
2. Staging e produção passam nas mesmas verificações do piloto.
3. O rollback no servidor leva ≤ 5 min.

**Testes:** a base de 7.12.1; as verificações de `tests/pilot` apontadas para o staging e a produção; o ensaio de rollback e a restauração do backup no servidor; a suíte de isolamento do NFR-07 no compose do servidor.

**Definition of Done:** a da seção 8, com os itens de implantação da Fase 2 sem [PLANEJADO].

**Riscos e bloqueios:** a sprint inteira está bloqueada pela P-09 e pela Q-12 e só é detalhada depois do piloto.
