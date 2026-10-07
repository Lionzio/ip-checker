# ADR-06 — Feedback por LLM com moldura determinística

**Título:** O backend monta a apresentação, a abertura e a frase obrigatória; a LLM escreve só o trecho livre, que é validado antes de ser exibido.

**Status:** Proposto em 02/10/2026 e implementado na Sprint 18, com a IA de reserva e o modelo sem IA do item 6 (pedido do autor em 02/10/2026); o provedor depende da Q-16.

**Contexto:** O FR-30 exige que o texto nunca contradiga o motor, que a apresentação seja usada exatamente como foi montada e que as autorreferências concordem com o tratamento. Uma LLM não garante nada disso sozinha, e o código do aluno pode conter instruções dirigidas a ela.

**Decisão:**
1. Partes fixas, montadas pelo backend: apresentação (tabela do FR-30), abertura e frase obrigatória, com as proibições pelos nomes legíveis que o motor já usa (`engine/display.py`).
2. Parte livre, escrita pela LLM: de 1 a 3 frases que incorporam a anotação ou fazem uma sugestão curta, com instruções de gênero e de tom. Código, resultado e anotação vão em blocos delimitados e marcados como dados.
3. Antes do envio: o nome do aluno vira `[ALUNO]` no prompt inteiro, inclusive no código e na anotação, e os comentários do código são removidos pelo analisador (Q-16).
4. Depois da resposta: validação (nenhuma frase que negue ou invente violações; no tratamento neutro, nenhuma autorreferência com marcação de gênero, por lista de termos; tamanho máximo). Se falhar, há uma nova geração; se falhar de novo, o texto sai só com as partes fixas.
5. Adaptadores `openai_compat`, `gemini` e `fake` atrás de uma interface `generate(prompt) -> texto`. Provedor, modelo, URL e chave vêm de variáveis de ambiente e existem só na `api`.
6. Duas IAs e um modelo sem IA: a principal (`IPC_LLM_*`) e a de reserva (`IPC_LLM_FALLBACK_*`), cada uma com provedor, modelo e chave próprios, tentadas nessa ordem dentro de um prazo total de 28 s (12 s por tentativa; com uma IA só, ela tem uma nova tentativa). Se nenhuma devolve um texto válido, ou se nenhuma está configurada, o trecho livre sai de modelos de texto (a alternativa C), escolhidos de forma determinística: a anotação entra como foi escrita, uma dica coerente com o resultado do motor e um fechamento, sem marcação de gênero. Assim, o botão funciona mesmo sem IA, e nada sai do servidor nesse caso.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida: moldura determinística e trecho livre validado | Apresentação e frase obrigatória sempre exatas; o motor continua decidindo | A validação de gênero por lista de termos não pega tudo; a pessoa revisa antes de copiar |
| B. Texto inteiro escrito pela LLM | Mais natural | Pode omitir a frase obrigatória ou contradizer o motor |
| C. Só modelos de texto, sem LLM | Determinístico, grátis e sem envio a terceiros | Textos repetitivos; não incorpora a anotação com naturalidade. É a saída se a Q-16 vetar o envio |
| D. Modelo local | Nada sai do servidor | Não cabe no Render (512 MB e CPU fraca) nem no tempo de um desenvolvedor |

**Consequências positivas:** o feedback herda a precisão do motor, e trocar de provedor é só configuração.

**Consequências negativas:** custo e dependência de um terceiro; o código do aluno sai do servidor (ameaça 18); a qualidade da parte livre varia com o modelo.
