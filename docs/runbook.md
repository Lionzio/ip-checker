# Runbook do piloto

O que fazer quando algo dá errado no piloto (Render, Vercel e Supabase; S25-02). Cada seção começa
pelo sintoma. A configuração das contas está em [`deploy/README.md`](../deploy/README.md), seção
"Piloto"; a passagem de bastão completa, com o ensaio cronometrado do rollback, vem na Sprint 28.

## Voltar para a versão anterior (rollback)

A meta da DoD é voltar em até 5 minutos. Os dois serviços guardam os deploys anteriores, então o
caminho mais rápido é pelos painéis; o Git vem depois, para a `main` não publicar o erro de novo.

1. **API (Render):** no serviço `ip-checker-api`, abra **Events**, escolha o último deploy que
   funcionava e clique em **Rollback**. O Render sobe a imagem anterior e só troca quando ela
   responde `/health/service`.
2. **Página (Vercel):** em **Deployments**, abra o deploy anterior de Production e use **Instant
   Rollback** (ou **Promote to Production**).
3. **Confira:** `curl -s <endereço do Render>/ready` e `<endereço da Vercel>/version.json` mostram o
   mesmo `release`, o do commit anterior.
4. **Git:** na `develop`, reverta o commit com problema por um PR (`git revert`), espere a CI verde e
   faça a release (fast-forward da `main`). O deploy seguinte publica a correção e alinha os painéis
   com a `main`.

**Migrações:** elas só acrescentam (tabelas, colunas, finalidades), então a versão anterior funciona
com o banco migrado e não precisa de `migrate down`. Só reverta uma migração se ela quebrou a
versão anterior:

```bash
cd backend
IPC_DATABASE_ADMIN_URL='<connection string do Supabase, usuário postgres>' \
uv run python -m ipc_api.db.migrate down --to <versão anterior, ex.: 0003>
```

## O deploy parou no meio

| Onde parou | O que significa | O que fazer |
|---|---|---|
| "Conferir que o commit ainda é a ponta da main" (aviso) | Outra release chegou à `main` durante o deploy | Nada: o deploy da release nova está na fila e publica a ponta |
| "Migrar o banco do piloto" | O Supabase recusou a conexão ou a migração falhou | Veja "Banco fora do ar"; a versão no ar não mudou |
| "Publicar a API no Render" | A API nova não respondeu `/ready` em 25 minutos | Veja o log do build no Render (**Events**); a página não foi publicada, e o Render manteve a versão anterior no ar |
| "Publicar a página na Vercel" | A página nova não publicou o `/version.json` em 10 minutos | Veja o build na Vercel; se a API nova já está no ar e é incompatível com a página antiga, faça o rollback da API |
| Verificações ou smoke e2e | O piloto está no ar, mas algo não funciona por fora | Leia o relatório do Playwright (artefato do workflow); se for grave, rollback |

Depois de corrigir a configuração, rode de novo em **Actions > Deploy do piloto > Run workflow**
(branch `main`).

## Banco fora do ar (DATABASE_UNAVAILABLE)

O `/ready` responde 503, a página não entra nem verifica, e o `/health/service` continua 200 (a
instância não reinicia por causa do banco).

1. No Supabase, veja se o projeto foi **pausado** (o plano gratuito pausa depois de 7 dias sem
   atividade). Se foi, clique em **Restore**; o monitor do `/ready` no UptimeRobot evita isso.
2. Veja **Database > Connection pooling**: a `IPC_DATABASE_URL` do Render usa o *Session pooler*,
   com o usuário `ipc_api`.
3. Se a senha do `ipc_api` mudou, atualize `IPC_DATABASE_URL` no Render e `PILOT_DB_API_PASSWORD` no
   GitHub.

## Analisador indisponível (ANALYZER_UNAVAILABLE)

O `/health/service` e o `/ready` respondem 503. No Render, o log mostra o motivo:

- **Filtro seccomp recusado** (`IPC_SANDBOX=required`, fail-closed): o Render não aceitou o filtro
  dos workers (P-12 b). A alternativa é `IPC_SANDBOX=optional`, com o risco das ameaças 2 e 6 em
  Médio (blueprint, 5.4); registre a decisão.
- **Ruleset inválido:** o analisador não sobe com um ruleset ou uma questão inválida (FR-15). Isso
  não deveria passar da CI (`ipc-rules validate`); faça o rollback e corrija por PR.

## Segredos

Trocar um segredo (vazou, ou alguém saiu da equipe técnica):

| Segredo | Onde trocar | Depois |
|---|---|---|
| Senha do `ipc_api` | Supabase (SQL: `ALTER ROLE ipc_api PASSWORD ...`, ou a migração com `--login-role`) | `IPC_DATABASE_URL` no Render e `PILOT_DB_API_PASSWORD` no GitHub |
| Senha do `postgres` | Supabase, **Project Settings > Database** | `PILOT_DATABASE_ADMIN_URL` no GitHub |
| Chave do Brevo | Brevo, **SMTP & API > API Keys** (crie a nova e apague a velha) | `IPC_EMAIL_API_KEY` no Render |
| Cliente OAuth do Google | Google Cloud, **Credentials** | `IPC_GOOGLE_CLIENT_SECRET` no Render |
| Chaves das IAs | Painel de cada provedor | `IPC_LLM_API_KEY` e `IPC_LLM_FALLBACK_API_KEY` no Render |
| Deploy hooks | Render (**Settings > Deploy Hook**, regenerar) e Vercel (apagar e criar) | `RENDER_DEPLOY_HOOK_URL` e `VERCEL_DEPLOY_HOOK_URL` no GitHub |

Trocar uma variável no Render reinicia o serviço; as sessões abertas continuam válidas, porque
ficam no banco.
