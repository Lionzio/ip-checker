# Sprint 50 — Catálogo das listas pela extensão do Dikastis (parte 1)

Do plano de 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md)); o plano comum está no [README](README.md). Primeira sprint da integração com o Dikastis; destrava a parte 2 da Sprint 42 (os enunciados passam a vir do catálogo).

**Objetivo:** o catálogo das listas e questões de 2026.2 no banco, sincronizado pela extensão nos modos manual e semi-automático, só com o que é novo ou mudou, e os enunciados prontos para o gerador de referências.

**Missão:** que nenhum monitor copie um enunciado à mão de novo, e que o IP-Checker saiba, a cada semana do período, quais listas e questões já existem no Dikastis.

**Personas:** o monitor-mantenedor que sincroniza (US-48 e US-49) e o monitor-chefe que acompanha o catálogo e precisa dos enunciados para as referências de IA (US-34).

**Execução:**
1. O esqueleto da extensão e o adaptador do Dikastis (S50-01 e S50-02).
2. A descoberta e a normalização do catálogo (S50-03).
3. O token de importação e as rotas de manifesto e gravação, com a migração `0008` (S50-04 e S50-05).
4. A tela "Listas do período" e o `.zip` dos enunciados (S50-06), o modo semi-automático (S50-07) e os documentos (S50-08).

**Histórias:** US-48, US-49 e US-34.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S50-01 | US-48 | Engenharia | Esqueleto da extensão (Manifest V3; Vite com várias entradas: popup, script da página e service worker; TypeScript; Vitest; ESLint); ID fixado por `key` no manifesto; permissões só para `dikastis.com.br`, o domínio do IP-Checker, `storage`, `alarms` e `notifications`; lint, tipos e testes na CI local e no `ci.yml` | `extensao/`, `scripts/ci-local.sh`, `.github/workflows/ci.yml` | Autor | 2 | Sprint 49 | `npm run build` gera `extensao/dist`; carrega no Chrome e no Edge pelo modo de desenvolvedor; Vitest roda na CI |
| S50-02 | US-49 | Engenharia | Adaptador do Dikastis, o único módulo que conhece a API: lê o token da sessão guardado pelo próprio site, chama a API com ritmo de até 2 pedidos por segundo e repetição com espera, confere o formato de cada resposta e devolve tipos próprios (`Turma`, `Tarefa`, `Problema`, `Submissao`); formato diferente lança `FormatoDesconhecido` com o endereço e o campo | `extensao/src/dikastis/` | Autor | 3 | S50-01 | Testes com um Dikastis falso (respostas sintéticas, sem dados de aluno): formato mudado para com a mensagem certa e sem envio parcial; o ritmo é respeitado |
| S50-03 | US-48 | Engenharia | Descoberta e mapeamento: turmas do período pelo nome ("IP SI UFPE 2026.2"), tarefas (treino, lista, prova), `26.2L1Q1` → `L1-Q1`; normalização do enunciado (título, descrição, entrada, saída e só os casos de exemplo) num Markdown estável, de onde sai o hash | `extensao/src/catalogo/` | Autor | 2 | S50-02 | As 28 questões de 2026.2 mapeadas no teste; nenhum caso oculto no resultado; o mesmo problema dá o mesmo hash em duas leituras |
| S50-04 | US-48 | Engenharia | Token de importação: criar e revogar no Perfil (chefia e desenvolvedor), mostrado uma vez, guardado só como hash, 90 dias de validade, limite de taxa próprio; as rotas `/api/v1/import/*` aceitam a origem `chrome-extension://<id>` de `IPC_IMPORT_EXTENSION_IDS` e recusam qualquer outra | API (`auth/`, `routes/import.py`), Perfil | Autor | 2 | — | Testes de autorização: sem token, vencido, revogado, outra origem, cargo errado; o token aparece uma vez; nada dele no log |
| S50-05 | US-49 | Engenharia | Migração `0008` (`periods`, `classes`, `task_lists`, `questions`, `question_versions`, `import_runs`, `import_tokens`); `POST /import/catalog/manifest` devolve o que falta (novo, mudou, igual); `PUT /import/catalog/questions` grava, guarda a versão anterior (até 5) e marca `missing_since` no que sumiu; `import_runs` registra quem, quando, modo e contagens | API, banco | Autor | 3 | S50-04 | Testes com o banco: reenvio idêntico não muda nada; alteração reescreve e guarda a versão; o que sumiu fica marcado, nunca apagado; o histórico registra a rodada |
| S50-06 | US-34 | Engenharia | Tela "Listas do período": listas e questões com o estado da etapa 1 (enunciado, regras, gabaritos, referências); `GET /periods/{p}/catalog` e `GET /periods/{p}/catalog/statements.zip` (chefia) com os enunciados em `L1-Q1.md`, no formato do `--enunciados` do gerador da Sprint 42 | Página, API | Autor | 2 | S50-05 | Vitest com cobertura e e2e; o gerador roda com o `.zip` descompactado |
| S50-07 | US-49 | Engenharia | Modo semi-automático: ao abrir o Dikastis, a extensão verifica em segundo plano, no máximo a cada 30 minutos, e mostra um selo com o número de novidades; um clique envia | Extensão (service worker, popup) | Autor | 1 | S50-03, S50-05 | Teste do agendamento e do selo com o Dikastis falso |
| S50-08 | US-20 | Documentação | ADR-15 e ADR-19 aceitas; guia da equipe ("Instalar a extensão" e "O token de importação"); runbook ("A sincronização parou: o formato do Dikastis mudou" e "Revogar um token"); FR-38 e FR-39; `decisoes.md` | docs | Autor | 1 | — | Revisão |

