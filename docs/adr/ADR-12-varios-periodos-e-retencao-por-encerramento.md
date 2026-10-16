# ADR-12 — Vários períodos carregados e retenção por encerramento

**Título:** Como a equipe escolhe o período na página e como os períodos antigos deixam de ser carregados.

**Status:** Aceito em 16/10/2026, na Sprint 43 (S43-01 a S43-05). Foi proposto em 12/10/2026 (revisão das seis frentes, [`revisao-seis-frentes.md`](../revisao-seis-frentes.md)) e revisa a decisão 3 da ADR-10.

**Contexto:** Até a Sprint 42, o analisador carregava um período só, o do arquivo `rulesets/ATIVO`, uma vez na subida. A API não devolvia o período em `/api/v1/lists` nem o aceitava em `/api/v1/validate`, e só aceitava questões do período ativo (P-07). A página não tinha seletor de período, embora o FR-32 e a US-37 o citassem. As listas são fixas (1 a 6); o que muda por período são os títulos, as regras e as questões. Os gabaritos já ficavam em memória indexados por período e questão (`gabaritos.py`). O autor quer um painel "Período" e que turmas com mais de 3 anos (6 períodos) deixem de ocupar memória.

**Decisão:**
1. **O período vem antes da lista** na página: Período (o ativo já escolhido, marcado "(ativo)") → Lista → Questão, no verificador, na Turma e no "Dois códigos" do plágio. Com um período só carregado, o seletor não aparece. Trocar de período limpa a lista e a questão, porque as listas habilitadas e as questões são por período; "Próximo aluno" mantém o período, e o rascunho da aba o guarda.
2. **O analisador carrega o ativo e os 5 anteriores** presentes em `rulesets/` (`load_rulesets` e `window_periods`, em `engine/ruleset/load.py`). A janela vai pelo nome, que ordena sozinho (`AAAA.S`); os posteriores ao ativo (em preparação) e `rulesets/encerrados/` ficam de fora. O ativo continua definido só pelo `ATIVO` (configuração, nunca a data), porque a data não sabe quando a UFPE abre o semestre (P-10). O manifesto interno lista os períodos carregados (`periods`), com a `ruleset_version`, o hash e as listas de cada um; um ruleset inválido em qualquer período da janela impede a subida, como antes.
3. **A API aceita `period` opcional** na verificação (também em lote), no feedback e no plágio entre dois códigos; sem ele, vale o ativo. `GET /api/v1/periods` lista a janela, e `GET /api/v1/lists?period=` as listas de um período. Fora da janela, a resposta é 422 `UNKNOWN_PERIOD`. No ativo, valem as listas de `IPC_ENABLED_LISTS`; num período anterior, todas as listas dele, porque a lista atrasada já foi publicada. O cache do feedback inclui o período.
4. **A telemetria não ganhou coluna nova:** cada análise já grava a `ruleset_version`, e o período vem dela (`semester_of`). A migração `0008` do plano não foi necessária, e os painéis por lista continuam lendo a versão; a versão corrente da telemetria (o semestre padrão do painel por lista e das recusas) só avança, para que uma lista atrasada não pareça uma volta de período.
5. **Encerrar, não apagar:** `ipc-rules retire-period <período> [--dry-run]` move a pasta para `rulesets/encerrados/`, que o carregador ignora. O comando recusa o ativo, os 5 anteriores, os posteriores ao ativo, um período que não existe e um já encerrado (nunca sobrescreve), e não faz commit: quem mantém o projeto o executa e abre o PR, revisado por professor ou monitor-chefe. O histórico do Git nunca é reescrito. No repositório dos gabaritos, a pasta do período pode ir para `encerrados/<período>/`: o índice da API só lê `<período>/lista-<n>/` e não a carrega, e a CI continua a conferir esses gabaritos com as regras do período, procuradas também em `rulesets/encerrados/`.
6. **A data só gera um aviso:** o `/health/slo` traz `warnings: ["ativo_defasado"]` quando o período ativo, pela versão corrente da telemetria, já devia ter acabado há mais de 60 dias (31/07 para `.1`, 31/12 para `.2`). O status continua 200, e o UptimeRobot não manda e-mail: trocar o período é decisão da coordenação (S31-09).

**Medida (S43-01, máquina do autor):** com 6 períodos completos, a subida de cada worker do analisador leva 1,44 s a mais e ocupa 0,9 MB a mais do que com um período (cerca de 150 KB por período, acima das "dezenas de KB" da proposta). O critério era até 2 s a mais. No piloto (0,1 CPU no plano gratuito), a subida é mais lenta na mesma proporção; até a troca do `ATIVO` para 2027.1, só um período fica na janela, e nada muda. Se a subida com 6 períodos atrapalhar o deploy, a alternativa é reduzir a janela para o ativo e 3 anteriores (`WINDOW`, uma constante), decisão do autor.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Só o período ativo, mostrado no cabeçalho | Nada muda no analisador | Não resolve a correção de uma lista atrasada |
| B. Escolhida: vários períodos carregados, com um ativo | Corrige listas atrasadas; os gabaritos já estão por período | A `ruleset_version` passa a depender do período escolhido |
| C. Um analisador por período | Isolamento total | Inviável no plano gratuito (0,1 CPU) |
| D. Períodos descobertos no repositório de gabaritos | "Cadastrado" passa a ser "tem gabarito" | Inverte a fonte da verdade das regras (`rulesets/`) |
| E. Apagar as pastas antigas | Pastas a menos | Não libera espaço (o Git guarda o histórico) nem memória relevante; perde o corpus de calibração |
| F. Coluna `period` na telemetria (migração `0008`) | O período explícito nas views | Duplica o que a `ruleset_version` já diz; mais uma migração no piloto |

**Consequências positivas:** uma lista de um período anterior é verificada com as regras certas; a página mostra só períodos recentes; gabaritos e referências encerrados continuam disponíveis para calibrar o plágio e os indícios.

**Consequências negativas:** cerca de 150 KB por período em cada worker do analisador e 1,44 s a mais na subida com a janela cheia; as views que agrupam por `ruleset_version` passam a mostrar versões de dois períodos na mesma semana quando há listas atrasadas; o aviso do `ATIVO` defasado usa a versão corrente da telemetria, que vem do manifesto na subida da API (com o banco ligado) ou, sem ele, da primeira verificação.
