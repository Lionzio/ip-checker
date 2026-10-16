# Sprint 37 — Verificação mais clara

Do blueprint até 15/10/2026, seção 7.15 (plano de polimento de 11/10/2026); o plano comum está no [README](README.md).

**Objetivo:** tornar a tela de verificação mais rápida de ler e de usar, no computador e no celular, e
dar à ferramenta uma identidade visual simples.

**Missão:** que o monitor, corrigindo dezenas de soluções seguidas, entenda o resultado num olhar,
sem rolar a página e sem perder o código de vista.

**Personas:** o monitor em correção em lote (US-33), no computador e no celular (US-21).

**Execução:**
1. O resumo e os cartões (S37-01) e os componentes comuns (S37-03), que o resto usa.
2. O editor fixo e as abas do celular (S37-02).
3. A tela inicial e o cabeçalho (S37-04).
4. As preferências (S37-05).
5. As capturas de antes e depois vão no PR (o roteiro de capturas entra em `scripts/`).

**Histórias:** US-09, US-11, US-21 e US-33.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S37-01 | US-09 | Engenharia | Resumo do resultado por categoria, com contadores clicáveis que filtram os cartões. Cada regra num cartão que abre e fecha, aberto por padrão até 5 regras. O trecho de código com a linha destacada | `frontend/src/components/ResultPanel.tsx` | Autor | 1,5 | — | Sete violações cabem numa tela de 900 px com os cartões fechados; teste dos filtros |
| S37-02 | US-33, US-21 | Engenharia | No computador, o editor fica fixo na tela (`position: sticky`) enquanto o resultado rola, e clicar numa linha continua selecionando o trecho. No celular, abas "Resultado", "Indícios" e "Feedback" e um botão "Voltar ao código" | `frontend/src/pages/Checker.tsx` | Autor | 1,5 | S37-01 | No celular, o resultado das 7 violações cabe em até 2 telas; e2e de layout verde com o axe |
| S37-03 | US-21 | Engenharia | Componentes comuns (`Button`, `Card`, `LineChip`, `SyntaxErrorBox`) no lugar das cópias de `ResultPanel`, `Plagiarism`, `IndicatorsPanel` e `FeedbackPanel`. No Gerenciar, os botões com foco visível e alvo de 44 px, e as tabelas que rolam no celular | `frontend/src/components/`, `frontend/src/pages/Admin.tsx` | Autor | 1 | — | Nenhuma classe de botão repetida; axe sem violações no Gerenciar |
| S37-04 | US-11 | Engenharia | Identidade visual simples: um logotipo em SVG e a cor da marca. A tela inicial explica Verificar, Plágio e Feedback em três blocos. O cabeçalho mostra o primeiro nome, com um menu da conta (Perfil e Sair). A área "Soluções da turma" ganha numeração de linhas | `frontend/src/pages/Landing.tsx`, `frontend/src/components/AppHeader.tsx`, `frontend/public/` | Autor | 1 | — | Capturas aprovadas pelo autor; nada novo no JS inicial além do SVG |
| S37-05 | US-33 | Engenharia | Preferências e atalhos. Tema claro, escuro ou do sistema, salvo neste navegador. O rascunho do editor sobrevive ao F5 (`sessionStorage`; o Sair continua apagando). Alt+N para "Próximo aluno" e Ctrl+Shift+C para copiar o feedback, com uma ajuda dos atalhos | `frontend/src/`, `docs/guia-da-equipe.md` | Autor | 1 | — | Testes do tema, do rascunho e dos atalhos; o guia atualizado |

**ADRs:** nenhum.

**Critérios de aceite:**
1. O resultado de 7 violações cabe numa tela no computador e em 2 no celular.
2. O código fica à vista enquanto o resultado rola.
3. Nenhuma violação do axe.
4. Lighthouse dentro da meta (FCP ≤ 1,65 s; Q-25), e o JS inicial ≤ 350 KB com gzip.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Resumo, filtros e cartões | Vitest | PR | Contadores e filtros corretos |
| Layout no celular e no computador | Playwright `layout.spec.ts` com o axe | PR | Sem rolagem lateral e sem violação |
| Tema, rascunho e atalhos | Vitest | PR | Preferência salva; rascunho volta depois do F5 e some no Sair |
| Desempenho da página | Lighthouse e `js-budget.mjs` | PR | FCP ≤ 1,65 s; JS ≤ 350 KB |
| Capturas de antes e depois | Roteiro de capturas | PR | Anexadas ao PR |

**Deploy:** release `sprint-37`.
- **Vercel:** sim, só a página muda.
- **Render:** não precisa.
- **Depois:** sintético e exercício de alerta.

**Riscos:** mudança visual grande; mitigada pelas capturas de antes e depois e pela aprovação do autor.

**Situação (14/10/2026):** engenharia concluída na release `sprint-37` (#106, #109 a #111): S37-01 a S37-05. Decisões tomadas na sprint (detalhes no `CHANGELOG.md`): o tema vale pelo `data-theme` do `<html>`, aplicado por `public/theme.js` (a CSP não aceita script inline); o rascunho fica no `sessionStorage` da aba e some no Sair (aviso de privacidade atualizado); acima de 5 regras os cartões nascem fechados; Perfil e Sair foram para o menu da conta; "Soluções da turma" virou um `CodeEditor`; Ctrl+Shift+C foi mantido (a página o intercepta no Chrome e no Edge). Aguardando: a aprovação das capturas pelo autor (`prints-sprint-37/`) e o deploy na Vercel.
