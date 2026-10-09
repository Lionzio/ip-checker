# Uso local e no servidor do CIn (compose, Fases 0 e 2)

Separado do `deploy/README.md` na S28-03. As seções sobre e-mail, feedback por IA, limpeza
diária e telemetria valem também para o piloto, com as variáveis no Render.


Todos os comandos rodam na raiz do repositório.

Antes da primeira subida, crie o `deploy/.env` (fora do Git) a partir do modelo e troque as três
senhas: a do administrador do banco, a do usuário da API e a senha inicial da conta do
desenvolvedor (P-14), que precisa de 9 caracteres, 1 maiúscula e 1 caractere especial:

```bash
cp deploy/.env.example deploy/.env
```

Subir tudo e esperar os healthchecks (cada serviço só sobe depois que o anterior está saudável; o
`migrate` aplica as migrações e sai):

```bash
docker compose -f deploy/compose.yaml up --build -d --wait
```

A página fica em http://127.0.0.1:8180, e a API, na mesma origem. Sem login, a página só mostra
Registrar e Entrar, e as rotas da equipe respondem 401:

```bash
curl -s http://127.0.0.1:8180/ready
```

Entrar pela página com `vlacg@cin.ufpe.br` (ou `vinicius.leoncio@ufpe.br`, ou o nome) e a senha do
`IPC_DEV_INITIAL_PASSWORD`. Ela só vale na criação da conta: trocar o `deploy/.env` depois não muda a
senha de uma conta que já existe. Para trocá-la, use **Perfil > Alterar a senha**; a troca encerra
as outras sessões da conta e mantém a atual.

## Registro e e-mails (S14)

Quem é da equipe se registra em **Registrar** com o e-mail `@cin.ufpe.br` ou `@ufpe.br`. No
compose, o e-mail de verificação não sai da máquina: o Mailpit o captura e mostra em
<http://127.0.0.1:8125>. O link abre a página **Confirmar o e-mail**, e só o botão dela gasta o
token (um antivírus que abre o link não confirma nada). Depois, o cadastro aguarda a aprovação
em **Gerenciar** (S15), que aparece para o desenvolvedor, os professores e os monitores-chefe: lá
ficam a fila de pedidos (aprovar com um cargo ou recusar), os membros ativos (alterar o cargo ou
remover) e as contas removidas (reativar). Cada linha só mostra o que o cargo de quem está logado
permite (FR-27), e a API confere de novo a cada ação.

Para enviar e-mails de verdade (Fase 2 ou piloto), configure um dos transportes na `api`:

| Variável | Uso |
|---|---|
| `IPC_EMAIL_TRANSPORT` | `smtp` (padrão) ou `brevo` (API HTTPS do Brevo) |
| `IPC_SMTP_HOST`, `IPC_SMTP_PORT`, `IPC_SMTP_SECURITY` (`starttls`, `ssl` ou `none`), `IPC_SMTP_USERNAME`, `IPC_SMTP_PASSWORD` | Transporte `smtp`. Sem `IPC_SMTP_HOST`, o envio fica desligado e o registro responde 503 `EMAIL_UNAVAILABLE` |
| `IPC_EMAIL_API_KEY` | Transporte `brevo`; obrigatória com ele (sem ela, a API não sobe) |
| `IPC_EMAIL_FROM` | Remetente, por exemplo `IP-Checker <endereco@cin.ufpe.br>` |
| `IPC_PUBLIC_BASE_URL` | Endereço público da página. O link é montado só a partir dele, nunca do `Host` da requisição |

O plano gratuito do Render bloqueia as portas SMTP de saída (25, 465 e 587) desde 09/2025; no
piloto, use o transporte `brevo` ou outro serviço por HTTPS. O provedor e o remetente ainda são
a questão Q-17 do blueprint: com um remetente `@cin.ufpe.br` enviado por terceiros, confira com o
NTI se a política de e-mail do CIn (SPF, DKIM e DMARC) aceita o envio, para os e-mails não caírem
no spam.

### Enviar de verdade a partir do compose (Gmail, Outlook e outros)

Por padrão, o compose entrega tudo ao Mailpit, e ninguém além de quem está na máquina vê o
e-mail. Para que o e-mail chegue à caixa de entrada (Gmail, Outlook, o webmail da UFPE...), ponha
um dos blocos abaixo no `deploy/.env` (modelo em `deploy/.env.example`) e suba de novo com
`docker compose -f deploy/compose.yaml up -d`. Sem essas linhas, volta o Mailpit.

