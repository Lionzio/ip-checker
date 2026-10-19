# Sprint 42 — Indícios de IA ligados no piloto (incluída a pedido do autor em 12/10/2026)

Do blueprint até 15/10/2026, seção 7.16 (proposta de 12/10/2026); o plano comum está no [README](README.md).

**Objetivo:** que a equipe veja os indícios de uso de IA no piloto, calibrados, com a política já
aprovada (Q-21, 7.13.1, opção A).

**Missão:** que o monitor decida com quem conversar a partir de evidências ancoradas no documento
de permissões, sem que o painel possa ser lido como prova.

**Personas:** o membro da equipe que corrige e conversa com o aluno (US-34), a coordenação, dona da
política, e o monitor-mantenedor que calibra.

**Por que agora e o que a bloqueia:** o código está pronto desde a Sprint 29 e a política foi
aprovada em 09/10/2026. A política pedia a calibração com soluções humanas anteriores a 2023
(S33-02), mas o autor a descartou em 12/10/2026: essas soluções não existem e não serão buscadas.
Esta sprint reúne o que faltava da Sprint 33 (S33-03, S33-05, S33-06 e o gerador da S33-09,
aprovado em 12/10/2026) e acrescenta uma ligação gradual por cargo. Os critérios dos indícios e a
nova base de calibração foram aprovados pelo autor em 12/10/2026 (Q-35).

**Execução:**
1. Os critérios e a base de calibração validados pelo autor (S42-01, Q-35).
2. A calibração (S42-02) e, em paralelo, a evidência e a confiança em cada indício (S42-03).
3. As referências por IA das questões cadastradas (S42-04), que não bloqueiam a ligação: sem elas,
   o sinal de referência fica inerte e os outros funcionam.
4. A ligação gradual (S42-05): primeiro a chefia (desenvolvedor, professores e monitores-chefes),
   por uma lista; depois a equipe toda (S42-06).
5. O guia, o registro de casos e o runbook (S42-07).

**Histórias:** US-34.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S42-01 | US-34 | Decisão | Validar os critérios dos indícios e a base de calibração sem as soluções anteriores a 2023 (Q-35): os gabaritos da equipe para os alarmes falsos e soluções novas geradas por IA, diferentes das referências, para os acertos | `docs/indicios-de-ia.md`, ADR-08 | Autor | — | Q-35 | Feito em 12/10/2026 (Q-35): critérios e metas aprovados e registrados em `docs/indicios-de-ia.md`; pelo menos 200 soluções no total, entre gabaritos e soluções geradas por IA (premissa validada pelo autor em 12/10/2026) |
| S42-02 | US-34 | Engenharia | Calibração (era a S33-03): `ipc-rules calibrate` na base da S42-01, em cada período carregado; faixas de `engine/indicators.py` ajustadas por PR até as metas; a distribuição registrada no ADR-08 | `cli.py`, `engine/indicators.py`, ADR-08 | Autor | 2 | S42-01 | Nenhum gabarito na faixa alta e as metas de acerto da S42-01 cumpridas; `test_indicators.py` com as faixas novas |
| S42-03 | US-34 | Engenharia | Os critérios aprovados na Q-35: a repetição da mesma proibição passa a ir no máximo à faixa média, e entram dois marcadores sem faixa (texto dentro do `input()` e validação de entrada que o enunciado não pede). Cada indício passa a trazer a evidência (regra, linhas e um trecho de até 120 caracteres) e a confiança (baixa, média ou alta); o painel ganha um teste de vocabulário que recusa "prova", "veredito", "plagiou" e "usou IA" como afirmação | `engine/indicators.py`, `IndicatorsPanel.tsx`, OpenAPI | Autor | 2 | — | pytest e Vitest; contrato atualizado |
| S42-04 | US-34 | Engenharia e equipe | Referências por IA das questões cadastradas (era a S33-05), geradas a partir do enunciado pela cadeia do "Aprimorar com IA" (gerador da S33-09, aprovado em 12/10/2026) e revisadas por quem cadastra; as de 2027.1 saem com as questões, perto de março de 2027 | `cli.py`, `rulesets/<período>/referencias/` | Autor e equipe | 1 | S33-04 | `ipc-rules validate` mostra as referências em todas as questões cadastradas |
| S42-05 | US-34 | Engenharia | Ligação gradual: `IPC_AI_INDICATORS` aceita `0` (desligado), `chefia` (desenvolvedor, professores e monitores-chefes) e `1` (toda a equipe); a API só calcula e devolve o painel para os cargos ligados, e `/api/v1/auth/options` informa a cada conta se ela o vê | `settings.py`, `routes/validate.py`, `routes/auth.py`, `test_indicators_api.py` | Autor | 1 | — | Matriz cargo × valor testada por chamada direta; o feedback continua sem indícios |
| S42-06 | US-34 | Engenharia | Ligar no piloto (era a S33-06): um PR com `IPC_AI_INDICATORS: chefia` no `render.yaml`, a variável `PILOT_AI_INDICATORS` e o teste do piloto; depois de uma lista com o registro de casos, outro PR com `1` | `render.yaml`, `.github/workflows/deploy.yml`, `backend/tests/pilot/` | Autor | 0,5 | S42-02, S42-05 | Painel visível numa verificação com a conta de verificação; o sintético e o exercício de alerta depois de cada deploy |
| S42-07 | US-34 | Documentação | Guia da equipe (como ler o painel e conduzir a conversa, com as perguntas sugeridas), como a chefia registra, sem nome nem matrícula, os casos confirmados e descartados (sem a planilha, descartada em 12/10/2026), o runbook (desligar pela variável no Render, sem deploy de código) e o status da ADR-08 e de `docs/indicios-de-ia.md` | docs | Autor | 1 | — | Revisão pela coordenação |

