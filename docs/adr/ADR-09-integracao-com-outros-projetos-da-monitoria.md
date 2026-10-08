# ADR-09 — Integração com outros projetos da monitoria

**Título:** Como o IP-Checker se integraria a outros 2 projetos mantidos por outros monitores, se a integração for confirmada.

**Status:** Proposto em 07/10/2026 (Q-23). A integração não está confirmada e os outros projetos não são conhecidos; nenhuma sprint a implementa.

**Contexto:** Há a possibilidade de o IP-Checker ser integrado a 2 projetos de outros monitores da disciplina. Hoje a API (seção 9.1 do blueprint) atende só a página do próprio IP-Checker: autenticação por cookie de sessão de uma conta aprovada da equipe (ADR-04), mesma origem no piloto (CORS desligado), `frame-ancestors 'none'`, limite de 30 análises por minuto por conta e nenhum dado de aluno guardado (NFR-11). Integrar sem decidir o modelo arriscaria abrir a API a chamadas sem conta, a dados de alunos fora do escopo da LGPD combinado com a coordenação ou a uma carga que o plano do Render não sustenta (ADR-03).

**Decisão (proposta, a confirmar depois das perguntas da seção 9.4):**
1. Integrar **pela API pública versionada** (`/api/v1`, contrato em `docs/openapi.json`), nunca pelo banco nem pela API interna do analisador (ADR-01).
2. Para chamadas de servidor a servidor, uma **conta de serviço por projeto**, aprovada pela equipe como as contas de pessoas, com credencial própria revogável, limite de taxa próprio e marca como a da conta de verificação (S28-02), para não contar na adoção nem na telemetria por pessoa.
3. Para chamadas do navegador de outro domínio, liberar a origem por configuração (`IPC_CORS_ORIGINS` e `IPC_ALLOWED_ORIGINS`), uma por projeto, e manter `SameSite=Lax` (o outro sistema usa a conta de serviço, não a sessão da pessoa).
4. Nenhum dado pessoal novo sem uma decisão registrada com a coordenação; o código do aluno continua sem ser guardado.
5. Mudanças de contrato seguem o versionamento (`/api/v2` para quebras), com o OpenAPI como fonte.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Proposta: API pública com conta de serviço por projeto | Reaproveita os limites, o isolamento e o contrato que já existem | Exige a autenticação de serviço, que não existe hoje |
| B. Acesso direto ao banco (papel de leitura) | Rápido para dados agregados | Acopla os esquemas; só serve à telemetria; nada de análise |
| C. Embutir a página em `iframe` | Sem mudança na API | Exige afrouxar a CSP (`frame-ancestors`); sessão em contexto de terceiros |
| D. Biblioteca do motor compartilhada (pacote `ipc_analyzer`) | Sem rede | O outro projeto passaria a analisar código do aluno sem o isolamento do ADR-01, e o ruleset ficaria duplicado |

**Consequências positivas:** a integração, se vier, parte de um contrato que já existe e é testado no CI.

**Consequências negativas:** a autenticação entre serviços, os limites por projeto e a eventual separação de dados por inquilino são trabalho novo, a estimar só depois das respostas da seção 9.4.