**Opção A, uma conta Gmail (bom para testar da sua máquina):**

1. Na conta Google que vai enviar, ligue a **Verificação em duas etapas** (Conta Google >
   Segurança).
2. Em **Conta Google > Segurança > Senhas de app**, crie uma senha de app chamada "IP-Checker" e
   copie os 16 caracteres, sem espaços. Ela só serve para enviar e pode ser revogada ali.
3. No `deploy/.env`:

   ```
   IPC_SMTP_HOST=smtp.gmail.com
   IPC_SMTP_PORT=587
   IPC_SMTP_SECURITY=starttls
   IPC_SMTP_USERNAME=sua.conta@gmail.com
   IPC_SMTP_PASSWORD=a-senha-de-app
   IPC_EMAIL_FROM=IP-Checker <sua.conta@gmail.com>
   ```

O remetente precisa ser a própria conta (ou um alias dela); senão o Gmail o troca. O limite do
Gmail é de cerca de 500 e-mails por dia, de sobra para a equipe. Uma conta `@cin.ufpe.br` ou
`@ufpe.br` hospedada no Google funciona do mesmo jeito se a instituição permitir senhas de app
[PREMISSA: confirmar com o NTI].

**Opção B, Brevo (o mesmo transporte do piloto, porque o Render gratuito bloqueia SMTP):**

1. Crie uma conta gratuita em <https://www.brevo.com> (300 e-mails por dia).
2. Em **Senders, Domains & Dedicated IPs > Senders**, cadastre e confirme o remetente (por
   exemplo o Gmail do projeto).
3. Em **SMTP & API > API Keys**, gere uma chave.
4. No `deploy/.env`:

   ```
   IPC_EMAIL_TRANSPORT=brevo
   IPC_EMAIL_API_KEY=a-chave-do-brevo
   IPC_EMAIL_FROM=IP-Checker <remetente.confirmado@gmail.com>
   ```

**O link do e-mail precisa abrir onde a pessoa está.** No compose, o link é
`http://127.0.0.1:8180/verificar...`, que só abre na sua própria máquina: um monitor que recebe o
e-mail no celular ou no computador dele não chega a ela. Com o e-mail real configurado, o compose
serve para você testar a entrega e o clique; para a equipe se registrar, o IP-Checker precisa
estar no ar no piloto ([`piloto.md`](piloto.md)), com `IPC_PUBLIC_BASE_URL` apontando para o endereço público
da página (por exemplo `https://ip-checker.vercel.app`), que o `render.yaml` já recebe.

## Gabaritos no ambiente local (Sprint 32)

A comparação com o gabarito (ADR-11) lê, no compose, uma pasta montada só para leitura na API
(`IPC_GABARITOS_DIR=/gabaritos`). O padrão são os gabaritos **sintéticos** do e2e
(`frontend/e2e/gabaritos-sinteticos`, só a L1-Q1 de 2026.2). Para testar com os gabaritos oficiais
na sua máquina, aponte para o clone do repositório privado no `deploy/.env`, com o caminho a partir
de `deploy/`:

```text
IPC_GABARITOS_HOST_DIR=../../ip-checker-gabaritos
```

e recrie a API: `docker compose -f deploy/compose.yaml up -d api`. Os gabaritos ficam só na sua
máquina e na memória do contêiner; nada vai para a imagem. No piloto, a API os baixa do GitHub com a
credencial do runbook ("Credencial dos gabaritos").

## Feedback por IA (S18): onde ficam as chaves

O botão **Gerar feedback** funciona sempre. A ordem é: a **IA principal**; se ela falhar, demorar
ou responder algo que não passa na validação, a **IA de reserva**; se nenhuma responder a tempo
(prazo total de 28 s), ou se nenhuma estiver configurada, o texto é **montado por modelos**, sem
IA e sem enviar nada para fora. A abertura e a frase obrigatória são as mesmas nos três casos.

As chaves ficam só em variáveis de ambiente da `api`, nunca no Git nem na página:

- **No compose (local ou Fase 2):** no `deploy/.env`, que o Git ignora. O `deploy/.env.example`
  traz o bloco pronto; depois de preencher, suba de novo com
  `docker compose -f deploy/compose.yaml up -d api`.
- **No piloto (Render):** no serviço `ip-checker-api`, em **Environment**, as mesmas variáveis
  (o `render.yaml` já as declara, vazias).

