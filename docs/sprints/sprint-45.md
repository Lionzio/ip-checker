# Sprint 45 — Aprimorar com IA: validação rastreável e crítica

Do blueprint até 15/10/2026, seção 7.16 (proposta de 12/10/2026); o plano comum está no [README](README.md).

**Objetivo:** nenhum erro inventado pela IA chega ao aluno.

**Missão:** que o texto da IA só fale do que o verificador achou, não entregue a solução nem o
gabarito, e seja reescrito uma vez antes de cair no texto sem IA.

**Personas:** o membro da equipe que usa o "Aprimorar com IA" (US-43).

**Execução:**
1. Os validadores novos (S45-01).
2. Uma rodada de crítica e reescrita dentro do prazo atual de 28 s (S45-02).
3. A avaliação com a rubrica (S45-03).

**Histórias:** US-32 e US-43.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S45-01 | US-43 | Engenharia | Validação da saída além dos filtros atuais: (a) toda construção citada (vocabulário de `display.py`) está entre os itens do motor; (b) nenhum bloco com 3 ou mais linhas de código; (c) nenhum trecho com 6 ou mais tokens seguidos iguais ao gabarito, conferido na API, sem enviar o gabarito ao provedor; (d) ao menos uma frase de encorajamento do estilo; (e) até 6 frases e 900 caracteres | `feedback/compose.py`, `feedback/service.py` | Autor | 2 | S44-01, S44-02 | Casos T4 a T6 da revisão; 0 texto de gabarito nos logs (canário) |
| S45-02 | US-43 | Engenharia | Uma rodada de crítica: com a lista de problemas da validação, uma chamada de reescrita, só se sobrarem pelo menos 10 s; depois, o texto sem IA (`NO_ANSWER`) | `feedback/service.py` | Autor | 1 | S45-01 | Caso T8 (fallback em até 28 s); `test_service.py` |
| S45-03 | US-43 | Avaliação | 20 casos revisados pela equipe com a rubrica de 5 critérios (achado com linha; nada sem achado; caminho sem solução; tom; forma), de 0 a 2 cada; resultado em `docs/eficacia.md` | docs | Autor e equipe | 1 | S45-02 | Média de pelo menos 9 em 10 |

**ADRs:** ADR-06 (revisão: etapas de validação e crítica). O NFR-26 ganha "0 construções citadas
fora dos achados do motor e 0 trechos de 6 ou mais tokens iguais ao gabarito".

**Critérios de aceite:**
1. Um texto da IA que cita `while` num código sem `while` nunca é exibido.
2. Sem resposta válida em 28 s, aparece o texto sem IA, como hoje.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Validadores | pytest com o provedor falso | PR | Os casos adversariais novos são recusados |
| Crítica e prazo | pytest | PR | Uma rodada só; fallback no prazo |
| Gabarito fora dos logs | canário do NFR-11 e do NFR-27 | PR | 0 ocorrências |
| Rubrica | revisão humana | Uma vez | Média ≥ 9/10 |

**Deploy:** release `sprint-45`. Render.

**Riscos:** a crítica gasta uma chamada a mais da cota gratuita (60 por conta e 1.000 por dia); com a
cota no fim, a crítica é pulada.
