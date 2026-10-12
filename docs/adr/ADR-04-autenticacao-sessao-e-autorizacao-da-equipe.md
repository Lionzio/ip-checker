# ADR-04 — Autenticação, sessão e autorização da equipe

**Título:** Contas próprias no PostgreSQL, com sessão no servidor, login por senha (Argon2id) ou pelo Google (OIDC), aprovação manual e uma única política de cargos no backend; página e API na mesma origem.

**Status:** Proposto em 02/10/2026 (P-13 e P-14) e implementado nas Sprints 13 a 16. **Confirmado no piloto (08/10/2026, S30-02 e S30-03; P-15):** o login pela página cria o cookie `__Host-ipc_session`, e o feedback pela página responde em até 30 s (P-15 a); o IP do cliente não é o penúltimo do `X-Forwarded-For`, e passou a vir do `Forwarded` ou da 4ª entrada a partir do fim (P-15 b).

**Contexto:** A P-13 restringe tudo à equipe. Alunos também têm e-mail institucional, então o domínio não basta e a aprovação é manual. A checagem precisa estar no backend. No piloto, a página está na Vercel e a API no Render, que são sites diferentes (`vercel.app` e `onrender.com` estão na Public Suffix List), e navegadores como o Safari bloqueiam cookies de terceiros. O projeto já prevê um PostgreSQL gerenciado (P-03).

**Decisão:**
1. Contas, e-mails, sessões e tokens ficam no esquema `app` do PostgreSQL (5.2.5), acessado pelo papel `ipc_app`; remover uma conta muda o status e nunca apaga o registro.
2. A sessão fica no servidor: identificador aleatório de 256 bits num cookie `__Host-` `HttpOnly`, `Secure` e `SameSite=Lax`, guardado no banco só como hash, com expiração por inatividade e absoluta, rotação no login e revogação na troca de senha, na mudança de cargo e na remoção (NFR-22).
3. Senhas em Argon2id. Google com Authlib (`state`, `nonce`, PKCE e ID token validado); o backend decide pelo `email` e pelo `email_verified` do token, nunca pelo `hd`.
4. Uma função pura, `can(ator, ação, alvo, cargo_novo)`, implementa o FR-27 e é a única fonte das permissões: as rotas a chamam, e a interface recebe dela as ações permitidas em cada linha.
5. Mesma origem no piloto: a Vercel repassa `/api/*` ao Render por *rewrite*. O CORS deixa de ser necessário, e o cookie e o retorno do Google ficam na origem da página. Toda rota que muda estado confere o `Origin`.
6. O link de verificação abre uma página da SPA, que confirma por `POST`; assim, o antivírus do e-mail não gasta o token ao abrir o link.
7. A conta do desenvolvedor é criada por um *seed* idempotente na subida da API, com a senha de `IPC_DEV_INITIAL_PASSWORD` usada só na criação.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida: contas próprias, sessão no servidor e mesma origem | Revogação imediata, regras de cargo sob controle do projeto, cookie primário e sem CORS | Mais código, e um acesso ao banco em cada requisição (alguns ms) |
| B. Supabase Auth ou outro provedor de identidade | Registro, verificação e Google prontos | Aprovação manual, cargos e status histórico continuam com o projeto; o token fica acessível ao JavaScript, e cada requisição passa a depender de um terceiro |
| C. JWT sem estado no cabeçalho `Authorization` | Nenhuma tabela de sessão | Não revoga na hora uma conta removida; o token fica exposto a XSS |
| D. Página e API em sites diferentes, com cookie `SameSite=None` | Nenhum *rewrite* | Bloqueado por navegadores que barram cookies de terceiros; exige CORS com credenciais |

**Consequências positivas:** nenhum dado sai sem conta ativa; remover alguém tem efeito imediato; as permissões são testáveis como tabela.

**Consequências negativas:** a `api` passa a guardar mais segredos (ameaça 12) e a depender do banco para atender, então o `/ready` também confere o banco; o *rewrite* acrescenta um salto e muda o IP que a API enxerga (P-15).