**ADRs:** ADR-15 e ADR-19 (novos).

**Critérios de aceite:**
1. Dada a Lista 3 com 8 questões no Dikastis, "Verificar agora" e "Enviar" trazem as 8 ao catálogo, com título, entrada, saída e exemplos, e nenhum caso oculto.
2. Numa segunda sincronização, com a Lista 4 publicada e uma questão da Lista 3 corrigida, só a Lista 4 e essa questão são enviadas; a questão é reescrita com a versão anterior guardada; o resto fica igual.
3. O `.zip` dos enunciados alimenta o gerador da Sprint 42 sem edição manual.
4. Um token revogado ou de outra origem é recusado, e a extensão mostra o motivo.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Adaptador do Dikastis | Vitest com respostas sintéticas | PR | Formato conferido; mudança para limpa; ritmo de 2/s |
| Diferença do catálogo | pytest com o banco | PR | Igual não muda; mudou reescreve e guarda a versão; novo acrescenta; o que sumiu fica marcado |
| Token de importação | pytest | PR | Sem token, vencido, revogado, outra origem e cargo errado recusados |
| Tela e `.zip` | Vitest e e2e | PR | Estado da etapa 1 certo; o `.zip` tem um arquivo por questão |
| Regressão | `scripts/ci-local.sh` (incremental; `--completo` na ponta da `develop`) | Todo PR | Verde; o resumo colado no PR |

**Deploy:** release `sprint-50`. Migração `0008` pelo autor (como a `0007`), depois Render (Manual Deploy) e Vercel (Create Deployment), com "faça o deploy"; `IPC_IMPORT_EXTENSION_IDS` no `render.yaml`, sozinho no PR (P-18). Depois, o exercício de alerta e o sintético. A extensão é instalada pelo autor no próprio navegador, pelo passo a passo do guia.

**Riscos:**
- A API do Dikastis muda: o adaptador para com a mensagem certa, e a correção é uma versão nova da extensão.
- Duas pessoas sincronizando ao mesmo tempo: a diferença por hash torna o reenvio inofensivo.
- Enunciados com imagens ou fórmulas que o Markdown não carrega: o hash usa só o texto; a tela avisa quando um enunciado tem anexos que não vieram.

**Situação (16/10/2026):** concluída na release `sprint-50`, no mesmo dia do plano: PR A (#149;
S50-04 e S50-05), PR B (#150; S50-01, S50-02, S50-03 e S50-07) e PR C (#151; S50-06 e S50-08).
Decisões no `CHANGELOG.md`. O que mudou em relação ao plano: as tabelas se chamam `catalog_*`; o
ID da extensão fica no código, sem `IPC_IMPORT_EXTENSION_IDS` no `render.yaml`; o manifesto não
pede `alarms` nem `notifications` (Sprint 54); a NFR-33 foi revista (sem novidade, uma leitura por
questão, porque o Dikastis não diz quando um problema mudou); e o estado das referências de IA na
tela fica para a 42.1. Falta, com o autor: a migração `0008`, o deploy (Render e Vercel), a
instalação da extensão, o token e a primeira sincronização de verdade (critérios 1 e 2 de aceite),
o exercício de alerta e o sintético.