**ADRs:** ADR-08 (status: ligado no piloto, com a calibração registrada).

**Critérios de aceite:**
1. Nenhum gabarito da equipe fica na faixa alta, e as metas de acerto validadas na Q-35 são cumpridas.
2. Com `chefia`, um monitor não recebe o painel, e um monitor-chefe recebe.
3. Com `1`, toda a equipe recebe o painel, e o feedback nunca leva os indícios.
4. Cada indício mostra a regra, as linhas, o trecho e a confiança, com o aviso de que não é prova.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Calibração | `ipc-rules calibrate` | À mão, a cada período | Sai com 0; a saída nunca mostra código |
| Ligação por cargo | pytest (matriz) | PR | `0`, `chefia` e `1` com o painel certo para cada cargo |
| Evidência e vocabulário | pytest e Vitest | PR | Todo indício com evidência; nenhum termo de veredito |
| Piloto | `tests/pilot` com `PILOT_AI_INDICATORS` | Depois do deploy | `ai_indicators` igual ao esperado |

**Deploy:** release `sprint-42`. A mudança do `render.yaml` publica sozinha no Render (sem migração
junto, P-18); a Vercel só se o painel mudar. Depois, o sintético e o exercício de alerta.

**Riscos:**
- O painel ser lido como prova: o texto, o guia e a ligação primeiro para a chefia reduzem o risco.
- A base humana é pequena (os gabaritos da equipe): as metas são revistas a cada lista, com o uso
  pela chefia.
- Desligar é imediato: a variável no Render volta a `0` sem deploy de código.

**Situação (16/10/2026):** parte 1 concluída na release `sprint-42` (#145): S42-03 (evidência e
confiança), S42-05 (ligação por cargo), S42-04 (o gerador, ainda sem as referências geradas), S42-02
(a calibração; alarmes falsos medidos nos 28 gabaritos de 2026.2, 0 na faixa alta) e S42-07 (os
documentos, a revisar pela coordenação). Decisões no `CHANGELOG.md`. O piloto segue com
`IPC_AI_INDICATORS=0`. Aguardando: os enunciados, que pelo plano de 16/10/2026 passam a
vir do catálogo da Sprint 50 (S50-06, o `.zip` dos enunciados), e as chaves das IAs, com o autor;
depois, a geração das referências (revisadas por PR), a meta de acertos e o `render.yaml` com
`chefia` (S42-06), numa `sprint-42.1`, logo depois da 50 (7.17). Desde a `sprint-50`, os
enunciados saem do botão **Baixar enunciados (.zip)** da tela "Listas do período" (um `L1-Q1.md`
por questão), descompactado na pasta do `--enunciados`, depois da primeira sincronização.

**Situação (17/10/2026):** parte 2 concluída na release `sprint-42.1` (#152 e #153): 102
referências de IA nas 34 questões das Listas 1 a 5 de 2026.2, a partir dos enunciados do catálogo
(S42-04); a calibração com as duas metas cumpridas (0 gabaritos na faixa alta e 83,0% das 206
soluções geradas na média ou alta; S42-02), depois de remover as 8 referências que repetiam o
gabarito; e `IPC_AI_INDICATORS: chefia` no `render.yaml` (S42-06), que liga o painel no deploy.
Falta: o deploy, a conferência do piloto com `PILOT_AI_INDICATORS=chefia`, o sintético, o
exercício de alerta e, depois de uma lista com o registro de casos, o PR com `1`.

**Situação (19/10/2026):** a `sprint-42.1` está no piloto desde 19/10/2026 (o Blueprint do Render
aplicou o `chefia`; `tests/pilot` com `PILOT_AI_INDICATORS=chefia`, 22 passaram). O último passo do
S42-06, o PR com `"1"` para toda a equipe, passa a ser a **S51-08** da Sprint 51 (opção A, decidida
pelo autor em 19/10/2026): sobe com a release da 51, depois de a chefia usar o painel por uma lista
inteira. Continuam pendentes o sintético e o exercício de alerta.