| Variável | IA principal | IA de reserva |
|---|---|---|
| Provedor: `openai_compat` (OpenAI, Groq, DeepSeek e outros compatíveis) ou `gemini` | `IPC_LLM_PROVIDER` | `IPC_LLM_FALLBACK_PROVIDER` |
| URL da API, só no `openai_compat` fora da OpenAI (Groq: `https://api.groq.com/openai/v1`; DeepSeek: `https://api.deepseek.com`) | `IPC_LLM_BASE_URL` | `IPC_LLM_FALLBACK_BASE_URL` |
| Modelo disponível na sua conta do provedor | `IPC_LLM_MODEL` | `IPC_LLM_FALLBACK_MODEL` |
| Chave da API | `IPC_LLM_API_KEY` | `IPC_LLM_FALLBACK_API_KEY` |
| Tempo de cada tentativa (padrão: 12 s) | `IPC_LLM_TIMEOUT_S` | `IPC_LLM_FALLBACK_TIMEOUT_S` |

Use provedores diferentes na principal e na reserva, para as duas não caírem juntas. Uma
configuração incompleta (provedor sem modelo ou sem chave, URL sem HTTPS, reserva sem principal)
impede a API de subir, com a mensagem dizendo o que falta. `GET /api/v1/auth/options` diz à página
se há IA (`feedback_ai`). Cada conta tem até 60 feedbacks por dia e o servidor até 1.000
(`IPC_FEEDBACK_PER_ACCOUNT_DAY` e `IPC_FEEDBACK_DAILY_CAP`), para limitar o custo. Desde a
Sprint 25 a cota fica no banco (não zera num deploy) e só é cobrada depois da análise.

O que vai ao provedor: só o código sem comentários nem docstrings, a anotação e o resultado do
motor, com o nome do aluno trocado por `[ALUNO]` e e-mails, CPFs e números com 8 ou mais dígitos
trocados por `[EMAIL]`, `[CPF]` e `[MATRICULA]`; o nome e o cargo de quem avalia não vão. Antes de usar dados reais
de alunos, confira os termos do plano (retenção e uso dos dados para treinar modelos) e a
política da UFPE (Q-16).

## Limpeza diária e robustez (S25)

Nada a configurar: os padrões abaixo valem no piloto e no compose. As variáveis só existem para
um ajuste pontual.

| O quê | Padrão | Variável |
|---|---|---|
| Limpeza diária do banco (sessões e links vencidos, cadastros não confirmados em 48 h, contas fora do status ativo com 365 dias sem atividade, registro com mais de 12 meses, cota de feedbacks antiga) | ligada, ao subir e a cada 24 h | `IPC_HOUSEKEEPING=0` desliga; `IPC_HOUSEKEEPING_INTERVAL_S` |
| Limite geral por IP em todo `/api/*`, antes da sessão | 600 por minuto; 6.000 nas faixas do campus | `IPC_RATE_LIMIT_API_IP_PER_MIN`, `IPC_RATE_LIMIT_API_CAMPUS_PER_MIN` |
| Prazo de uma análise no worker | 2 s | `IPC_TIMEOUT_S` (no analisador) |
| Prazo da API para o analisador | o da análise + 1 s | `IPC_ANALYZER_TIMEOUT_S` |
| Workers do analisador e análises simultâneas | 2 e 4 no compose; 1 e 1 no Render | `IPC_WORKERS` (no analisador) e `IPC_ADMISSION_CAPACITY` (na API) |

As contagens da limpeza desde a subida aparecem em `/health/slo` (`housekeeping`). Uma falha da
limpeza (banco fora do ar) não derruba a API: ela fica no log e em `failures`, e a próxima rodada
tenta de novo. A API não sobe com `IPC_PUBLIC_BASE_URL` em `http://` fora do `localhost` enquanto
o cookie for seguro (`IPC_SESSION_COOKIE_SECURE=1`, o padrão).

## Telemetria e alertas (S21)

**Telemetria.** Cada verificação vira um evento anônimo no esquema `telemetry` do mesmo banco:
período, lista, questão, versão do ruleset, resultado, regras violadas e tempo de análise. Nada de
código, conta, nome ou IP (FR-16). A API grava em lote, fora do caminho da resposta, com o usuário
dela (membro de `ipc_writer`, que só insere); se o banco cair, os eventos são descartados e a
verificação segue normal. A migração `0002` cria o esquema; no piloto, o pipeline a aplica sozinho.
A própria API apaga o que passa de 12 meses ao subir e uma vez por dia (P-06), sem `pg_cron`.

