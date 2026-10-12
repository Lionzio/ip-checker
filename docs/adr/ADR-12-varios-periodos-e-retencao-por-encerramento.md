# ADR-12 — Vários períodos carregados e retenção por encerramento

**Título:** Como a equipe escolhe o período na página e como os períodos antigos deixam de ser carregados.

**Status:** Proposto em 12/10/2026 (revisão das seis frentes, [`revisao-seis-frentes.md`](../revisao-seis-frentes.md)); Sprint 43, que só começa com o comando do autor. Revisa a decisão 3 da ADR-10.

**Contexto:** O analisador carrega um período só, o do arquivo `rulesets/ATIVO` (`engine/ruleset.py`, `active_period` e `load_ruleset`), uma vez na subida. A API não devolve o período em `/api/v1/lists` nem o aceita em `/api/v1/validate`, e só aceita questões do período ativo (P-07). A página não tem seletor de período, embora o FR-32 e a US-37 o citem. As listas são fixas (1 a 6); o que muda por período são os títulos, as regras e as questões. Os gabaritos já ficam em memória indexados por período e questão (`gabaritos.py`). O autor quer um painel "Período" e que turmas com mais de 3 anos (6 períodos) deixem de ocupar memória.

**Decisão (proposta):**
1. **O período vem antes da lista** na página: Período (o ativo já escolhido) → Lista → Questão.
2. **O analisador carrega o ativo e os 5 anteriores** presentes em `rulesets/`. O ativo continua definido só pelo `ATIVO` (configuração, nunca a data), porque a data não sabe quando a UFPE abre o semestre (P-10). A data só gera um aviso em `/health/slo` quando o `ATIVO` parece defasado.
3. **A API aceita `period` opcional** na verificação, no plágio e no feedback; sem ele, vale o ativo. A telemetria e a adoção gravam o período da requisição.
4. **Encerrar, não apagar:** `ipc-rules retire-period <período> [--dry-run]` move a pasta para `rulesets/encerrados/`, que o carregador e o índice de gabaritos ignoram. O comando recusa o ativo e os períodos da janela. Quem mantém o projeto o executa, por PR revisado por professor ou monitor-chefe. O histórico do Git nunca é reescrito.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Só o período ativo, mostrado no cabeçalho | Nada muda no analisador | Não resolve a correção de uma lista atrasada |
| B. Escolhida: vários períodos carregados, com um ativo | Corrige listas atrasadas; os gabaritos já estão por período | A `ruleset_version` passa a depender do período escolhido |
| C. Um analisador por período | Isolamento total | Inviável no plano gratuito (0,1 CPU) |
| D. Períodos descobertos no repositório de gabaritos | "Cadastrado" passa a ser "tem gabarito" | Inverte a fonte da verdade das regras (`rulesets/`) |
| E. Apagar as pastas antigas | Pastas a menos | Não libera espaço (o Git guarda o histórico) nem memória relevante; perde o corpus de calibração |

**Consequências positivas:** uma lista de um período anterior é verificada com as regras certas; a página mostra só períodos recentes; gabaritos e referências encerrados continuam disponíveis para calibrar o plágio e os indícios.

**Consequências negativas:** um pouco mais de memória no analisador (dezenas de KB por período) e de tempo na subida; as views que agrupam por `ruleset_version` precisam ser conferidas.
