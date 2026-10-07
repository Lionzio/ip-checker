# Segurança

O IP-Checker recebe código de alunos, guarda dados pessoais da equipe da disciplina (nome, e-mail,
curso, cargo e o resumo da senha) e roda num piloto público na internet, mesmo com o acesso restrito
à equipe. Este arquivo diz como relatar um problema e o que já está em vigor.

## Como relatar

Encontrou uma falha (um jeito de ver dados de outra conta, de executar código no servidor, de
contornar o login ou a aprovação, um segredo exposto)? **Não abra uma *issue* pública nem comente
num PR.** Escreva para o mantenedor:

- Vinícius Leôncio (Lionzio), desenvolvedor: `vlacg@cin.ufpe.br`.

Conte o que fez, o que esperava e o que aconteceu, com os passos para reproduzir. Não mande código
de aluno nem dados de outras pessoas; se precisar de um exemplo, use um código seu. A resposta vem
em até 5 dias úteis, com o que será feito. O tratamento segue a seção "Incidentes de segurança" do
[runbook](docs/runbook.md).

Testes de invasão contra o piloto (`ip-checker-red-phi.vercel.app` e o serviço no Render) só com
combinação prévia: o plano gratuito tem pouca CPU, e um teste de carga derruba a ferramenta da
equipe.

## O que está em vigor

| Controle | Onde | Testado por |
|---|---|---|
| O código do aluno nunca é executado: só a árvore sintática (AST) é lida, num analisador isolado | ADR-01; `backend/src/ipc_analyzer/` | Suíte de segurança (DoD, seção 8, itens 1 a 12), na CI |
| O analisador não tem rede, segredos nem escrita em disco; no piloto, UID próprio e seccomp | ADR-01 e ADR-03; `deploy/render/` | `backend/tests/security/test_pilot_isolation.py`, na CI |
| Acesso só para contas aprovadas da equipe, com e-mail `@cin.ufpe.br` ou `@ufpe.br` | ADR-04; P-13 | Itens 16 a 20 da seção 8, na CI |
| Senhas com Argon2id; sessão em cookie `__Host-`, `HttpOnly`, `Secure`, `SameSite=Lax` | ADR-04 | Itens 19 e 20 |
| O código do aluno não vai para logs, banco nem disco | NFR-11 | Teste canário, na CI |
| Limite de taxa por conta e por IP, admissão e prazos ponta a ponta | ADR-03; S10 e S25-04 | Testes da API e da borda |
| CSP, HSTS e `nosniff` na página; mesma origem para a API | NFR-10; S16-02 | Verificações do pipeline de deploy (`backend/tests/pilot/`) |
| Dependências travadas com hash e actions fixadas por SHA; Dependabot | S25-01 | CI |
| Varredura semanal de segredos (gitleaks) e de vulnerabilidades (pip-audit, npm audit e Trivy), ainda não bloqueante | `.github/workflows/audit.yml` | — |
| Backup semanal do banco, criptografado | `.github/workflows/backup.yml`; S28-03 | Ensaio de restauração no runbook |

O que ainda não existe está marcado como [PLANEJADO] no [blueprint](docs/blueprint.md) (seções 3.3,
5 e 8). O modelo de ameaças, com o risco que sobra em cada caso, está na seção 5.4 do blueprint.

## Segredos

Nenhum segredo entra no Git: o `deploy/.env` é ignorado, e os do piloto ficam no Render, na Vercel e
nos secrets do GitHub Actions. Quem troca cada um e como está no runbook ("Segredos"). Nunca cole
senhas, chaves, *connection strings* nem URLs de deploy hook em *issues*, PRs ou conversas.
