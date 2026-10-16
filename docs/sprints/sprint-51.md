# Sprint 51 — Gabaritos pelo painel (Notion e IP CC)

Do plano de 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md), seção 4.3); o plano comum está no [README](README.md).

**Objetivo:** cadastrar até dois gabaritos por questão, "Notion" e "IP CC", por cliques, validados ao salvar, com o banco como fonte da verdade e o repositório de gabaritos virando arquivo.

**Missão:** que um professor ou monitor-chefe registre o gabarito de uma questão em um minuto, sem Git, e saiba na hora se ele aciona alguma regra.

**Personas:** o membro da chefia que cadastra (US-50) e o membro da equipe que vê a comparação com o gabarito (US-51).

**Execução:**
1. A tabela e a API dos gabaritos, com a validação ao salvar (S51-01 e S51-02).
2. A comparação e o alerta de vazamento com os dois tipos (S51-03).
3. O spike da conta IP CC UFPE e o gabarito IP CC automático (S51-04).
4. A migração dos 28 gabaritos, o `export-gabaritos` e o arquivo do repositório (S51-05); a tela (S51-06) e os documentos (S51-07).

**Histórias:** US-50, US-51 e US-37.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S51-01 | US-50 | Engenharia | Tabela `gabaritos` (questão, `kind` em {`notion`, `ip_cc`}, código, origem painel ou Dikastis, quem, violações, data), com índice único por questão e tipo, e auditoria de quem mudou | Banco (migração) | Autor | 1 | Sprint 50 | Teste do índice único e da auditoria |
| S51-02 | US-50 | Engenharia | `GET/PUT/DELETE /api/v1/gabaritos/{p}/{q}/{tipo}` (chefia e desenvolvedor); ao salvar, o analisador roda o gabarito com o ruleset do período e as regras da questão, e a resposta traz as violações (regra, linha); o código do gabarito nunca vai a um monitor (a resposta dele traz só a existência e a data) | API, analisador | Autor | 2 | S51-01 | Matriz cargo × ação por chamada direta; a resposta de um monitor não tem o código; o canário do gabarito não aparece em log |
| S51-03 | US-51 | Engenharia | A comparação com o gabarito (ADR-11) e o alerta de possível vazamento usam os dois tipos: na verificação vale o mais parecido, e a resposta diz qual (`gabarito_kind`); no alerta, basta um; a API lê os gabaritos do banco, não mais do GitHub | API, analisador, página | Autor | 2 | S51-02 | Testes com 1 e com 2 gabaritos; a página mostra "Gabarito IP CC" ou "Gabarito Notion" |
| S51-04 | US-50 | Engenharia | Spike: a conta IP CC UFPE envia as soluções no Dikastis? Se sim, a extensão traz a última submissão aceita dessa conta para o cartão "Gabarito IP CC", marcada "veio do Dikastis" e editável; se não, o cartão segue só pelo painel | Extensão, API | Autor | 2 | S51-02 | Spike documentado em `decisoes.md` (Q-40); com a conta confirmada, a L1-Q1 ganha o gabarito IP CC sem digitar |
| S51-05 | US-50 | Engenharia | Os 28 gabaritos de 2026.2 entram no banco como `notion` (comando `ipc-rules import-gabaritos-db`, rodado pelo autor com o clone local); `ipc-rules export-gabaritos` gera `<período>/lista-<n>/L<n>-Q<m>.py` a partir do banco para o harness da CI (S20, S31-11); o `ip-checker-gabaritos` ganha um README de arquivo somente leitura que aponta para o painel; `IPC_GABARITOS_TOKEN` sai do Render (runbook) | API, CLI, CI, repositório de gabaritos | Autor | 2 | S51-02 | 28 no banco; o job "Gabaritos" passa a partir do export; a variável removida com o passo no runbook |
| S51-06 | US-50 | Engenharia | Tela "Gabaritos" (chefia): período → lista → questão, dois cartões (Notion e IP CC) com colar ou arrastar `.py`, o estado (sem gabarito, válido, com violações) e as violações na hora, com a pergunta "o enunciado libera?" | Página | Autor | 2 | S51-02 | Vitest com cobertura; e2e com a chefia; o monitor não vê a tela nem a rota |
| S51-07 | US-20 | Documentação | ADR-17 aceita; revisões da ADR-10 (item 2) e da ADR-11 (item 2); guia ("Cadastrar um gabarito"); `rulesets/README.md` (a seção dos gabaritos aponta para o painel); FR-40; NFR-27 revisado (o gabarito fica no banco, cifrado nos backups, nunca no navegador do monitor) | docs | Autor | 1 | — | Revisão |

**ADRs:** ADR-17 (novo); ADR-10 e ADR-11 (revisões).

**Critérios de aceite:**
1. Dada a L2-Q4, colar o código no cartão "Gabarito Notion" e salvar mostra "sem violação" ou as regras e linhas acionadas, e o gabarito passa a valer na comparação.
2. Com os dois gabaritos, a verificação mostra a semelhança com o mais parecido e diz qual é.
3. Um monitor não vê a tela "Gabaritos", e a API não devolve o código de nenhum gabarito a ele.
4. O job "Gabaritos" da CI passa com o export do banco, sem o repositório de gabaritos.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Gabaritos | pytest e Vitest | PR | Validação ao salvar; monitor sem acesso ao código; os dois tipos na comparação e no alerta |
| Privacidade | pytest com canário | PR | O código do gabarito não aparece em log, telemetria nem na resposta ao monitor |
| Export para o harness | pytest (`official_answers`) | PR | A árvore exportada passa no harness como antes |
| Regressão | `scripts/ci-local.sh` | Todo PR | Verde; o resumo colado no PR |

**Deploy:** release `sprint-51`. Migração pelo autor; Render e Vercel com "faça o deploy"; depois, `IPC_GABARITOS_TOKEN` sai do Render (runbook) e o exercício de alerta e o sintético.

**Riscos:**
- A conta IP CC UFPE não envia soluções: o cartão IP CC continua só pelo painel.
- Um gabarito com violação cadastrado por engano: o painel mostra a violação antes de salvar, e a auditoria diz quem salvou.
- Gabaritos no banco entram nos backups: eles já são cifrados (age), e a retenção segue a dos períodos (6).
