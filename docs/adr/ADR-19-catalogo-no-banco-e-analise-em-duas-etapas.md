# ADR-19 — Catálogo no banco e análise em duas etapas

**Título:** Como as listas e as questões do Dikastis entram no IP-Checker, e por que a análise do código é uma etapa separada da análise da questão.

**Status:** Aceito em 16/10/2026 (Sprint 50, a etapa 1), depois de proposto no mesmo dia ([`plano-dikastis.md`](../plano-dikastis.md)) e aprovado pelo autor; Sprints 50 e 52. **Na implementação (Sprint 50):** as tabelas são `app.catalog_period`, `catalog_class`, `catalog_list` (com `catalog_list_task`, a mesma lista em várias turmas), `catalog_question` e `catalog_question_version`, mais `app.import_run` e `app.import_token` (migração `0008`, só acréscimos); a API só acrescenta e reescreve (não apaga questões, listas nem rodadas), e tokens e rodadas somem com a conta; o hash do enunciado tem a mesma regra na API e na extensão, conferida pelos mesmos vetores (`extensao/test/vetores-hash.json`), e a API recalcula e recusa o que não confere; a tela "Listas do período" mostra, por questão, o enunciado, as regras e o gabarito; o estado das **referências de IA** entra na Sprint 42.1, porque o manifesto do analisador ainda não diz quais questões têm referências. Complementa a ADR-12 (a janela de períodos) e a ADR-10 (as regras das questões continuam em `rulesets/`).

**Contexto:** As listas aparecem no Dikastis ao longo do período: na primeira semana há a lista de treino e, no máximo, a Lista 1; as outras entram depois, e uma questão pode ser corrigida depois de publicada. Os alunos resolvem aos poucos, e nem todos resolvem tudo. O IP-Checker hoje só conhece as regras (`rulesets/`) e não sabe quais questões existem no Dikastis nem o que o enunciado diz. O autor pediu que o enunciado, a descrição da entrada e da saída e os casos de teste sejam analisados separadamente dos códigos dos alunos.

**Decisão:**
1. **O catálogo fica no banco** (`periods`, `classes`, `task_lists`, `questions`, `question_versions`): o que existe no Dikastis para cada período, com o enunciado normalizado (título, descrição, entrada, saída e só os casos de exemplo), o hash do conteúdo, o estado e a data em que sumiu, se sumiu. As regras das questões continuam em `rulesets/<período>/questions/` (ADR-10): o catálogo diz o que existe; o ruleset diz o que a questão permite.
2. **Etapa 1, da lista e da questão:** entra quando a questão aparece no Dikastis. A questão fica "pronta para a etapa 2" com o enunciado e as regras da lista; regras próprias, gabaritos (ADR-17) e referências de IA enriquecem a análise, mas não a bloqueiam. A tela "Listas do período" mostra o que falta em cada questão.
3. **Etapa 2, dos códigos:** entra quando os alunos enviam (ADR-16). Cada código novo passa pelo verificador, pelos indícios (para quem vê) e pelo plágio incremental (ADR-18), numa fila com estados próprios e retomada. Um código que chega antes da sua questão fica "aguardando a questão".
4. **Novo, mudou, igual:** a sincronização só acrescenta o novo e reescreve o que mudou (guardando até 5 versões anteriores do enunciado); nunca apaga o que sumiu do Dikastis, só marca.
5. **Separação de dado:** o enunciado não é dado pessoal e pode ir às IAs gratuitas, só com os casos de exemplo (Q-41); o código é dado pessoal, cifrado, e nunca sai para uma IA. Tabelas, permissões e telas separadas.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Só as regras, sem catálogo (situação atual) | Nada muda | O IP-Checker não sabe o que existe; os enunciados são copiados à mão |
| B. Catálogo nos arquivos de `rulesets/`, por PR | Tudo no Git | Um PR por questão nova, várias vezes por semana; enunciados no repositório principal |
| C. Escolhida: catálogo no banco, duas etapas | Acompanha o período; separa o que é dado pessoal do que não é | Mais tabelas; a tela precisa mostrar o estado de cada questão |
| D. Uma etapa só (código e questão juntos) | Mais simples | Um código sem questão não teria onde esperar; a análise ficaria presa à publicação completa da lista |

**Consequências positivas:** o IP-Checker acompanha o período como ele acontece; os enunciados alimentam o gerador de referências sem cópia manual; a equipe vê o que falta em cada questão.

**Consequências negativas:** duas fontes para a mesma questão (catálogo no banco e regras no ruleset), ligadas pelo `question_id`; a tela precisa deixar claro quando uma questão existe no Dikastis mas ainda não tem regras cadastradas.
