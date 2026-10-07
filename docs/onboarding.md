# Do zero ao compose verde

Para quem vai manter o IP-Checker: em cerca de 30 minutos, a máquina sai sem nada e chega ao
ambiente completo rodando (página, API, analisador isolado, banco e e-mail), com os testes passando.
Depois disto, leia o [`CONTRIBUTING.md`](../CONTRIBUTING.md) e o [mapa da documentação](README.md).

Os comandos são para o Git Bash (Windows), Linux ou macOS, na raiz do repositório, salvo quando
dizem outra pasta.

## 1. Ferramentas (10 min)

| Ferramenta | Versão | Para quê |
|---|---|---|
| Git | qualquer recente | o repositório |
| [uv](https://docs.astral.sh/uv/) | 0.12 ou mais nova | Python 3.13 e as dependências do backend (o uv instala o Python sozinho) |
| Node.js | 24 | a página (React + Vite) e os testes e2e |
| Docker Desktop (ou Docker Engine com o Compose) | recente | o ambiente completo e as suítes de segurança |
| GitHub CLI (`gh`) | recente | PRs, secrets e releases |

Confira:

```bash
git --version && uv --version && node --version && docker compose version && gh --version
```

## 2. O repositório (2 min)

```bash
gh repo clone Lionzio/ip-checker
cd ip-checker
git switch develop
```

## 3. Backend e página, sem Docker (8 min)

```bash
cd backend
uv sync
uv run pytest -q
cd ../frontend
npm ci
npm test
cd ..
```

Os testes do banco são pulados sem um PostgreSQL de teste. Para rodá-los também, suba um banco
descartável só em `127.0.0.1` (a porta 55432 não colide com outros projetos) e aponte o
`IPC_TEST_DATABASE_URL` para ele:

```bash
docker run -d --name ipc-test-db -e POSTGRES_PASSWORD=teste-local -e POSTGRES_DB=ipc_test -p 127.0.0.1:55432:5432 postgres:17-alpine
```

```bash
cd backend && IPC_TEST_DATABASE_URL=postgresql://postgres:teste-local@127.0.0.1:55432/ipc_test uv run pytest -q
```

## 4. O ambiente completo (5 min)

O compose sobe a borda (Caddy com a página), a API, o analisador endurecido, o banco e o Mailpit.
Ele lê as senhas do `deploy/.env`, que nunca entra no Git. Crie o arquivo com senhas sorteadas:

```bash
cp deploy/.env.example deploy/.env
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

Troque no `deploy/.env` as três senhas (`IPC_DB_ADMIN_PASSWORD`, `IPC_DB_API_PASSWORD` e
`IPC_DEV_INITIAL_PASSWORD`; esta última precisa de 9 caracteres, 1 maiúscula e 1 caractere
especial) e suba:

```bash
docker compose -f deploy/compose.yaml up --build -d --wait
```

Abra <http://127.0.0.1:8180> e entre com `vlacg@cin.ufpe.br` e o `IPC_DEV_INITIAL_PASSWORD`. Os
e-mails de verificação aparecem no Mailpit, em <http://127.0.0.1:8125>. Os detalhes do compose estão
em [`deploy/compose.md`](../deploy/compose.md).

## 5. O e2e verde (5 min)

```bash
cd frontend
npx playwright install chromium
npm run e2e
```

O Playwright lê a senha do desenvolvedor do `deploy/.env`. O projeto "contas" cria uma conta por
projeto que mexe na própria conta (senha, tratamento, limite por conta), pelo caminho de verdade:
registro, e-mail no Mailpit e aprovação (S28-04).

Se tudo ficou verde, o ambiente está pronto.

## Para desligar

```bash
docker compose -f deploy/compose.yaml down
```

`down -v` apaga também o banco local (contas e telemetria de teste).

## Próximos passos

- Como o projeto decide e registra as coisas: [`blueprint.md`](blueprint.md),
  [`decisoes.md`](decisoes.md) e os [ADRs](adr/).
- Como uma mudança chega ao piloto: [`CONTRIBUTING.md`](../CONTRIBUTING.md) e
  [`deploy/piloto.md`](../deploy/piloto.md).
- O que fazer quando algo dá errado no piloto: [`runbook.md`](runbook.md).
- As suítes de segurança, que sobem o compose num projeto próprio:
  [`deploy/seguranca.md`](../deploy/seguranca.md).
