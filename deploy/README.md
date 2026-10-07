# deploy

Configuração de implantação do IP-Checker. Nas Fases 0 (local) e 2 (servidor do CIn), o compose
sobe a borda `web` (Caddy com a SPA, S9-02), a `api` pública (S8-01), o `analyzer` endurecido
(S6-01), desde a Sprint 13, o banco de contas e sessões (`db`) com o serviço `migrate` e, desde a
Sprint 14, o `mailpit`, que captura os e-mails de verificação no desenvolvimento. No piloto
(Fase 1, 2027.1), a página vai para a Vercel e o backend para o Render, com o isolamento por
processo ([`piloto.md`](piloto.md)).

| Serviço | Redes | Porta na máquina | Endurecimento |
|---|---|---|---|
| `analyzer` | `analyzer_net` (interna, sem saída) | nenhuma | NFR-07 completo, testado ([`seguranca.md`](seguranca.md)) |
| `api` | `analyzer_net`, `edge_net` e `db_net` | nenhuma | UID 10001, só leitura, sem capabilities, `no-new-privileges`, 64 processos, 256 MB |
| `web` | `edge_net` | `127.0.0.1:8180` | UID 10001, só leitura, sem capabilities (nem a de portas baixas), `no-new-privileges`, 64 processos, 128 MB |
| `db` | `db_net` (interna, sem saída) | nenhuma | PostgreSQL 17 por digest, usuário `postgres` (70) sem passar pelo root, só leitura (dados num volume), sem capabilities, `no-new-privileges`, 100 processos, 256 MB |
| `migrate` | `db_net` | nenhuma | Roda uma vez a cada subida e sai; é o único com a senha de administrador do banco |
| `mailpit` | `edge_net` | `127.0.0.1:8125` (página de leitura) | Só no desenvolvimento; UID 10001, só leitura, mensagens só em memória, sem capabilities, `no-new-privileges`, 64 processos, 128 MB. Não envia nada para fora |

A `api` entra no banco com o usuário `ipc_api`, membro de `ipc_app`: lê e escreve contas e sessões,
mas não altera o esquema nem apaga contas (`backend/tests/test_migrations.py`).

## Onde está cada coisa

| Arquivo | Conteúdo |
|---|---|
| [`piloto.md`](piloto.md) | Piloto no Render e na Vercel: como o deploy acontece, o passo a passo das contas, a lista de conferência do primeiro deploy, o teste de carga e os riscos |
| [`compose.md`](compose.md) | Ambiente local e Fase 2: subir o compose, registro e e-mails, feedback por IA, limpeza diária, telemetria e alertas |
| [`seguranca.md`](seguranca.md) | Borda (Caddy), controles do NFR-07, submissões maliciosas, ataques à API pública e ao limite de taxa, imagem base |
| [`../docs/runbook.md`](../docs/runbook.md) | O que fazer quando algo dá errado no piloto: rollback, backup, banco, analisador e segredos |
| [`load/`](load/) | Teste de carga (k6): capacidade por plano do Render e a carga no piloto de verdade |
