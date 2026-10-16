# Sprint 48 — Entrada com o Google no piloto (no fim da fila, decisão de 12/10/2026)

Do blueprint até 15/10/2026, seção 7.16 (proposta de 12/10/2026); o plano comum está no [README](README.md).

**Objetivo:** que a equipe entre no piloto também com a conta Google da UFPE, além da senha.

**Missão:** ligar no piloto a entrada pelo Google que existe desde a Sprint 16, sem afrouxar as regras
de domínio e de aprovação.

**Personas:** o membro da equipe que prefere não guardar outra senha (US-25).

**Contexto:** o código, os testes e a recusa de domínios fora da UFPE e de e-mail não verificado
existem desde a Sprint 16 (US-25, `auth/google.py`). No piloto, o botão não aparece porque faltam o
cliente OAuth e as variáveis `IPC_GOOGLE_CLIENT_ID` e `IPC_GOOGLE_CLIENT_SECRET` (`deploy/piloto.md`,
passo 6). A antiga Sprint 48 (impressões digitais, ADR-14) saiu do plano com a Q-27; a integração
com outros projetos da monitoria (Q-23) fica para depois, sem sprint por enquanto.

**Execução:**
1. O autor cria o cliente OAuth e grava as variáveis no painel do Render (S48-01).
2. A verificação no piloto e o ensaio de entrada (S48-02).
3. Os documentos (S48-03).

**Histórias:** US-25.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S48-01 | US-25 | Externa | Criar no Google Cloud o cliente OAuth do tipo aplicativo da Web, com a URI de retorno `<endereço da Vercel>/api/v1/auth/google/callback`, só os escopos `openid`, `email` e `profile` e a tela de consentimento publicada; gravar `IPC_GOOGLE_CLIENT_ID` e `IPC_GOOGLE_CLIENT_SECRET` no painel do Render, nunca no repositório | Google Cloud, painel do Render | Autor | — | — | `/api/v1/auth/options` responde com o Google ligado no piloto |
| S48-02 | US-25 | Engenharia | O teste do piloto confere o Google ligado; ensaio com uma conta `@cin.ufpe.br` nova (entra na fila de aprovação), uma já existente (chega à mesma conta) e uma de outro domínio (recusada) | `backend/tests/pilot/`, `docs/runbook.md` | Autor | 1 | S48-01 | Os três casos registrados no runbook |
| S48-03 | US-25 | Documentação | Guia da equipe (entrar com o Google), aviso de privacidade (o Google como provedor de identidade), runbook (troca do segredo) e README | docs, `Privacy.tsx` | Autor | 0,5 | — | Revisão |

**ADRs:** nenhum novo; o ADR-04 já cobre a entrada pelo Google.

**Critérios de aceite:**
1. O botão de entrar com o Google aparece no piloto.
2. Uma conta Google fora de `cin.ufpe.br` e `ufpe.br` é recusada, mesmo com o parâmetro `hd` alterado (US-25).
3. Uma conta nova pelo Google só tem acesso depois da aprovação.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Domínio e aprovação | pytest (os testes da Sprint 16) | PR | Verdes |
| Google ligado no piloto | `tests/pilot` | Depois do deploy | O Google aparece ligado |
| Ensaio de entrada | Roteiro do runbook | Uma vez | Os três casos |

**Deploy:** release `sprint-48` (teste do piloto e documentos). As variáveis do Google valem no
Render depois de um Manual Deploy; a Vercel não muda. Depois, o sintético.

**Riscos:**
- Em modo de teste, a tela de consentimento só aceita os usuários listados; ela precisa estar
  publicada. Com só os escopos básicos, o Google não deve exigir a revisão do aplicativo
  [A CONFIRMAR no console].
- Um segredo a mais para trocar (runbook).