**Consultas para os professores (FR-17 e relatório de eficácia, [`docs/eficacia.md`](../docs/eficacia.md)).** Só por views, com o papel `ipc_reader`, que não lê as
tabelas nem as contas:

| View | O que mostra |
|---|---|
| `telemetry.v_top_rules_by_list` | Regras mais violadas por período, lista e questão (eventos e ocorrências) |
| `telemetry.v_syntax_error_rate` | Taxa de erro de sintaxe por período, lista e questão |
| `telemetry.v_weekly_volume` | Verificações por semana e lista, com o resultado |
| `telemetry.v_team_adoption_by_list` | Porcentagem dos membros ativos da equipe que já verificaram algum código em cada lista do período (critério 2 da P-09; S28-02). Só a porcentagem, nunca quem |

Para dar acesso a alguém da coordenação, rode no banco, com o administrador (no Supabase, em **SQL
Editor**), escolhendo você a senha:

```sql
CREATE ROLE coordenacao LOGIN PASSWORD 'escolha-uma-senha' IN ROLE ipc_reader;
```

Exemplo de consulta:

```sql
SELECT rule_id, events, occurrences FROM telemetry.v_top_rules_by_list
WHERE semester = '2026.2' AND list_number = 2 ORDER BY occurrences DESC;
```

`GET /health/slo` mostra também quantos eventos foram gravados, descartados e estão na fila desde
que a API subiu.

**Alertas (US-19, NFR-15).** `GET /health/slo` responde 503 quando, nos últimos 5 minutos, o P95
de `POST /api/v1/validate` passa de 200 ms ou mais de 1% das respostas são 5xx. Com menos de 20
requisições na janela, ele nunca alerta, para um caso isolado não virar e-mail. O monitor do
UptimeRobot nessa rota (passo 9) manda o e-mail; o do `/ready` cobre a indisponibilidade. Os
limites mudam por `IPC_SLO_P95_MS`, `IPC_SLO_ERROR_RATE_PCT`, `IPC_SLO_MIN_REQUESTS` e
`IPC_SLO_WINDOW_S`.

**Exercício de falha (a cada release, NFR-15).** Confira que os dois e-mails chegam:

1. **Latência:** no Render, em **Environment**, defina `IPC_SLO_P95_MS=1` e
   `IPC_SLO_MIN_REQUESTS=1` e salve (o serviço reinicia). Faça uma verificação pela página. Em até
   10 minutos, o UptimeRobot avisa que `/health/slo` caiu. Apague as duas variáveis e salve de novo;
   o aviso de volta chega no próximo ciclo. No compose, o mesmo vale com
   `IPC_SLO_P95_MS=1 IPC_SLO_MIN_REQUESTS=1 docker compose -f deploy/compose.yaml up -d api`.
2. **Indisponibilidade:** no UptimeRobot, edite o monitor do `/ready` para `/ready-exercicio` (que
   responde 404). Em até 10 minutos chega o alerta; volte o endereço para `/ready`.

Anote a data e o resultado do exercício na descrição da release.

O banco não publica porta na máquina, então não disputa a 5432 nem a 6432 de outros projetos. Para
consultá-lo, entre no contêiner:

```bash
docker compose -f deploy/compose.yaml exec db psql -U postgres -d ipchecker
```

O analyzer não publica porta na máquina. Para falar direto com ele, entre na rede dele:

```bash
docker compose -f deploy/compose.yaml exec analyzer python -c "import json, urllib.request; r = urllib.request.Request('http://127.0.0.1:8001/internal/analyze', data=json.dumps({'code': 'for i in range(3):\n    print(i)\n', 'list_number': 1}).encode(), headers={'Content-Type': 'application/json'}); print(urllib.request.urlopen(r).read().decode())"
```

Rodar a suíte de segurança (isolamento, submissões maliciosas e API pública). Ela sobe o compose
inteiro num projeto próprio (`ipc-security-test`, com a borda na porta 18180, então convive com o
compose acima), cria dois contêineres clientes, um na rede interna e outro na da borda, ataca e
derruba tudo no final:

```bash
cd backend && IPC_SECURITY_TESTS=1 uv run pytest tests/security --no-cov -v
```

Derrubar tudo:

```bash
docker compose -f deploy/compose.yaml down
```
