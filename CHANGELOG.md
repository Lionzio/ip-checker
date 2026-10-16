# Changelog

O que cada sprint entregou e as decisões de implementação tomadas nela. Até a Sprint 27, este
texto ficava nos parágrafos "Situação" do blueprint (seção 7); desde a S28-04, fica aqui. O que
estava planejado para cada sprint continua nas tabelas de tasks do [blueprint](docs/blueprint.md).

Cada release na `main` ganha a tag `sprint-NN` e um GitHub Release com a seção da sprint
(`scripts/release.sh`). O ruleset tem versão própria (`ruleset_version`), citada nas sprints que o
mudaram.

## Sprint 39 — Qualidade interna, operação e documentação

A Sprint 39 (S39-01 a S39-06; US-14, US-15, US-20 e US-35) começou em 16/10/2026, depois da 40. A
missão é que o próximo monitor-mantenedor assuma o projeto sem depender do autor. As personas são o
monitor-mantenedor, o monitor logado num pico do banco e o desenvolvedor que revisa. A S39-06 veio
primeiro: era a última falha intermitente da CI local. Sem a cota do Actions (P-19), a evidência de
cada PR é o `scripts/ci-local.sh --e2e`.

- **16/10/2026, S39-06 (#131):** com o banco lento, a sessão não resolvia (`StoreBusy`), a
  requisição ficava sem conta e o limitador a contava como anônima pelo IP: o monitor logado recebia
  429 "Você fez muitas requisições" no lugar do 503 `OVERLOADED`, e todos atrás do mesmo IP dividiam
  30 por minuto até a janela esvaziar. Agora essa requisição conta só no limite do IP, e a rota
  responde 503 com `Retry-After`; o teto do IP continua (teste novo). Os testes de borda deixaram de
  depender da virada do minuto e do pool do banco. Ensaio: a etapa de segurança passou 3 vezes
  seguidas com 16 processos ocupando a máquina.
- **16/10/2026, S39-03 (#132):** a cobertura das páginas passou a ser cobrada por arquivo (80% das
  instruções, linhas e funções, 75% dos ramos) na etapa do Vitest. Login, Register, Verify, Landing,
  ForgotPassword e ResetPassword já estavam cobertos pelo `App.test.tsx`; os buracos eram a Turma
  (71%) e os erros do Perfil, que ganharam testes. Páginas: 93% das instruções e 86% dos ramos. No
  backend, o `pytest-xdist`: os testes sem banco e sem relógio rodam com 4 processos e os do
  PostgreSQL (marcador `db`) e os de tempo (marcador `timing`) em série, somando a cobertura. Na CI
  local, as duas etapas somam cerca de 90 s, contra 146 a 210 s antes (−40% ou mais). O teste do
  prazo do pool só passava com o worker deixado pronto pelo teste anterior, e foi corrigido.
- **16/10/2026, S39-01 (#133):** `Plagiarism.tsx` (527 → 101 linhas), `Admin.tsx` (421 → 201) e
  `Checker.tsx` (359 → 277) em arquivos menores, sem mudança de comportamento; nenhuma página passa
  de 300 linhas. A refatoração somou 0,3 KB ao JS inicial e o FCP do Lighthouse móvel pulou de 1.505
  para 1.656 ms, estável: medindo builds parciais, a causa era o tamanho total, no limite de uma
  janela do TCP da simulação de rede (cruzá-lo custa uma ida e volta, ~150 ms). O Plágio, o
  Gerenciar e o Perfil passaram a carregar sob demanda, como a Turma: o JS inicial caiu para 107,8
  KB e o FCP voltou a 1.506 ms.
- **16/10/2026, S39-02 (#134):** `engine/ruleset.py` (773) virou o pacote `engine/ruleset/`
  (`schema`, `compile` e `load`); `engine/indicators.py` (706 → 488), com as listas de palavras e as
  perguntas em módulos próprios; `service/app.py` (698 → 308), com os modelos em `service/schemas.py`;
  e `ipc_api/schemas.py` (873) virou o pacote `ipc_api/schemas/`. Os `__init__` reexportam tudo, e
  o `docs/openapi.json` gerado ficou idêntico. Ficam acima de 500 linhas: `accounts/postgres.py`,
  `engine/similarity_tree.py` e `accounts/store.py`.
- **16/10/2026, S39-04 (#135):** o backup agendado no Agendador de Tarefas do Windows (domingo ao
  meio-dia), com a connection string guardada pelo DPAPI do usuário, e o ensaio de restauração em
  script (`scripts/restaurar-ensaio.sh`). Ensaio de 16/10/2026 no backup de 11/10: linhas iguais nas
  9 tabelas, em 7 s. O teste com um segredo de mentira achou e corrigiu um defeito que impediria o
  backup agendado de abrir o segredo. Gravar o segredo e registrar a tarefa ficam com o autor.
- **16/10/2026, S39-05 (#136):** o blueprint caiu de 2.443 para 985 linhas: o detalhe de cada
  sprint foi para `docs/sprints/` (da 36 em diante) e `docs/historico/sprints-01-35.md`, e a seção
  7.2 nova mapeia as seções antigas. O `decisoes.md` ganhou uma tabela-resumo escrita à mão (71 IDs)
  e uma seção por ID. Novos: `glossario.md`, `estado.md`, `faq-mantenedor.md`, `rotinas.md` e
  `contas.md`. O índice de sintomas do runbook ganhou três sintomas, e um teste confere os links
  relativos de todos os `.md`.
- **Deploy (16/10/2026):** sem migração; Render por Manual Deploy (`/ready` em `c5cd0c1` às 09:23)
  e Vercel por Create Deployment (`/version.json` em `c5cd0c1` às 09:24; Plágio, Gerenciar, Perfil e
  Turma respondendo, com o JS inicial novo). Exercício de alerta (#137 e #138): 503 só por
  `latencia`, e-mail de queda às 09:37 e de volta às 09:52 (runbook). O autor guardou o segredo do
  backup agendado; falta registrar a tarefa. O sintético fica para o autor rodar.

## Sprint 40 — A correção da turma inteira

A Sprint 40 (S40-01 a S40-03; US-16, US-31 e US-33) começou em 15/10/2026, antes da 39, por pedido
do autor. A missão é que o monitor receba as soluções de uma lista (do Dikastis ou de uma pasta) e
veja, numa tabela, o status de cada aluno e os grupos de soluções parecidas. As personas são o
monitor em correção em lote e o professor que acompanha a lista. Sem a cota do Actions (P-19), a
evidência do PR é o `scripts/ci-local.sh --e2e`.

- **15/10/2026, S40-01 (Turma inteira):** a tela nova **Turma** (`/turma`) recebe vários `.py` ou um
  `.zip` (até 100 arquivos, 50 KB cada, 2 MB no total e 4 MB de `.zip`), escolhidos ou arrastados.
  O `.zip` é aberto no navegador, sem biblioteca nova: o diretório central é lido, pastas,
  `__MACOSX` e arquivos ocultos ficam de fora, e a descompressão (`DecompressionStream`) para assim
  que passa do tamanho declarado, o que barra a *zip bomb*. A barreira de 128 KiB por requisição
  (Caddy e API) **não mudou**: a página manda os arquivos em partes de até 20 e abaixo de 110 KB
  para a rota nova `POST /api/v1/validate/batch`. A lista e a questão são conferidas uma vez; cada
  arquivo passa pelos mesmos limites do `/validate` e pela admissão, e um arquivo recusado vira
  uma linha "Recusada", sem derrubar a parte. Se o serviço estiver sobrecarregado (429 ou 503 com
  `Retry-After`), a tela espera o tempo pedido e continua de onde parou, até 5 vezes por parte, e
  pode ser cancelada. A rota conta 1 no limite de 30 por minuto da conta, como o
  `/similarity/batch`; o que protege o servidor é a admissão por arquivo. O resultado tem uma
  linha por aluno (o nome do arquivo), com o status, as violações por categoria, as regras e a
  semelhança com o gabarito, e vira um CSV (`;`, com BOM, para o Excel) **sem o código**. Nada é
  guardado.
- **15/10/2026, S40-02 (Todos contra todos):** o Plágio ganhou o modo **Todos contra todos**: de 2 a
  60 soluções no formato do "Contra a turma" (`=== nome`), até 120 KB juntas. O motor
  (`compare_all`) usa o mesmo IDF da turma inteira e devolve os pares do mais parecido para o
  menos (a API manda os 200 primeiros) e os **grupos**: as soluções ligadas por pares a partir de
  "Requer atenção" (90%), de modo que A parecida com B e B com C ficam juntas. A tela mostra os
  grupos, os pares a partir de 80% (com "Mostrar todos os pares") e leva qualquer par ao "Dois
  códigos" para o lado a lado. Na turma sintética de 30 soluções (dois grupos de cópias
  disfarçadas e o resto independente), os dois grupos são achados e nada mais. Medido em
  15/10/2026 na máquina do autor: 30 soluções em 0,14 s e 60 soluções de 1,2 KB em 0,35 s; o
  analisador tem 10 s para a turma. O limite de 60 cabe com folga no piloto (0,1 CPU); as 100
  soluções do NFR-30 ficam para a S46-03.
- **15/10/2026, S40-03 (Painel por lista):** o Gerenciar ganhou o **Painel por lista**: para a lista
  escolhida, no período ativo, as 15 regras mais violadas (em quantas verificações e quantas
  ocorrências), quantas verificações houve, quantas com erro de sintaxe e quanto da equipe já usou
  a lista. Vem da rota nova `GET /api/v1/admin/list-panel` (só monitor-chefe, professor e
  desenvolvedor), que lê **só** as views anônimas da telemetria (`v_top_rules_by_list`,
  `v_syntax_error_rate` e `v_team_adoption_by_list`). Para isso, a migração `0007` dá ao usuário
  da API o papel `ipc_reader`, que só lê essas views; nenhuma tabela nova é exposta, e nenhum
  aluno, conta, código ou nome aparece no painel.
- **15/10/2026, S40-04 (Benchmark estável sob carga, incluída a pedido do autor):** a CI local da
  sprint reprovou em 4 rodadas seguidas, com o mesmo código, por três ruídos diferentes: o benchmark
  do motor (`plagio_50kb` com razão de 47 a 52, máximo 51, duas vezes), o teste do limite por IP
  (duas vezes) e os prazos do Vitest (uma vez). O motor não ficou mais lento: com a máquina ociosa,
  a razão fica em 40 a 42, abaixo da linha de base (42,5). A medida é que estava errada: a
  calibração (10 execuções de 10 ms) era feita toda antes da ação (10 execuções de 500 ms), e as
  duas pegavam momentos diferentes da carga do notebook (o processador híbrido do i7-13620H, com
  4 núcleos de eficiência 2 vezes mais lentos, e outros programas abertos). Agora a razão é
  **pareada**: cada amostra mede uma calibração, a ação e outra calibração, e divide a ação pela
  média das duas; a carga que muda no meio da rodada deixa de distorcer. E uma entrada acima da
  tolerância é **medida de novo** até 2 vezes, só contando como regressão se passar nas três (a
  carga só deixa o motor mais lento, nunca mais rápido). A tolerância de 20% e o piso de 0,5 ms
  (S36-10) não mudaram. A linha de base foi regravada na escala nova: `plagio_50kb` de 42,5 para
  43,0 e `grande_50kb` de 17,7 para 18,2; as entradas pequenas subiram mais (de 0,019 a 0,033 na
  `proibicoes_variadas`), porque as calibrações em volta esvaziam o cache de uma ação de 0,5 ms,
  mas continuam abaixo do piso. A etapa passou de 50 para 65 s. Ensaio de 15/10/2026 com o motor de verdade: com 16 processos ocupando todos os núcleos, 3 rodadas passaram com razão de 43,2 a 43,7 sem nenhuma nova medida (antes, a mesma carga dava de 47 a 52); presa aos núcleos de eficiência, 48,4 (passou); uma regressão de mentira de 30% no `compare_sources` reprovou nas três medidas, ociosa (54,7 / 54,2 / 57,2) e com carga (58,3 / 58,3 / 57,3).
  O Vitest ganhou 5 s de espera nos `findBy` (era 3 s), e o 429 enganoso do limite por IP, que
  aparece quando o banco demora a resolver a sessão, ficou registrado para a Sprint 39 (S39-06).
- **Deploy (15/10/2026):** a migração `0007` foi aplicada pelo autor pelo runbook "Sem GitHub
  Actions" (connection string de admin só no terminal); Render por Manual Deploy às 20:30 (`/ready`
  em `b10cb1d` às 20:31) e Vercel por Create Deployment (`/version.json` em `b10cb1d` às 20:33;
  `/turma` no ar). Exercício de alerta (#127 e #128): 503 só por `latencia`, e-mail de queda às
  20:44 e de volta às 21:00 (runbook).
- **16/10/2026, sintético da `sprint-40`:** rodado pelo autor por volta das 05:20; pelo
  `/health/slo`, uma verificação na janela, P95 de 28 ms no servidor (limite de 300 ms) e 0% de
  erros.

## Sprint 38.1 — Conexões com o analisador que ele mesmo fechou

- **15/10/2026:** depois do sintético da `sprint-38`, o `/health/slo` do piloto ficou em 503 por
  `erros` de 12:35:53 a cerca de 12:41, sem nenhuma verificação com falha: duas chamadas ao
  `/health/service` (12:35:00 e 12:35:55) receberam 503 `ANALYZER_UNAVAILABLE`, e a API registrou
  `RemoteProtocolError` e `ReadError` ao falar com o analisador. A causa: o cliente da API
  guardava a conexão parada por 5 s, o mesmo tempo depois do qual o `uvicorn` do analisador a
  fecha, e às vezes a reaproveitava no instante em que ela era fechada. Com pouco tráfego, dois
  erros desses passam de 1% e disparam o alerta; é a explicação mais provável para o 503 da
  madrugada de 15/10, que não teve deploy nem reinício. O cliente passa a descartar a conexão
  parada depois de 2 s e, se a conexão ainda assim falhar desse jeito (`RemoteProtocolError`,
  `ReadError` ou `WriteError`), tenta de novo uma vez, numa conexão nova e dentro do mesmo prazo.
  Repetir é seguro, porque nenhuma rota do analisador muda estado. Uma conexão recusada (o
  analisador fora do ar) continua dando 503 na hora, sem nova tentativa.
- **15/10/2026, depois do deploy da `sprint-38.1`** (Render às 13:04; a página não mudou): 10
  chamadas ao `/health/service` com pausas de 6 a 7 s, mais que o keep-alive do analisador, deram
  200. O exercício de alerta (#123 e #124) teve o primeiro 503 às 13:16:33, só por `latencia`,
  sem a fase de `erros` que aparecia depois da carga; o e-mail de queda chegou às 13:17 e o de
  volta às 13:28 (runbook).

## Sprint 38 — Explicar cada regra e exportar o resultado

A Sprint 38 (S38-01 a S38-05; US-02, US-08, US-10, US-12, US-22, US-32 e US-33) começou em
15/10/2026. A missão é que o monitor explique a violação ao aluno sem reler o documento de
permissões e que o feedback sem IA baste na maioria dos casos. As personas são o monitor que dá o
feedback e o professor que mantém as regras. Sem a cota do Actions (P-19), a evidência de cada PR
é o `scripts/ci-local.sh --e2e`.

- **15/10/2026, S38-01:** cada regra do ruleset ganhou `explicacao` (por que a construção é
  proibida ou ainda não vale) e `alternativa` (o que usar no lugar), obrigatórias no carregador e
  no esquema JSON, também nas seis exigências e na R-04; a R-01, que vem do enunciado, tem textos
  fixos no motor. Os 71 pares de textos saem do documento de permissões, sem criar regra: as
  proibições gerais citam a lista do documento, as regras de listas posteriores dizem em que lista
  entram e o que usar antes, e as que têm condição (zip(), enumerate(), items(), type()) explicam a
  condição. Rulesets `2026.2.7` e `2027.1.2`. A violação passou a levar `explanation` e
  `alternative` do analisador à página (contrato OpenAPI regenerado; vazios com um analisador
  anterior), e o cartão de cada regra mostra "Por quê" e "O que usar". **Revisão dos textos:**
  pela Q-31, um monitor-chefe, um professor ou o desenvolvedor; aguardando a do autor.
- **15/10/2026, S38-02:** o feedback sem IA usa a alternativa de cada construção ("Sobre for: Na
  Lista 1, resolva com…") e o que fazer quando falta o assunto da lista, sem repetir a mesma
  alternativa. O trecho continua nos limites do NFR-26 (4 frases e 600 caracteres): entram as
  alternativas que couberem, e o resto fica com a dica geral de antes. A abertura, a frase
  obrigatória e o `[ALUNO]` não mudaram. Um teste passa todas as alternativas reais pela validação
  nos três tratamentos.
- **15/10/2026, S38-03:** "Carregar .py", ao lado de Colar e Limpar, e arrastar o arquivo para o
  editor: só `.py` em UTF-8 de até 50 KB (o limite da API), com o BOM e as quebras de linha do
  Windows tratados; um arquivo grande, em outro encoding ou que não é texto é recusado com o
  motivo, sem mexer no editor. O resultado ganhou "Copiar o relatório" e "Baixar .txt"
  (`ip-checker-lista-1.txt` ou `ip-checker-L3-Q9.txt`), com a lista, a questão, a versão das
  regras e, por regra, a categoria, a mensagem, as linhas, o porquê e o que usar, sem o código.
  Tudo acontece no navegador: nada vai ao servidor nem é guardado. Nos testes da página, a espera
  dos `findBy` passou de 1 s para 3 s (`setup.ts`), a causa das falhas por tempo na CI local da
  Sprint 37.
- **15/10/2026, S38-04:** o feedback deixa de reanalisar o código a cada "Gerar". A API guarda
  em memória, por 10 minutos e até 512 resultados (o mais antigo sai primeiro), só o resultado da
  análise (o status e os itens com os nomes e as alternativas), pela chave do SHA-256 do código,
  da lista e da questão; o código, o nome do aluno, a anotação e o texto nunca entram. Gerar de
  novo com outro nome ou outra anotação não chama o analisador nem ocupa a admissão. O "Aprimorar
  com IA" continua analisando, porque precisa do código sem comentários, que só o analisador
  isolado prepara (decisão da sprint; o resultado guardado é renovado). O cache é de um processo e
  some num reinício ou num deploy.
- **15/10/2026, S38-05:** o `SourceMap.column` não decodifica mais a linha a cada fato: uma linha
  só ASCII usa o byte como coluna, e as outras ganham, uma vez, a tabela do byte para o caractere.
  Um teste confere, byte a byte, que as colunas são as mesmas de antes, com caracteres de 1 a 4
  bytes. Medida na entrada de 50 KB, intercalando a versão antiga e a nova: 4% mais rápida em
  código só ASCII (631 contra 658 ms) e igual com acentos. A conversão de colunas não era o
  gargalo da extração; a linha de base do benchmark não foi regravada, porque o ganho fica dentro
  do ruído da máquina. Onde está o custo de verdade fica para a Sprint 39 (qualidade interna).
- **15/10/2026, depois do deploy da `sprint-38`:** Render (Manual Deploy, `/ready` com `319ab17` e
  as regras `2026.2.7`) e Vercel (`/version.json` com `319ab17`) publicados a pedido do autor,
  antes da revisão dos textos pela Q-31, que segue pendente. O exercício de alerta (#118 e #120)
  teve o primeiro 503 às 12:14:11, o e-mail de queda às 12:15 (NFR-15: até 5 min) e o de volta
  às 12:30 (runbook).
- **15/10/2026, sintético da `sprint-38`:** rodado pelo autor; pelo `/health/slo`, a verificação
  levou 20 ms no servidor (limite de 300 ms).

## Sprint 37 — Verificação mais clara

A Sprint 37 (S37-01 a S37-05; US-09, US-11, US-21 e US-33) começou em 14/10/2026. A missão é que o
monitor, corrigindo dezenas de soluções seguidas, entenda o resultado num olhar, sem rolar a página
e sem perder o código de vista, no computador e no celular. As personas são o monitor em correção
em lote e o monitor no celular. Com a cota do Actions esgotada até 01/11/2026 (P-19), a evidência
de cada PR é o `scripts/ci-local.sh --e2e`. As capturas de antes e depois saem do roteiro
`frontend/scripts/capturas.mjs` e ficam fora do repositório (`prints-sprint-37/`).

- **14/10/2026, S37-03:** os componentes comuns de `frontend/src/components/ui.tsx` passam a ser
  os únicos botões da página: `Button` ganhou os tamanhos `md` e `sm` (o `sm` cabe numa linha de
  tabela) e a variante `link`; entraram `Card` (a moldura dos painéis e dos cartões de regra),
  `LineChip` (o botão "Linha 3, coluna 1" que seleciona no editor, também nos indícios, no gabarito
  e nos trechos do plágio) e `SyntaxErrorBox` (o erro de sintaxe, igual na verificação e nos dois
  modos do plágio). As dezessete cópias de classes de botão (resultado, feedback, indícios,
  gabarito, plágio, editor, gerenciamento, cabeçalho e as telas de conta) foram trocadas. No
  Gerenciar, os botões e os seletores de cargo têm 44 px nas telas de toque e o foco visível, e as
  tabelas ganharam largura mínima para rolar na horizontal no celular em vez de espremer as
  colunas. Um teste-guarda (`src/ui.guard.test.ts`) falha se algum `<button>` ou classe de botão
  aparecer fora de `ui.tsx`, como a guarda de código do backend.
- **14/10/2026, S37-01:** o resultado da verificação ganhou o resumo por categoria: um contador
  por categoria ("4 anulações imediatas"), na ordem de gravidade, que filtra os cartões ao clicar
  (o resumo em frase continua para o leitor de tela). Cada regra é um cartão que abre e fecha pelo
  cabeçalho, com a categoria, a regra, o número de linhas e a mensagem sempre à vista; até 5 regras
  os cartões nascem abertos, acima disso fechados, com "Abrir todos" e "Fechar todos". A exigência
  da lista ("Solução inteira") não tem o que abrir. O trecho de cada regra passou a mostrar uma
  linha de contexto antes e outra depois, sem o recuo comum, com a linha da violação em destaque.
  O filtro e os cartões recomeçam a cada verificação (a chave é o `request_id`). Os componentes
  `Chip` e `Disclosure` entraram em `ui.tsx`.
- **14/10/2026, S37-02:** no computador, a coluna do editor fica fixa (`position: sticky`)
  enquanto o resultado rola, com a altura limitada à janela e rolagem própria se a janela for
  baixa; clicar numa linha do relatório continua selecionando o trecho, que já está à vista. No
  celular (abaixo de `lg`, 64rem), o lado do resultado vira abas, "Resultado" (com a comparação com
  o gabarito), "Indícios" (só quando a resposta os traz) e "Feedback", com `role="tablist"`, setas,
  Home e End no teclado, e um "Voltar ao código" fixo no rodapé da coluna que devolve o foco ao
  editor. O Verificar escolhe a aba Resultado antes de enviar, para que o foco vá ao título do
  resultado como antes. A largura vem de um `useMediaQuery` (`hooks/useMediaQuery.ts`); sem
  `matchMedia`, a página se comporta como no computador. `TabList` entrou em `ui.tsx`. O e2e
  `checker-layout.spec.ts` (projeto "feedback") confere, com sete violações, a primeira tela de
  1280×900 com os cartões fechados, o editor fixo, as duas telas de 375×812, as abas, o "Voltar ao
  código" e o axe nos dois temas.
- **14/10/2026, S37-04:** a identidade visual: um logotipo em SVG inline (`components/Logo.tsx`,
  um quadrado na cor da marca com duas linhas de código e a marca de verificação; o mesmo desenho
  em `public/favicon.svg`) e a cor da marca com nome (`--color-brand`, o azul que a página sempre
  usou, no `@theme` do Tailwind), usada no logotipo e nos botões principais. A tela inicial explica
  Verificar, Plágio e Feedback em três blocos, com Entrar e Registrar como botões (`ButtonLink`).
  O cabeçalho mostra o logotipo, a navegação (Verificar, Plágio, Gerenciar) e o **primeiro nome**
  num botão que abre o menu da conta, com o nome completo, o cargo, Perfil e Sair (`role="menu"`,
  setas, Esc devolve o foco, clique fora fecha); Perfil e Sair saíram da navegação. A área
  "Soluções da turma" do plágio virou um `CodeEditor`, com numeração de linhas, Tab e Colar, e a
  dica do formato continua como descrição (`describedBy`). Os e2e que clicavam em Sair ou Perfil
  passam a abrir o menu antes.
- **14/10/2026, S37-05:** preferências e atalhos. O **tema** passa a ser claro, escuro ou do
  sistema, escolhido no Perfil ("Aparência") ou no menu da conta e guardado neste navegador
  (`localStorage`, `ipc:tema`); a variante `dark` do Tailwind deixa de ser o `prefers-color-scheme`
  e passa a ser o `data-theme="dark"` do `<html>`, que o `public/theme.js` (um arquivo de cerca de
  500 bytes, carregado antes do módulo da página, porque a CSP só aceita scripts da própria origem)
  aplica antes da primeira pintura, sem piscar, e que o `useTheme` mantém em dia, acompanhando o
  sistema operacional na opção "Do sistema". O **rascunho** (código, questão, nome do aluno e
  anotação) passa a sobreviver a um F5: fica no `sessionStorage` desta aba (`ipc:rascunho`), morre
  com ela e some no Sair; a lista continua no `localStorage`; o aviso de privacidade diz isso. Os
  **atalhos** Alt+N ("Próximo aluno") e Ctrl+Shift+C (copia o feedback gerado; dentro de um campo
  de texto, o atalho fica com o campo) entram na tela de verificação, com uma ajuda "Atalhos do
  teclado" abaixo dos botões que lista também Ctrl+Enter, Tab, Shift+Tab e Esc. O guia da equipe
  ganhou o menu da conta, o tema, o rascunho e os atalhos.
- **14/10/2026, depois do deploy da `sprint-37`:** a página foi publicada na Vercel às 15:28 (`/version.json` com `0ce3d71`); o Render não mudou. O exercício de alerta (#113 e #114) teve o primeiro 503 às 15:37:54, o e-mail de queda às 15:41 (cerca de 3 min; NFR-15: até 5 min) e o de volta às 15:56 (horário de Brasília; runbook). Depois da carga, o motivo do 503 passou de `latencia` a `erros` por alguns minutos: respostas 5xx da carga ficaram na janela de 5 min e, com o tráfego caindo, passaram de 1%.
- **15/10/2026, sintético da `sprint-37`:** `scripts/sintetico-local.sh`, rodado pelo autor, entrou
  pela página e verificou em 42,1 ms no servidor (limite de 300 ms).

## Sprint 36.1 — Prazo da análise no piloto com a medição depois do deploy

- **12/10/2026, S36-06:** depois do deploy da `sprint-36`, a medição no piloto (prazo de 7 s) não
  teve nenhuma recusa nas 20 verificações de 10 a 50 KB, mas a entrada de 50 KB levou de 3,3 a 3,8 s:
  a extrapolação de 3,1 s ficou curta, e 7 s não dava o dobro da maior entrada. O analisador do
  piloto passa a ter 8 s e a API espera 9 s; a página continua com 10 s. O teste dos prazos usa a
  maior entrada medida, e o teste do piloto confere a mediana da maior entrada (ADR-03).
- **12/10/2026, depois do deploy da `sprint-36.1`:** a medição no piloto passou (nenhuma recusa;
  50 KB com mediana de 3,8 s), o sintético ficou em 18 ms no servidor, e o exercício de alerta
  (#103 e #104) teve o e-mail de queda às 16:16 e o de volta às 16:26, cerca de 4 min e meio depois
  do primeiro 503 (NFR-15: até 5 min; runbook).

## Sprint 36 — Defeitos e documentos certos para a campanha de testes

A Sprint 36 (S36-01 a S36-10; US-06, US-08, US-11, US-20, US-22, US-31, US-33 e US-37) fechou a
engenharia em 12/10/2026. A missão é que a equipe faça a campanha de testes manuais sem defeito
conhecido e com um guia que diz o mesmo que o motor. As personas são o monitor que corrige e
compara soluções e o monitor-mantenedor que cuida da documentação. Com a cota do Actions esgotada
até 01/11/2026 (P-19), a evidência de cada PR é o `scripts/ci-local.sh --e2e` (27 etapas). As
medições no piloto saíram de um ajudante no terminal: o autor digitou a senha da conta de
verificação uma vez, e as ações (sintético, medição e carga) rodaram a pedido, sem a senha sair
daquele terminal.

Aguardando:

| Task | Entrada pendente |
|---|---|
| S36-08 | A campanha de testes manuais da equipe com o `docs/testes-manuais.md` (em andamento) |
| Exercício de alerta | Os horários dos e-mails do UptimeRobot, registrados no runbook depois do deploy |

- **12/10/2026, S36-01 e S36-02 (#95):** no "Contra a turma", cada solução ganha um rótulo
  único: com duas "Ana", a segunda vira "Ana (2)", com um aviso, e o "Comparar lado a lado" abre o
  código certo (antes, a segunda apagava a primeira). O separador passa a ser `=== nome`, que não é
  Python e nunca aparece num código; um comentário `### ...` dentro da solução não a parte mais. O
  formato antigo `### nome` continua aceito numa turma sem nenhum `===`, com um aviso.
- **12/10/2026, S36-03 (#98):** no editor, Tab com várias linhas selecionadas indenta
  todas, e Shift+Tab desindenta a linha ou a seleção (até 4 espaços ou um tab), mantendo o Ctrl+Z.
  O teste novo do componente achou um defeito: apertar só Shift desfazia o Esc, e Esc e depois
  Shift+Tab não saía do editor. Corrigido.
- **12/10/2026, S36-04 e S36-05 (#97):** todo nó que o motor pode emitir tem nome em
  português ("atribuição", "comparação", "conta aritmética"...), com um teste que percorre o `ast`
  do Python 3.13; na comparação com o gabarito, o termo técnico fica na dica. O Verificar mostra
  "Verificando…" e um Cancelar. As opções do seletor de Questão ficam curtas ("L4-Q4 · gabarito"),
  e o título e o que vale vão para a frase abaixo dos seletores.
- **12/10/2026, S36-06 (#100):** medido no piloto (0,1 CPU) pela página, com o
  `Server-Timing`: a análise leva cerca de 60 ms por KB, e entradas legítimas de 40 e 50 KB
  recebiam 422 `ANALYSIS_LIMIT` no prazo de 2 s. No piloto, o analisador passa a ter 7 s e a API
  espera 8 s (ADR-03); o compose e a CI continuam com 2 s. A medição é repetida depois do deploy e registrada no ADR-03.
- **12/10/2026, S36-10 (#101):** o benchmark do motor só aponta regressão quando a
  diferença também passa de 0,5 ms: nas entradas pequenas, o ruído da máquina carregada passava
  dos 20% de tolerância sem nenhuma mudança no motor.
- **12/10/2026, S36-07 (#96 e #100):** o guia da equipe (a lista do `split()` na Lista 3, os casos do Marco 2, a condição do `zip()` nas Listas 2 a 4, os indícios e o feedback sem IA como padrão), o `deploy/piloto.md` (a ordem real do IP do cliente, as variáveis novas e o backup diário), o `RULES.md` (Q-22 decidida), o blueprint (o status dos ADRs, os restos da Q-25, as listas habilitadas, caminhos e marcadores resolvidos), o ADR-04, o ADR-03 (1 worker), o `edge.py` (mesma origem desde a Sprint 16) e o comentário dos indícios no `render.yaml`.
- **12/10/2026, S36-09 (#99), com o de acordo do professor:** a recursão (uma função que chama a
  si mesma, direta ou mutuamente) só é permitida a partir da Lista 6 (Q-33): nas Listas 1 a 5, ela
  aparece como "Fora da lista" no `def`, pela R-68, que no catálogo já é "permitida e obrigatória na
  Lista 6". Uma função que só chama outras continua permitida desde a Lista 4 (R-59). O carregador
  aceita o mesmo id numa regra e numa exigência só quando a regra começa na lista da exigência.
  Rulesets `2026.2.6` e `2027.1.1`; nenhum dos 40 gabaritos mudou de resultado.

## Depois da Sprint 35

- **12/10/2026, token dos gabaritos sem vencimento (P-23):** o autor criou o `IPC_GABARITOS_TOKEN` sem data de vencimento. O runbook e a S39-04 passam a tratar a troca por evento (suspeita de vazamento, mudança de quem administra a conta ou 401 nos logs), e não por data.
- **12/10/2026, Q-33, Q-35 e Q-36 decididas:** a recursão só é permitida a partir da Lista 6 (nova task S36-09, porque hoje o catálogo a aceita desde a Lista 4); o `None` e o `in`, o `pop()` e o `copy()` em tuplas e dicionários já seguem a decisão. Os critérios dos indícios de IA foram aprovados (repetição no máximo média, dois marcadores novos e a calibração pelos gabaritos e por soluções novas geradas por IA). A satisfação será medida pelo autor com os feedbacks da equipe coletados manualmente.
- **12/10/2026, decisões do autor sobre a revisão:** Q-26, Q-28 a Q-32 e Q-34 decididas. Dos alunos, guarda-se só o nome (e, opcionalmente, o login do Dikastis) e o resultado resumido de cada verificação, sem código nem feedback (Q-27): a ADR-14 foi rejeitada e a Sprint 48 passou a ser a entrada com o Google no piloto. As soluções anteriores a 2023 e o formulário da pesquisa com a planilha do critério 3 foram descartados (Q-36 aberta para o critério de satisfação); o gerador de referências por IA foi aprovado; a integração com outros projetos fica para depois. As marcas desatualizadas do blueprint foram corrigidas, as premissas validadas foram registradas e a matriz 7.14 ganhou a situação de cada pendência. Q-33 e Q-35 aguardam o autor.
- **12/10/2026, revisão das seis frentes:** análise só de leitura dos dois repositórios, do documento de permissões (o `.docx` e o `.pdf` têm o mesmo conteúdo) e dos documentos, com seis frentes: o período da turma, a qualidade do feedback, os indícios de uso de IA, o plágio, os alunos de cada monitor e os grupos de monitores. O resultado está em `docs/revisao-seis-frentes.md`; a proposta das Sprints 42 a 48 está em 7.16 do blueprint, com os FR-33 a FR-37, os NFR-29 e NFR-30, as US-39 a US-47 (Épico E8), as ADR-12 a ADR-14 propostas e as perguntas Q-26 a Q-35. A pedido do autor, a Sprint 42 liga os indícios de IA no piloto e reúne as S33-02, S33-03, S33-05 e S33-06.
- **11/10/2026, plano de polimento:** até o fim do piloto, as Sprints 36 a 40 melhoram o que existe (defeitos e documentos da equipe, a tela de verificação, a explicação de cada regra e a exportação, a qualidade interna e a correção da turma inteira), a partir de uma análise com revisão dos documentos e do código e um tour da interface com 41 capturas. A Fase 2 passa a ser a Sprint 41 (S41-01 a S41-04). Plano em 7.15 do blueprint.
- **11/10/2026, branches:** as 23 branches remotas já mergeadas (todas com PR fechado) foram apagadas; ficam a `develop`, a `main` e as tags das releases.
- **11/10/2026, Q-25 decidida pelo autor:** o NFR-02 passa a ser ≤ 50 ms para entradas de até 5 KB e
  linear até 50 KB (teto de 2 s por análise), e o NFR-03, FCP ≤ 1,65 s no perfil móvel do
  Lighthouse. As proteções da CI da Sprint 35 já seguem essas metas; só a documentação mudou.

## Sprint 35 — Qualidade medida e os achados corrigidos

A Sprint 35 (S35-01 a S35-10; US-08, US-12, US-14, US-15, US-17, US-21 e US-22) fechou a engenharia
em 11/10/2026. A missão é chegar a 2027.1 com os achados recentes corrigidos (o plágio dentro de
blocos, achado ao montar o roteiro de testes manuais, e a mensagem errada sob sobrecarga, achada na
S34-03), o período 2027.1 pronto e os controles de qualidade do blueprint medindo de verdade. A
persona é o monitor-mantenedor que cuida da qualidade e opera o piloto. Com a cota do Actions
esgotada até 01/11/2026 (P-19), a evidência de cada PR é o `scripts/ci-local.sh --e2e`, que ganhou
os passos novos (27 etapas).

Aguardando:

| Task | Entrada pendente |
|---|---|
| Q-25 | A decisão do autor sobre as metas medidas pela primeira vez: NFR-02 (a entrada de 50 KB leva cerca de 260 ms) e NFR-03 (FCP de 1,51 s no perfil móvel) |
| S35-10 | A campanha de testes manuais da equipe com o `docs/testes-manuais.md` |
| S35-04 | O primeiro canário mensal no piloto (dia 1; até a cota voltar, `scripts/canario-local.sh`) |

- **11/10/2026, S35-09 (#80):** o período 2027.1 existe como cópia do 2026.2 (P-22), ainda inativo;
  todo período do repositório carrega nos testes. No mesmo PR, o teste da sessão vencida
  (`App.test.tsx`) passou a esperar a ida para Entrar, que é uma transição do roteador: falhava
  conforme a ordem dos testes.
- **11/10/2026, S35-08 (sobrecarga):** sob sobrecarga, o pool do banco esgotado respondia
  `DATABASE_UNAVAILABLE` ("o banco de contas não respondeu"). Com mais de 20 operações esperando o
  banco, a API recusa na hora com `OVERLOADED` e o `Retry-After` da admissão, e o prazo estourado com
  o pool cheio também conta como sobrecarga; o banco fora do ar continua `DATABASE_UNAVAILABLE`. No
  NFR-05 do gratuito, as 4.111 recusas saíram como `OVERLOADED`, e a mediana do 503 caiu de 5,8 s
  para 1,0 s (ADR-03).
- **11/10/2026, S35-07 (plágio):** uma linha acrescentada dentro de um laço copiado baixava a cópia
  para 83,2%, e um `else` com contador, para 76,1% ("Sem suspeitas"). Um comando com blocos passa a
  entrar no multiconjunto pelo cabeçalho e por cada comando de dentro, junto com o anterior do mesmo
  bloco; as duas cópias vão a 100% (contenção), e as soluções independentes não mudam (ADR-07,
  "Revisão da S35-07"; 5 pares novos no corpus).
- **11/10/2026, S35-05 (#83):** `ipc-rules schema` gera os esquemas JSON do ruleset e das questões
  dos modelos do carregador (`rulesets/schema/`), e a CI confere que nenhum diverge; `ipc-rules
  compile` grava o ruleset em JSON com o mesmo `ruleset_sha256` do manifesto do analisador.
- **11/10/2026, S35-01, S35-02 e S35-03 (#84):** na CI, o benchmark do motor (P95 ≤ 50 ms nas
  entradas de até 5 KB e regressão ≤ 20% sobre uma linha de base que não depende da máquina), o
  orçamento do JS inicial (104,5 KB com gzip; teto de 350 KB), o Lighthouse no perfil móvel (FCP de
  1,51 s; a CI falha acima de 1,65 s até a Q-25) e a cobertura por pasta (o motor com 90% ou mais e
  cada outra pasta com 80% ou mais). O gate achou `ipc_analyzer/runtime` com 74%: os limites do
  worker ganharam testes com um `resource` falso (83,5%).
- **11/10/2026, S35-04:** canário mensal (`canary.yml`, dia 1, e `scripts/canario-local.sh`): uma
  marca única num código verificado, comparado e usado no feedback pela página, procurada em todas
  as colunas de `app` e `telemetry`. Os logs do Render são conferidos pelo painel, com a marca
  (decisão do autor: sem chave de API do Render, que daria acesso total ao serviço).
- **11/10/2026, S35-06:** decisão do autor: só o `/health/slo` com o UptimeRobot, sem Grafana nem
  `/metrics` (C8).

## Sprint 34.1 — Lista 4 de 2026.2 com a numeração certa

Release extra depois da Sprint 34, pedida pelo autor em 11/10/2026, com a CI local como evidência
e o deploy à mão (P-19).

- **11/10/2026, Lista 4 de 2026.2 renumerada:** o autor reenviou os gabaritos da Lista 4 com a
  numeração oficial. A questão do `eval()` é a L4-Q4, e não a L4-Q3: o cadastro passa para
  `rulesets/2026.2/questions/L4-Q4.yaml`, que também libera o `reverse=` no `sort()`
  (`kwarg:sort.reverse`), usado pelo gabarito novo. A L4-Q5 é cadastrada com o valor padrão de
  parâmetro (`param:default`), também pelo enunciado. Fora dessas questões, valem as decisões
  da Q-02 (c e f): `reverse=` e valor padrão continuam na R-04. Os 28 gabaritos de 2026.2 têm zero
  violação. O ruleset continua `2026.2.5`.

## Sprint 34 — Prontidão para 2027.1

A Sprint 34 (S34-01 a S34-06; US-12, US-19 e US-22) fechou a engenharia em 11/10/2026. A missão é
chegar à primeira lista de 2027.1 sabendo como o piloto se comporta no pico, no plano gratuito
(S30-11), e com um aviso automático se a primeira verificação do dia ficar lenta ou falhar. A
persona é o monitor-mantenedor que opera o piloto. Com a cota do Actions esgotada até 01/11/2026
(P-19), a evidência de cada PR é o `scripts/ci-local.sh --e2e`. Esta release também leva ao piloto
a Sprint 33 (seção abaixo), que entrou na `main` sem tag, e a correção do `\r` sozinho.

Aguardando:

| Task | Entrada pendente |
|---|---|
| S34-05 | O ruleset de 2027.1 validado pelo professor (S33-04), para habilitar as listas (`IPC_ENABLED_LISTS`) |
| S34-06 | As datas de 2027.1 (P-10), para conferir os 7 dias de monitores verdes antes da primeira lista |
| S34-02 | Os "7 dias seguidos sem falha" do sintético contam a partir de 01/11/2026, com a cota de volta; até lá, o `scripts/sintetico-local.sh` |

- **11/10/2026, S34-02 e S34-04 (#71):** a `/api/v1/validate` responde com
  `Server-Timing: app;dur=<ms>`, o tempo dentro da API, só nessa rota (no login, o tempo exato só
  ajudaria quem ataca); o workflow "Sintético diário" (S34-02) usa esse tempo, nos dias úteis às
  07:00, e o `scripts/sintetico-local.sh` faz o mesmo desta máquina. O exercício de alerta passa a
  ser a cada release (S34-04), com o `scripts/carga-piloto.sh` no lugar da "Carga no piloto"
  enquanto a cota do Actions não volta.
- **11/10/2026, S34-01 e S34-03 (#74):** o `run_load.py` ganhou os cenários `degraus`, `nfr04` (500 por
  minuto por 15 min, 80% de 4 IPs do campus, com os limites por IP do piloto) e `nfr05` (1.500 por
  minuto e a recuperação), cada um com veredito. No gratuito emulado: no máximo 100 verificações
  por minuto sem recusa; sob sobrecarga, nenhum 500, 502 ou 504, todo 503 com `Retry-After`,
  nenhum 429 para o NAT do campus e recuperação em 5,7 s, mas os 503 levam segundos e a maioria
  diz `DATABASE_UNAVAILABLE` (achado para a Sprint 35). Números no ADR-03.
- **11/10/2026, `\r` sozinho no código:** um código com caractere não ASCII e linhas terminadas só
  em `\r` (`"Ý\rØ"`) passava pelo `ast.parse` e derrubava o `tokenize` do CPython
  (`UnicodeDecodeError`): erro 500 no plágio da turma, achado pelo schemathesis, e também nos
  indícios e no feedback. Os três passam a ler os tokens por `source_tokens` (`engine/guards.py`),
  que traduz `\r\n` e `\r` para `\n`, com a mesma numeração de linhas da AST.

## Sprint 33 — Calibração do alerta e importação dos gabaritos

A Sprint 33 (S33-01 a S33-10; US-13, US-14, US-34, US-36 e US-38) fechou a engenharia em
11/10/2026, sem release própria: entrou na `main` em 11/10/2026 e no piloto com a release da Sprint
34. O resto depende de dados externos (P-21): os gabaritos das Listas 5 e 6 de 2026.2 e dos
períodos anteriores (S33-01), as soluções anteriores a 2023 (S33-02), o documento de 2027.1 (S33-04
e S33-05) e a decisão do gerador de referências por IA (S33-09).

- **11/10/2026, S33-07 e S33-08:** `ipc-rules calibrate-gabarito` mede o alerta de vazamento em
  soluções humanas (faixas do FR-29 e alarmes falsos, só contagens e caminhos); `ipc-rules
  import-gabaritos` importa os gabaritos de uma exportação do Notion em Markdown para o repositório
  privado, nunca para este (NFR-27). Medição preliminar dos indícios nos 23 gabaritos de 2026.2
  (S33-03): 0% na faixa alta (ADR-08), só um primeiro ponto.
- **11/10/2026, L4-Q3 de 2026.2 cadastrada:** a primeira questão real (`rulesets/2026.2/questions/L4-Q3.yaml`).
  O enunciado libera `eval()` para ler as listas da entrada (`allow_facts: builtin:eval`), como
  o gabarito oficial faz; sem a questão, o `eval()` continua na R-04. O ruleset continua `2026.2.5`.
- **10/10/2026, S32-01 e S32-11 concluídas pelo autor:** a credencial dos gabaritos no Render (23
  gabaritos carregados) e as chaves do Gemini e da Groq, com a cadeia `gemini,groq`
  (`gemini-3.5-flash-lite`, que raciocina pouco, e `openai/gpt-oss-120b`, dos planos gratuitos); o
  Aprimorar com IA respondeu pelo Gemini no piloto.

## Sprint 32 — Comparação com o gabarito e Aprimorar com IA

A Sprint 32 (S32-01 a S32-14; US-32, US-34, US-37 e US-38; ADR-11 e ADR-06 revisto) fechou a
engenharia em 09/10/2026. A missão é dar à equipe, na correção, a distância entre o código do aluno
e a solução oficial e um sinal de que o gabarito pode estar circulando, sem guardar nada e sem
expor o gabarito, e deixar o feedback sem IA por padrão, com a IA só a pedido (Q-16). A persona é
quem corrige, com o Tech Lead cuidando da confidencialidade (NFR-27). Com a cota do Actions esgotada
(P-19), a evidência de cada PR é o `scripts/ci-local.sh --e2e`.

Aguardando o autor (sem elas, o piloto funciona como antes, com os avisos):

| Task | Entrada pendente |
|---|---|
| S32-01 | A credencial só de leitura dos gabaritos no Render (`IPC_GABARITOS_TOKEN`; runbook, "Credencial dos gabaritos"). Até lá, a página avisa que os gabaritos não estão disponíveis |
| S32-11 | As contas e chaves das IAs gratuitas e a cadeia no Render (`IPC_LLM_CHAIN`; runbook, "IAs do Aprimorar com IA"). Até lá, o botão Aprimorar com IA não aparece |

Medição local do NFR-28 (09/10/2026, esta máquina, só o motor): a análise do maior gabarito de
2026.2 (137 linhas) com a comparação levou 25,7 ms na mediana e 34,2 ms no P95, contra 7,9 ms e
8,9 ms sem ela; bem abaixo dos 200 ms. A carga no piloto fica para o "Carga no piloto", com a cota
de volta.

- **09/10/2026, Aprimorar com IA (S32-12 a S32-14; Q-16, ADR-06 revisto).** O **Gerar
  feedback** monta o texto sem IA e não gasta cota. O **Aprimorar com IA** manda essa versão, com o
  mesmo contexto de antes (código sem comentários, anotação, resultado, nome trocado por `[ALUNO]`),
  a uma cadeia de IAs (`IPC_LLM_CHAIN`, por exemplo `gemini,groq`), em ordem, com fallback por erro,
  prazo, cota esgotada (a IA que responde 429 fica fora por 60 s) ou texto reprovado na validação;
  sem resposta válida, fica o texto sem IA com um aviso. Na página, o botão aparece só com IA
  configurada (`can_enhance`), com o aviso de que os planos gratuitos podem usar os dados para
  treino, e **Desfazer** volta ao texto sem IA. Sem a cadeia, valem a principal e a de reserva.
- **09/10/2026, comparação com o gabarito (S32-02 a S32-09; ADR-11, FR-32, US-37, US-38).** A API
  baixa os gabaritos do repositório privado ao subir (`IPC_GABARITOS_REPO` e
  `IPC_GABARITOS_TOKEN`, só leitura) e os guarda só na memória; no compose, lê uma pasta
  (`IPC_GABARITOS_DIR`), com gabaritos sintéticos por padrão. Na verificação, uma questão com
  gabarito, mesmo sem regra cadastrada, traz a semelhança com a faixa do FR-29, as construções em
  comum, só no aluno e só no gabarito e os trechos do aluno que coincidem; no plágio, A e B também
  com o gabarito e o alerta de possível vazamento (os três acima de 95% e os códigos com 60 tokens
  ou mais, [PREMISSA] até a S33-02). Nos indícios, o sinal "Semelhança com o gabarito". O
  analisador recebe o gabarito na chamada interna, prepara-o com cache por hash e devolve só
  porcentagem, nomes de construções e linhas do aluno; testes canário garantem que nenhum texto do
  gabarito chega a uma resposta ou a um log.
- **09/10/2026, ensaio do cadastro (S31-13):** a questão L3-Q9 ("Ensaio: média da turma sem
  sum()"), criada para o ensaio a pedido do autor, libera `map()` e proíbe `sum()`, `sort()` e
  `sorted()`; enunciado e resultado em `docs/ensaio-cadastro.md`, com testes no backend e no e2e.

## Sprint 31.1 — Casos do Marco 2 e decisões do autor

Release extra entre as Sprints 31 e 32, pedida pelo autor em 09/10/2026, com a CI local como evidência
e o deploy à mão (P-19).

- **09/10/2026, ruleset `2026.2.5`: os casos do Marco 2, decididos pelo autor.** Passam a ser
  permitidos: o `if __name__ == "__main__":` e o argumento nomeado numa função do aluno, a partir
  da Lista 4 (R-59); vários nomes no `for` com qualquer iterável, a partir da Lista 3 (R-40); o
  `zip()` de 2 ou mais sequências no `for` de uma compreensão (R-37); e, na Lista 5, os argumentos
  nomeados de `dict()` e `update()` e o `start=` de `enumerate()` (R-62, R-66 e R-63). A lista de um
  `split()` comprova o assunto da Lista 3 (R-02). A expressão geradora foi ratificada; a recursão por
  `lambda` continua sem contar. No motor: o fato `kwarg:<função>.*` para os argumentos nomeados de
  `dict()` e `update()`, que são chaves livres, e o predicado do `zip` também no `for` das
  compreensões. Casos golden: 303.
- **09/10/2026, decisões do autor:** política dos indícios de IA aprovada (Q-21); Q-16 com o
  feedback sem IA como padrão e um "Aprimorar com IA" futuro, com provedores gratuitos em cadeia;
  Q-17 e Q-22 mantêm como está; questões e gabaritos cadastrados por monitores, monitores-chefes,
  professores e o desenvolvedor; Marco 2 em 19/10/2026.
- **Plano:** o "Aprimorar com IA" (Q-16) entra na Sprint 32 (S32-11 a S32-14). `scripts/release.sh`
  aceita releases extras (`31.1`).

## Sprint 31 — Auditoria bloqueante e período sem código

A Sprint 31 (S31-01 a S31-13; US-11, US-13, US-15, US-23, US-32, US-34 e US-36) fechou a engenharia em
09/10/2026; as decisões e tarefas externas ficam "aguardando", com a entrada pendente, como o plano
prevê. A missão é a auditoria bloqueante e o período pronto para trocar sem mudar código; a persona
é o Tech Lead e monitor-mantenedor. Com a cota do GitHub Actions esgotada até 01/11/2026 (P-19), a
evidência de cada PR é o `scripts/ci-local.sh --e2e`, com o resumo no PR. Decisões de implementação:

- **S31-09 a S31-11 (#62):** o arquivo `rulesets/ATIVO` tem a única linha com o período ativo
  (`2026.2`); o analisador (`IPC_RULESET_PATH=/opt/ip-checker/rulesets` nas duas imagens e no
  supervisord), a CI, o `ci-local.sh` e o `ipc-rules validate ../rulesets` leem dali, e um teste
  falha se a configuração repetir o período. O nome da variável não mudou, para não mexer no
  ambiente do analisador nem no `render.yaml`. `ipc-rules new-period 2027.1 --from 2026.2` cria a
  pasta do período novo, validada (296 de 296 casos golden), sem questões e sem ativá-lo; o
  carregador recusa um `base.yaml` cujo `period` difere do nome da pasta. O harness dos gabaritos
  usa o ruleset do período de cada gabarito, quando `rulesets/<período>/` existe.
- **S31-03 e S31-04 (P-20):** novo job "Auditoria" no `ci.yml`, em todo PR: gitleaks no histórico,
  Semgrep com as regras próprias de `.semgrep/ip-checker.yml` (9 regras, com casos de teste),
  `pip-audit` e `npm audit`; o `ci-local.sh` roda os mesmos passos, e o `audit.yml` semanal perde o
  `continue-on-error`. Primeira triagem: 3 falsos positivos do gitleaks no `.gitleaksignore`; na
  imagem do piloto, a base `python:3.13-slim` vai para o digest de 06/10/2026 (OpenSSL e PCRE2
  corrigidos, Python 3.13.16) e o `pip`, que o runtime não usa e embutia bibliotecas vulneráveis,
  sai das duas imagens; o Trivy ficou sem achados altos ou críticos corrigíveis. Um commit com token
  falso, uma dependência vulnerável e um `eval` sobre o corpo da requisição falham nos mesmos
  comandos (provado nesta máquina; a primeira rodada no Actions fica para a volta da cota).

- **Release (decisão do autor, P-19):** sem a cota do Actions, `scripts/release.sh 31 --ci-local`
  aceita a rodada completa e sem falha do `ci-local.sh --e2e` na árvore da `develop`, e o deploy é
  à mão pelo runbook. O teste de tempo da similaridade passou a medir o NFR-25 sem a instrumentação
  de cobertura, que sozinha o fazia passar de 2 s no Windows.

Aguardando (a sprint não espera por elas, critério de aceite 1):

| Task | Entrada pendente | Com quem |
|---|---|---|
| S31-01 | Aprovação da política dos indícios de IA (`docs/indicios-de-ia.md`), item 3 da pauta do Marco 2; os indícios seguem desligados no piloto | Coordenação |
| S31-02 | Q-16, provedor de IA do feedback (7.13.2); o feedback segue por modelos de texto, sem enviar nada a terceiros | Autor e coordenação |
| S31-05 | Data do Marco 2 e revisão do guia da equipe | Autor |
| S31-06 | Os links do formulário da pesquisa e da planilha do critério 3, em `docs/eficacia.md` | Equipe |
| S31-07 | Q-17, remetente definitivo dos e-mails e SPF, DKIM e DMARC (7.13.3); segue o remetente atual pelo Brevo | Autor e NTI |
| S31-08 | Q-22, governança das regras (7.13.4); vale a aprovação por processo do `RULES.md` | Autor |
| S31-12 | O Marco 2: os casos 1 a 9 do mapeamento decididos ou adiados e o caso 10 (expressão geradora) ratificado ou revertido | Autor, monitores-chefes e professores |
| S31-13 | O ensaio do cadastro de questões reais de 2026.2 pelo `RULES.md` | Equipe e professor |

Também nesta release, feito entre as Sprints 30 e 31:

- **09/10/2026, ruleset `2026.2.4`: expressão geradora a partir da Lista 3.** A R-41 (*list
  comprehension*) passa a casar também `node:GeneratorExp`, por decisão provisória do autor
  (revisão da Q-02 e), a ratificar no Marco 2 (caso 10 de `docs/marco-2.md`). A *dict
  comprehension* continua na R-04. Origem: o gabarito oficial L3-Q8 de 2026.2, que usa
  `" ".join(str(num) for num in ...)` e agora tem zero violação, como os outros 22 de 2026.2. Quatro
  casos golden novos (Listas 2, 3 e 6 e a *dict comprehension*) e o caso da Lista 3 atualizado.
- **09/10/2026, plano:** a comparação com o gabarito (ADR-11, Q-24, FR-32, US-37, US-38) vira a nova Sprint 32; as antigas Sprints 32 a 35 passam a 33 a 36, com as tasks renumeradas. O NFR-27 admite os gabaritos na memória da API do piloto; o NFR-28 mede o custo da comparação.
- **08/10/2026:** CI e backup locais sem a cota do GitHub Actions (P-19), o repositório dos gabaritos
  (ADR-10) e a pauta do Marco 2.

## Sprint 30 — Piloto verificado ponta a ponta

A Sprint 30 (S30-01 a S30-12; US-17, US-19, US-20, US-22, US-26, US-32 e US-35) foi concluída em
08/10/2026. A missão é o "Deploy do
piloto" verde sem nenhum passo pulado, com alerta, backup e rollback ensaiados e medidos; a persona é
o monitor-mantenedor. O primeiro deploy completo é o run 37761090896 (`2a55908`): migração, Render,
Vercel, verificações com login, smoke e2e no piloto e o limite por IP, todos verdes. Decisões de
implementação:

- **S30-01 (autor):** conta de verificação "Lionzio", com um subendereço da caixa institucional do
  autor (os e-mails da conta do desenvolvedor são reservados a ela), e os secrets `PILOT_CHECK_*`.
- **S30-02:** `tests/pilot` ganhou o feedback pela página em até 30 s; o teste do login esperava as
  violações sem a exigência R-02 da Lista 1 (Sprint 23), porque nunca tinha rodado sem a conta.
- **S30-03:** o limite por IP do piloto não limitava ninguém: com 2 saltos, a chave era um proxy
  interno do Render, diferente a cada requisição. Com o diagnóstico `/api/v1/proxy-check` (devolve a
  quem chama só os cabeçalhos de proxy e o IP que o limite usaria, sem log), a estrutura real foi
  medida: o cliente vem do `Forwarded: for=`, que a Vercel sempre reescreve, e, sem ele, da 4ª
  entrada do `X-Forwarded-For` a partir do fim (ou da primeira, direto no Render); sem sessão, um
  segundo limite de 60 por minuto usa o `cf-connecting-ip`, que o cliente não forja. O último passo
  do deploy (`tests/pilot/test_rate_limit.py`) confere tudo a cada release. Risco residual na P-15.
- **S30-04:** o plano gratuito do UptimeRobot só consulta com HEAD, e a API respondia 405: as rotas
  de operação respondem HEAD, fora do OpenAPI. Os três monitores foram criados, de 5 em 5 min, com
  alerta por e-mail.
- **S30-05:** exercício de alerta com `IPC_SLO_P95_MS=50` por uma release e 10 min de carga: do 503
  ao e-mail do UptimeRobot, 61 a 92 s (NFR-15: até 5 min). A meta voltou a 200 ms, escrita no
  `render.yaml` (P-18).
- **S30-06 e S30-07:** chave `age` gerada fora do repositório e `BACKUP_AGE_RECIPIENT` gravada; o
  backup passou a registrar as linhas por tabela (`deploy/backup/contagens.sql`) no resumo do run e
  no artefato. Ensaio de restauração: linhas iguais nas 9 tabelas, RTO técnico de 9 s.
- **S30-09:** carga no Render com login, 20 por minuto: P95 do servidor entre 127 e 195 ms, k6 com
  P95 de 272 a 282 ms do GitHub à página, 0% de falhas; a sessão no banco soma cerca de 10 ms (Q-20).
- **S30-10:** o Render roda sem `CAP_KILL` (P-17), e nem o `kill()` nem o `PR_SET_PDEATHSIG` de um
  root alcançam outro usuário. `deploy/render/run_as.py`: o supervisord sinaliza um lançador root,
  que fecha um pipe; um guardião com o usuário do serviço o encerra. O `env -i` do analisador veio
  para antes do lançador. A suíte do piloto roda sem `CAP_KILL` e confere o desligamento em menos de
  15 s, sem `CRIT`; nos logs do Render, nenhum `CRIT` desde a correção.
- **S30-11 (autor):** plano gratuito, sem orçamento (ADR-03).
- **S30-12 (autor):** backup diário, às 06:00 UTC; a NFR-20 continua com RPO de até 24 h.
- **S30-03, só pela página:** para fechar o risco residual da P-15, o middleware da Vercel
  (`frontend/scripts/edge-middleware.mjs`, Build Output API) manda em `/api/*` um segredo que só
  a página e a API conhecem (`IPC_EDGE_SECRET`, cadastrado nos dois painéis) e o IP do cliente
  que a Vercel determinou; com o segredo configurado, o Render responde 403 a `/api/*` sem ele
  (`ipc_api/edge_gate.py`). As rotas de operação continuam abertas para o UptimeRobot.
- **Achado (P-18):** uma release que muda o `render.yaml` é publicada pela sincronização do Blueprint
  antes da migração do pipeline; uma release com migração não muda o `render.yaml`.
- **S30-08:** rollback ensaiado pelos painéis, com o autor cronometrando (`scripts/rollback-check.sh`):
  a API voltou em cerca de 1 min e a página logo depois da confirmação, no total cerca de 4 min
  (meta: até 5 min). Na Vercel, um Instant Rollback deixa os deploys novos fora de Production até o
  **Promote** da versão atual; o runbook registra isso.
- **Segredo da página ligado:** `IPC_EDGE_SECRET` cadastrado pelo autor, primeiro na Vercel e depois
  no Render. O "Deploy do piloto" de 08/10/2026 (run 37775207076) confirmou, com login e e2e, que a
  página funciona e que `/api/*` direto no Render recebe 403.
- **Fica para 09/10/2026:** conferir os 24 h verdes do UptimeRobot (critério 4).

## Sprint 29 — Indícios de uso de IA, nunca veredito

A Sprint 29 (S29-01 a S29-04; ADR-08, Q-21, US-34) foi concluída em 07/10/2026. A missão é dar à
equipe motivos explicáveis para decidir com quem conversar, sem acusar ninguém por um número; a
persona é quem corrige (monitor, monitor-chefe ou professor), e o aluno nunca vê os indícios.
Decisões de implementação:

- **S29-01:** `engine/indicators.py`, no analisador isolado (a árvore só existe ali), a partir das
  violações que o motor já achou e da mesma árvore: variedade (proibições gerais diferentes, contadas
  por construção, porque `break` e `continue` são a mesma regra R-11), repetição, salto de lista (2
  ou mais listas depois da escolhida; o `for` na Lista 1 é erro comum e não conta) e construções
  fora do documento (R-04), com as faixas iniciais da ADR-08 [PREMISSA]. Os marcadores de estilo
  (docstring, anotações de tipo, `if __name__`, nomes e comentários em inglês, por listas iniciais
  de palavras) são fatos sem faixa. Cada indício traz o motivo em PT-BR e as linhas (até 200), e o
  conjunto traz 2 ou 3 perguntas para a conversa. Uma solução limpa, uma proibição isolada ou um erro
  de sintaxe não mostram nada.
- **S29-02:** as referências ficam em `rulesets/<período>/referencias/<questão>/*.py` (até 10 por
  questão), neste repositório privado, carregadas com o ruleset e incluídas no SHA-256 dele; o
  carregador recusa referência de questão não cadastrada, inválida ou grande demais. A comparação
  usa o motor da ADR-07 (`compare_prepared`), com as referências preparadas uma vez por worker, e
  mostra a mais parecida a partir de 80%, nas faixas do plágio. Ainda não há questão real
  cadastrada, então o mecanismo foi testado com uma questão de teste.
- **S29-03:** a API pede os indícios ao analisador só com `IPC_AI_INDICATORS=1` e os devolve no campo
  `indicators` do `/validate`, com o aviso de que não são prova; o `/auth/options` diz se estão
  ligados. Nada vai para o feedback, a telemetria, o log ou o banco. O painel "Indícios de uso de
  IA" aparece abaixo do resultado só quando há indício, com a faixa, cada motivo, as linhas
  clicáveis (selecionam no editor) e as perguntas; os marcadores de estilo ficam à parte, sem faixa.
- **S29-04:** `docs/indicios-de-ia.md` (proposta de política para a coordenação, o texto para os
  alunos, quem gera as referências e como ligar), a seção no guia da equipe, o passo 5 do
  `RULES.md` e o `ipc-rules calibrate`, que mede as faixas em soluções humanas
  (`<período>/lista-<n>/*.py`) e falha acima de 5% de faixa alta, sem nunca mostrar código. A
  chave fica desligada no piloto (`render.yaml`, conferido por teste e pela verificação do piloto)
  até a política ser aprovada e a calibração ficar na meta, o que depende das soluções anteriores a
  2023 (Q-14).

Sem migração de banco e sem dado novo: o deploy é igual ao da Sprint 28. O e2e com a chave ligada
roda no projeto "feedback", com conta própria, para não gastar o limite por conta do projeto
principal.

## Sprint 28 — Carga, eficácia e passagem de bastão

A Sprint 28 (S28-01 a S28-04) foi concluída em 07/10/2026, no mesmo dia em que o piloto subiu
(Render, Vercel e Supabase), com estas decisões de implementação:

- **S28-01:** o `pilot-load.js` entra com uma conta antes de verificar e mede também uma rota que
  só consulta a sessão no banco (`/auth/me`) e uma que não consulta o banco (`/auth/options`); a
  diferença entre as duas é a distância até o Supabase (Q-20). O `run_load.py` sobe um PostgreSQL,
  aplica as migrações e entra com a conta do desenvolvedor desse banco descartável, com os limites
  por conta e por IP aumentados só ali. Com login, o plano gratuito não atende o P95 ≤ 200 ms nem
  com 30 verificações por minuto (P95 de 383 ms, pela cota de 0,1 CPU), e o Starter atende 500 por
  minuto com P95 de 28 ms: a recomendação passou a ser o Starter antes do primeiro prazo (ADR-03).
  O workflow manual "Carga no piloto" (`load.yml`) roda o k6 no piloto de verdade, pela página, com
  a conta de verificação, a até 25 por minuto, e traz o P95 do servidor (`/health/slo`); ele espera
  a conta de verificação.
- **S28-02:** a primeira verificação de cada conta em cada lista do período grava
  `app.list_adoption` (conta, período e lista, sem data nem resultado), fora do caminho da resposta,
  com a combinação já gravada guardada na memória; a view `telemetry.v_team_adoption_by_list`
  devolve só a porcentagem de membros ativos por lista, para o `ipc_reader`. A conta de verificação
  do deploy ganhou a marca `check_account`, gravada pelo passo das migrações do pipeline
  (`IPC_CHECK_ACCOUNT_LOGIN`, uma conta marcada por vez): as verificações dela não entram na
  telemetria nem na adoção, e ela não conta como membro. `docs/eficacia.md` diz como medir os cinco
  critérios da P-09 e traz o formulário da pesquisa de satisfação. O aviso de privacidade conta a
  adoção e o backup.
- **S28-03:** `docs/onboarding.md` (do zero ao compose e ao e2e verdes), `CONTRIBUTING.md`,
  `SECURITY.md` e `docs/README.md` como mapa. O `deploy/README.md` virou um índice de
  `deploy/piloto.md`, `deploy/compose.md` e `deploy/seguranca.md`. O runbook ganhou o índice por
  sintoma, o registro dos ensaios de rollback, a latência do `/health/slo`, a conta de verificação,
  o backup e a restauração e o registro de incidentes. O workflow `backup.yml` faz, todo domingo, o
  `pg_dump` dos esquemas `app` e `telemetry`, confere com o `pg_restore --list`, criptografa com o
  age (chave pública em `BACKUP_AGE_RECIPIENT`; a privada fica só com o autor) e guarda 90 dias como
  artefato. O primeiro ensaio cronometrado do rollback espera o primeiro deploy completo pelo
  pipeline.
- **S28-04:** o blueprint foi dividido: os ADRs em `docs/adr/`, a antiga seção 1.3 em
  `docs/decisoes.md` e os parágrafos "Situação" neste `CHANGELOG.md`, conferido linha a linha para
  nada se perder. Uma auditoria das afirmações sobre controles corrigiu ou marcou [PLANEJADO] o que
  não existe (CODEOWNERS e *branch protection*, que o GitHub Free não aplica em repositório privado;
  GHCR e deploy por SSH; Prometheus e Grafana; pytest-benchmark, Lighthouse, Semgrep e o k6 por
  release; o editor CodeMirror). O `scripts/release.sh` faz o fast-forward da `main`, a tag
  `sprint-NN` e o GitHub Release com a seção daqui. O `migrate` guarda o SHA-256 de cada migração
  aplicada e recusa uma que mudou depois (as aplicadas antes ganham o SHA-256 na primeira execução;
  versões mais novas que a pasta são ignoradas, para o rollback). O e2e cria uma conta por projeto
  que mexe na própria conta, pelo caminho de verdade, e a pausa de 61 s saiu. Na CI, um primeiro
  job decide o que roda: na `main`, só a política de branches (o commit já passou na `develop`); com
  só `.md` mudando, nenhum teste. O modelo de PR ganhou "Como foi testado" e os itens de dados,
  migração, contrato e documentação.

Antes da primeira release pelo pipeline, as verificações do piloto rodaram contra o piloto de
verdade pela primeira vez e acharam duas expectativas antigas nos testes (a CSP com o endereço do
Render, de antes da mesma origem, e o `/auth/options` sem o `feedback_ai`); o piloto estava
certo, e os testes foram corrigidos. Enquanto a conta de verificação não existe, o pipeline
confere o que não precisa de login e avisa, em vez de falhar.

O primeiro deploy pela `main` (07/10/2026) travou 15 minutos instalando o Chromium: um espelho
do Ubuntu parou no meio de um download, e o `apt` não tem prazo para isso. Foi cancelado antes
de publicar qualquer coisa. Desde então, o deploy só instala a página e o Chromium quando o smoke
e2e vai rodar (com a conta de verificação), e a instalação, no deploy e na CI, tem prazo de 30 s
por espelho no `apt` e de 10 minutos no passo.
Na segunda tentativa, a migração 0006 e o deploy da API passaram, mas o passo parou na primeira
consulta ao `/ready` que demorou mais de 20 s: com `bash -e`, a falha do `curl` dentro de
`api=$(...)` encerrava o laço de espera. A consulta agora nunca falha (`|| true`), e quem desiste é
o laço, depois de 25 minutos para a API e 10 para a página.

## Sprint 27 — Plágio por árvore canonizada

A Sprint 27 (S27-01 a S27-03) foi concluída em 06/10/2026, com estas decisões de implementação:

- **S27-01:** o motor fica em `engine/similarity_tree.py`, no analisador isolado, sobre a mesma árvore da análise (com os limites de `guards.py`). As reescritas (`+=`, `if` negado com `else`, retorno antecipado, laços) mudam a árvore; a ordem canônica dos operandos (`+`, `*`, `&`, `|`, `^`, `and`, `or`, `==`, `!=`, `is`), a troca de `>` por `<` e a reordenação por dependência entram direto no hash de baixo para cima, numa passada só: nenhuma subárvore é percorrida duas vezes, e a cadeia `1+1+…+1` não fica quadrática. As comparações de ordem num `if` com `else` ficam sempre na forma `<`, trocando os ramos quando preciso (`if x >= 7: A else: B` é `if x < 7: B else: A`). Os três laços equivalentes viram um laço genérico sobre a sequência (`for x in v`, `for i in range(len(v))` com `v[i]` e `while i < len(v)` com `v[i]`, `i += 1` e o `i = 0` logo antes); `for i in range(n)` e `while i < n` viram o laço até `n`. A reordenação só troca comandos vizinhos sem dependência de dados; `input`, `print` e as chamadas de funções do aluno mantêm a ordem entre si, uma chamada de método conta como escrita no objeto (`v.append`), e laços, `return`, `break`, `try` e `with` são barreiras. No nível do módulo a ordem nunca conta, porque o módulo não entra no multiconjunto. A similaridade é o maior de três números: a métrica da ADR-05 (que continua como segunda métrica, item 7), o Dice da árvore e a contenção, esta só quando o menor código tem pelo menos 25% do tamanho do maior (um código de três linhas sempre "cabe" num programa grande). No corpus, todas as reescritas da tabela da ADR-07 deram 100% (inclusive todas juntas, que a ADR-05 dava 42,9%), e as soluções independentes ficaram entre 0% e 22%; dois códigos de 50 KB são comparados em cerca de 0,3 s.
- **S27-02:** `POST /api/v1/similarity/batch` compara uma solução com até 100 da turma num worker só, com prazo próprio (10 s no analisador, 12 s na API) e uma vaga de análise. Só a árvore entra, com o peso de cada subárvore pelo IDF da turma, `ln((N + 1) / df)` normalizado; a métrica da ADR-05 não tem como ser pesada pela turma. A solução com erro de sintaxe ou recusada pelos limites aparece na lista, no fim, com o motivo; erro na solução comparada é a resposta inteira. O corpo continua limitado a 128 KB: a página aceita até 120 KB de soluções e pede que turmas maiores sejam comparadas em partes. A rota entra no limite por conta das verificações.
- **S27-03:** a resposta de `/api/v1/similarity` traz as três métricas e até 30 pares de intervalos de linhas com a mesma estrutura, dos maiores para os menores, sem sobreposição, só de comandos com pelo menos 6 nós. A página marca os trechos nos dois editores, destaca o par escolhido e rola os dois até ele; a rolagem sincronizada é opcional. Os trechos somem quando um dos códigos muda depois da comparação. O botão da página virou "Limpar os dois", porque cada editor já tem o seu "Limpar".

No stack local, o e2e completo passou com a cópia disfarçada (funções e linhas reordenadas, nomes trocados e o `for` virando `while`) aparecendo como Plágio, com o par de trechos certo nos dois lados, e com a comparação contra a turma pondo a cópia em primeiro lugar.

## Sprint 26 — Correção em lote e relatório

A Sprint 26 (S26-01 a S26-04) foi concluída em 06/10/2026, com estas decisões de implementação:

- **S26-01:** o cabeçalho mostra só "IP-Checker" e a navegação no celular; o subtítulo aparece a partir de 640 px, e o nome de quem está logado a partir de 1024 px (no celular, ele fica no `title` do link Perfil). A navegação é uma lista em `<nav aria-label="Principal">`, com `aria-current="page"` na tela atual, inclusive Verificar; os itens têm 44 px de altura nas telas de toque. Cada tela tem o próprio `<title>` ("Verificação · IP-Checker"), e a verificação ganhou o `<h2>` "Verificação". Os componentes `Button`, `TextLink` e `ErrorText` ficam em `components/ui.tsx`, com as classes em `ui.ts`, e os rótulos da navegação, dos títulos e do resumo foram para o `labels.ts`. Os textos cinza-claros que não passavam no contraste AA do tema escuro foram trocados; o axe não acha violações graves nos dois temas, conferido no e2e.
- **S26-02:** o rascunho (código, lista, questão, nome do aluno e anotação) fica num contexto acima da sessão, só na memória: sobrevive à navegação e ao novo login depois de a sessão vencer, e **Sair** o apaga. Só o número da última lista vai para o `localStorage`. Depois de verificar, o foco vai ao título do resultado (com rolagem); depois de gerar o feedback, a Copiar. O aviso de nome repetido aparece quando o código verificado é outro e o nome é o mesmo do último feedback gerado. O Tab insere 4 espaços e mantém o desfazer do navegador; Esc e depois Tab sai do editor (sem armadilha de teclado, WCAG 2.1.2). O e2e conta 4 ações por aluno: colar, Ctrl+Enter, nome e Enter, Próximo aluno.
- **S26-03:** as violações são agrupadas por regra e mensagem, na ordem anulação, proibição da questão, exigência, fora da lista e não consta, e dentro de cada uma pela primeira linha; cada categoria tem uma cor (anulação vermelha, questão fúcsia, exigência roxa, fora da lista âmbar, não consta azul) e uma borda à esquerda. Cada ocorrência é um botão "Linha L, coluna C" que seleciona no editor o trecho que o motor apontou, até `end_line` (um `for` inteiro, por exemplo), e marca essas linhas na numeração. O trecho mostrado no cartão é a primeira linha da primeira ocorrência, do código que foi verificado.
- **S26-04:** `useApiCall` dá a todas as chamadas do plágio e do feedback um prazo (15 s e 40 s), cancelamento (botão Cancelar) e o tratamento central da sessão vencida. Uma 401 `UNAUTHENTICATED` em qualquer tela leva a Entrar com o aviso e, depois de entrar, de volta à tela de origem; uma 401 de senha atual errada no perfil não conta como sessão vencida. Durante a verificação o editor fica só para leitura, sem perder o foco. O leitor de tela recebe só o resumo do resultado, numa região viva própria, e não o relatório inteiro. O gerenciamento ganhou busca por nome ou e-mail (sem acento), filtro por cargo, "Mostrar mais" no registro (20 por vez) e ocupado só na linha da ação. O cliente simulado exige a sessão e ganhou `# simular: truncado`, `limite_analise` e `ia`.

No stack local, o e2e completo passou com os testes novos de lote, clique na violação, largura de 375 px e axe nos dois temas.

## Sprint 25 — Endurecimento para o primeiro deploy

A Sprint 25 (S25-01 a S25-05) foi concluída em 06/10/2026, com estas decisões de implementação:

- **S25-01:** todas as actions fixadas por SHA (com a versão no comentário), `persist-credentials: false` em todo checkout, exceto o da política de branches, que precisa do histórico; o `uv` fixado em 0.12.21; o `openapi-typescript` continua no `npx` com a versão fixada, porque a 7.13 pede TypeScript 5 e o projeto usa o 6; Dependabot mensal para a `develop`, agrupado; o job `audit` (gitleaks, pip-audit, npm audit e trivy na imagem do piloto) roda toda semana e ainda não bloqueia; o job dos gabaritos não roda para o Dependabot, que não recebe o segredo.
- **S25-02:** o deploy aceita `workflow_dispatch` só na `main` e só para um commit com a CI verde; as instalações rodam sem segredo no ambiente; antes de cada etapa o pipeline confere se o commit ainda é a ponta da `main` e, se não for, encerra sem publicar; o Render vem primeiro, e a Vercel só depois de o `/ready` responder com o commit certo (prazo de 25 min), com outro prazo para o `version.json` da página. O health check do Render passou a ser `/health/service` (API e analisador, sem o banco), e não `/health`, para uma oscilação do banco não derrubar a instância nem travar o deploy; o `/ready` continua checando o banco para o UptimeRobot. A tabela de migrações saiu do `public` para o esquema `ipc_meta`, fora do alcance da Data API do Supabase, e uma tabela antiga é movida sozinha. O roteiro do primeiro deploy (`deploy/README.md`) tem a migração manual antes do Render e uma lista de conferência com a P-15, e o `docs/runbook.md` cobre rollback, deploy parado, banco ou analisador fora do ar e troca de segredos.
- **S25-03:** a migração é a `0005` (a `0004` ficou com a redefinição de senha). A limpeza apaga sessões vencidas, links usados ou vencidos, cadastros não confirmados 48 horas depois do último pedido (um novo cadastro com o mesmo e-mail recomeça o prazo), contas fora do status `ativo` com 365 dias sem atividade (nunca a do desenvolvedor nem as criadas pela semente), o registro de gerenciamento com mais de 12 meses e a cota de feedbacks de antes de ontem. A atividade é o cadastro, cada login, a confirmação do e-mail, a redefinição da senha e cada mudança de status ou de cargo. Uma conta apagada leva os e-mails (que ficam livres), as sessões, os links e a cota; quem ela aprovou fica sem "quem decidiu", e o registro de gerenciamento guarda os nomes, só sem o vínculo com a conta. Os prazos são contados pelo relógio do banco: a API não consegue apagar nada antes da hora. A tarefa roda ao subir e a cada 24 horas (`IPC_HOUSEKEEPING`, `IPC_HOUSEKEEPING_INTERVAL_S`), e as contagens desde a subida aparecem em `/health/slo`.
- **S25-04:** no Render, o analisador roda com 1 worker e a API admite 1 análise por vez (`deploy/render/supervisord.conf`). O prazo da API para o analisador é o do pool mais 1 s (`IPC_TIMEOUT_S` + 1, ou `IPC_ANALYZER_TIMEOUT_S`) e vale para a chamada inteira, não para cada leitura; ele vai no cabeçalho `X-IPC-Budget-Ms`, e o analisador descarta o pedido que vence na fila, sem analisá-lo, e interrompe a análise que passaria do prazo (503 `DEADLINE_EXCEEDED`, que só aparece no log). Cada operação no banco tem 5 s, incluindo a espera por uma conexão do pool; a sessão e a conta vêm numa consulta só. Todo `/api/*` tem um limite por IP de 600 por minuto (6.000 nas faixas do campus), contado antes da sessão, numa janela fixa de 1 minuto; o contrato OpenAPI descreve esse 429 na introdução, sem repeti-lo em cada rota. A API não sobe com `IPC_PUBLIC_BASE_URL` sem `https://` quando o cookie é seguro, exceto em `localhost`, `127.0.0.1` e `::1`, que o navegador trata como seguros. O worker nega também `io_uring_*`, `ptrace`, `process_vm_readv`/`process_vm_writev`, `bpf`, `userfaultfd`, `unshare` e `setns` (os que a libseccomp do sistema conhece; as quatro chamadas originais continuam obrigatórias), não grava core dump e não cria processos nem threads (`RLIMIT_NPROC` = 0, aplicado por último, porque a libseccomp é procurada com um subprocesso). Uma exceção inesperada vira 500 `INTERNAL_ERROR` em JSON, com o `X-Request-Id` na mensagem e no cabeçalho, sem detalhes da falha. O Google e o Brevo deixaram de usar proxies do ambiente.
- **S25-05:** o analisador troca por `...` toda docstring e todo texto solto no código do feedback, além de tirar os comentários; a API mascara e-mails (`[EMAIL]`), CPFs com pontuação (`[CPF]`) e números com 8 ou mais dígitos (`[MATRICULA]`, inclusive dentro de um nome) no código e na anotação, antes de trocar o nome do aluno por `[ALUNO]`; o trecho livre da IA que repete uma dessas marcas é recusado. A cota de feedbacks fica no banco (`app.feedback_quota`, na mesma migração `0005`), por conta e dia UTC, e só é cobrada depois de a análise dar certo: um código com erro de sintaxe ou o analisador fora do ar não gastam nada.

No stack local, o e2e completo passou com a imagem nova; os testes que dependem do Linux (seccomp, rlimits e o pool) passaram num contêiner Linux antes do PR.

Manutenção (06/10/2026): o Dependabot (S25-01) abriu na primeira rodada saltos de versão principal que quebrariam o projeto, misturados a atualizações seguras: Postgres 17 → 18 (a imagem muda o caminho dos dados, e o banco do compose não sobe; o Supabase do piloto está na 17), TypeScript 6 → 7 (o typescript-eslint ainda não aceita) e @types/node 24 → 26 (tipos de um Node que o projeto não usa). O `dependabot.yml` passou a ignorar esses saltos, e também o do Python além de 3.13 e o do Node além de 24 nas imagens, para não deixar o analisador e o build fora do ar; correções e versões menores continuam chegando. Cada salto vira uma tarefa feita de propósito, com o seu gatilho: Postgres 18 quando o Supabase do piloto subir, junto com o volume do compose; TypeScript 7 quando o typescript-eslint aceitar; Node e `@types/node` juntos, com o `engines`, as imagens e a CI; Python 3.14 junto com o ruleset (`target_python`), o `pyproject.toml` e as imagens.

## Sprint 24 — Regras por questão, ipc-rules e esqueci minha senha

A Sprint 24 (S24-01 a S24-04) foi concluída em 06/10/2026, com estas decisões de implementação:

- **Onde ficam as questões:** em `rulesets/2026.2/questions/`, o período do ruleset ativo, e não numa pasta 2027.1, que ainda não existe; quando o ruleset de 2027.1 for criado, as questões dele vão para a pasta dele (P-07). Nenhuma questão real foi cadastrada, porque o conteúdo vem dos enunciados; a pasta traz só um `LEIA-ME.md`, e o seletor da página diz "Nenhuma questão com regra específica cadastrada".
- **Precedência:** a proibição da questão sai com o ID R-01 e a categoria `PROIBIDO_NA_QUESTAO`; `allow` libera regras inteiras com as condições delas (liberar a R-37 libera o `zip` no `for`, não qualquer `zip`); `allow_facts` libera fatos sem condição; as exigências (R-02 e R-68) e as meta-regras não mudam com a questão.
- **Validação:** o carregador recusa a questão com nome de arquivo diferente do `question_id`, lista diferente da do nome, R-xx inexistente, meta-regra ou exigência em `allow`/`deny`, proibição geral em `deny` (já vale sempre), fato estrutural e o mesmo fato liberado e proibido; ele marca as proibições gerais liberadas, que o `ipc-rules` mostra como aviso (anotação no PR, C-02).
- **Versão:** o `ruleset_version` continua mudando só com o `base.yaml`, para um PR de questão não disputar a versão com outro; o `ruleset_sha256` do manifesto e do `/internal/health` passa a cobrir as questões.
- **API:** a questão é conferida no manifesto do analisador (`UNKNOWN_QUESTION` para questão inexistente ou de outra lista) e de novo no analisador, antes do worker; com questão, o aviso `QUESTION_RULES_NOT_APPLIED` some; a telemetria grava a questão; o feedback usa a mesma questão da verificação; `GET /api/v1/lists` traz as questões de cada lista.
- **Gabaritos:** só um gabarito do período ativo cujo nome é a questão (`2026.2/lista-3/L3-Q2.py`) usa as regras dela; os de períodos anteriores continuam no `excecoes.yaml`, porque as questões deles não ficam cadastradas (P-07).
- **S24-02:** `ipc-rules validate <período> [--golden <pasta>]` sai com 0, 1 ou 2 e virou passo bloqueante do job do backend; os predicados ficam em `engine/predicates.py`, do qual o carregador tira os parâmetros e as condições tiram a função; o `facts.py` virou o pacote `facts/` (modelo, extrator e grafo de chamadas), com a mesma interface.
- **S24-03:** governança por processo, porque a Q-22 foi adiada: `RULES.md` com um exemplo comentado (conferido pelo `ipc-rules`) e o modelo de PR `.github/PULL_REQUEST_TEMPLATE/regras.md`.
- **S24-04:** o link de redefinição vale por 1 hora (o de verificação vale 24 horas); só o recebe quem já confirmou o e-mail e não foi recusado, inclusive contas na fila de aprovação e removidas; o pedido responde sempre 202 e segue o limite do reenvio; a troca da senha gasta o token na mesma transação e encerra todas as sessões; a migração `0004` amplia a finalidade dos tokens; as rotas novas entram no limite por IP das rotas de autenticação.

No stack local, o e2e completo passou (37 testes, com o fluxo de redefinição pelo Mailpit e o seletor de questão).

## Sprint 23 — Listas 5 e 6, recursão obrigatória e registro do gerenciamento

A Sprint 23 (S23-01 a S23-03) foi concluída em 06/10/2026, com estas decisões de implementação: a partir da Lista 5, vários nomes no alvo do `for` valem quando o `for` percorre `zip()` (R-64, com qualquer número de sequências), `enumerate()` (R-63) ou `.items()` sem argumentos (R-65), e nos outros casos a violação sai com o ID da R-63 e uma mensagem que cita as três construções; `derived:recursion` passou a fato estrutural, porque o `def` e a chamada já são decididos pela R-59 (assim, uma função recursiva antes da Lista 4 aparece como o `def`, e não como "recursão"); a recursão por `lambda` não comprova a R-68, porque só funções com `def` entram no grafo; a dict comprehension não comprova o assunto da Lista 5 e continua na R-04 (Q-02 e); com as seis listas habilitadas, os testes do `LIST_NOT_ENABLED` desabilitam a Lista 6 nas próprias configurações; o registro de gerenciamento é lido pelo desenvolvedor e pelos professores (como a REC-06 propôs), mostra até 500 ações dos últimos 12 meses, e o expurgo roda a cada ação e a cada leitura, sem tarefa agendada; o prazo de 12 meses é contado pelo relógio do banco, então a API não consegue apagar um registro recente. Entraram três casos a observar no mapeamento: argumentos nomeados em `dict()`, `update()` e `enumerate()` (Q-02 c), vários nomes no `for` sobre pares quaisquer na L5 e na L6, e a recursão por `lambda`. A revisão de fim de sprint achou e corrigiu duas falhas do motor: o iterável do primeiro `for` de uma compreensão, os valores padrão e os decoradores passaram a ser resolvidos no escopo de fora, como no Python (antes, `[v for map in [map(s)] for v in map]` escondia o built-in `map`, ameaça 8); e um parâmetro ou variável local com o nome da função (`def f(f): return f(1)`) deixou de contar como recursão. O corpus golden tem 292 casos (eram 241), com 4 casos novos de evasão.

## Sprint 22 — Listas 3 e 4

A Sprint 22 (S22-01 e S22-02) foi concluída em 02/10/2026, com estas decisões de implementação: a R-39 (matrizes) casa o mesmo `node:List` da R-38, porque matriz é lista de listas, e por isso as mensagens antes da L3 citam a R-38; a R-40 casa toda tupla, inclusive a atribuição múltipla, e com isso `a, b = 1, 2` antes da L3 passa de R-04 a "Fora da lista" pela R-40, sem mudar a decisão da Q-02 (d); o `in` da R-44 é o mesmo fato das R-30 e R-36; `call:user` (a chamada de uma função do aluno) entra na R-59, e por isso os casos de evasão em que o aluno guarda um built-in num nome e o chama passaram de R-04 a "Fora da lista" (R-59); parâmetro com valor padrão e função aninhada continuam na R-04 (Q-02 f), a segunda pelo fato novo `derived:nested_function` (métodos de classe não contam, pois a classe já é R-09); a recursão é permitida na L4 como chamada de função (a exigência dela é só da L6, R-68). Os casos em aberto do mapeamento (`if __name__`, `f(x=1)`, `for a, b in pares`, `f"{x!r}"`, `zip` em compreensão) seguiram sem decisão e ficaram do lado mais restritivo; entrou um novo: uma lista que só vem de `split()` não comprova o assunto da L3 pela Q-05. O corpus golden tem 241 casos (eram 158).

## Sprint 21 — Telemetria anônima e alertas de latência e erro

A Sprint 21 (S21-01 e S21-02) foi concluída em 02/10/2026, com estas decisões de implementação: o período do evento é o do ruleset (`2026.2.1` dá `2026.2`), porque a identidade da questão é (período, questão) (P-07); as recusas antes da análise usam a última versão do ruleset vista, lida do manifesto quando a API sobe, e só contam nas listas habilitadas; o tempo de análise é medido na API, em volta da chamada ao analisador; o expurgo é uma função `SECURITY DEFINER` chamada pela API, no lugar do `pg_cron` (5.2.4); os alertas de latência e de erro saem de `/health/slo` com o UptimeRobot, sem Grafana (C8), e não alertam com menos de 20 requisições na janela; os contadores da telemetria aparecem no mesmo endereço; o aviso de privacidade ganhou a seção "Estatísticas de uso". No stack local, o e2e gerou 19 eventos, as views responderam como a coordenação as consultaria, e o exercício de falha virou o `/health/slo` para 503 e de volta para 200. Ficam com o autor o terceiro monitor do UptimeRobot e o exercício no piloto (`deploy/README.md`, "Telemetria e alertas").

## Sprint 20 — Lista 2 (zip condicional e exigência do laço) e gabaritos

A Sprint 20 (S20-01 e S20-02) foi concluída em 02/10/2026, com estas decisões de implementação: só o comando `for` conta como "comando for" da R-37, e o `zip()` de uma compreensão cai na R-37 (caso a observar no mapeamento, antes da Sprint 22); o `zip()` dentro de outra chamada no cabeçalho, ou com um nome que guarda o `zip` (`z = zip`), não vale; a falha da condição usa a categoria `NAO_CONSTA` com o ID e a mensagem da R-37, como a da R-33; o `target:for_unpack` só é permitido pela R-37, então a R-64 precisa casá-lo também na Sprint 23, senão `for a, b in zip(x, y)` cairia na R-04 nas Listas 5 e 6; os casos golden antigos da Lista 2 sem laço passaram a esperar a R-02; os testes que usavam a Lista 2 como "não habilitada" passaram a usar a Lista 3. O corpus golden tem 158 casos (eram 145). Os gabaritos reais ainda não rodam: o repositório privado e o token são do autor (`rulesets/README.md`, seção "Gabaritos").

## Sprint 19 — Feedback na página e liberação para a equipe

A Sprint 19 (S19-01 e S19-02) foi concluída em 02/10/2026: o painel "Feedback para o aluno" aparece sob o resultado e gera o texto sobre o código que foi verificado, mesmo que o editor mude depois; o nome do aluno e a anotação continuam no painel entre verificações, e um texto gerado para uma verificação anterior some quando chega uma nova; com erro de sintaxe, o painel explica que não há feedback; a página diz se o texto foi escrito com IA ou montado sem IA e pede revisão antes de copiar; o e2e gera o feedback com o provedor falso nos três tratamentos, num projeto do Playwright à parte, porque troca o tratamento da conta; o aviso de privacidade (Q-19 d) fica em `/privacidade`, aberto sem login e ligado no rodapé, com um resumo nos dois registros; o guia da equipe (`docs/guia-da-equipe.md`) substitui o guia do piloto; a apresentação do Marco 2 foi revista para o uso pela equipe, com cinco decisões (uso pela equipe com os quatro casos de interpretação, Q-16, Q-17, custeio e Q-15 com a REC-05); com só a equipe usando, o pico esperado fica abaixo do que o plano gratuito atende, e o Starter passa a ser reserva, a confirmar na S28-01. Ficam com o autor a configuração das contas externas (`deploy/README.md`), o primeiro deploy com login, que confirma a P-15, a revisão do guia e a data da apresentação.

## Sprint 18 — Feedback por IA (principal e reserva) e montagem determinística

A Sprint 18 (S18-01 e S18-02) foi concluída em 02/10/2026: a abertura segue os exemplos da especificação ("seu código estava muito bom" ou "seu código precisa de ajustes", com vírgula depois da apresentação neutra) e a frase obrigatória lista as construções pelos nomes do `display.py`, com a falta de R-02 como "a falta de if ou operador ternário" (proposta da Q-18 b); o analisador devolve o resultado com os nomes legíveis e o código sem comentários (`POST /internal/feedback-input`); o nome do aluno vira `[ALUNO]` inteiro e em partes, e o nome e o cargo de quem avalia não vão ao provedor; o trecho livre é recusado se fala de anulação ou violação, contradiz o motor, repete a abertura, traz link ou usa palavra com marcação de gênero fora do tratamento; a pedido do autor, há IA principal e de reserva e, sem nenhuma, o feedback montado por modelos (ADR-06, item 6), e a resposta diz de onde veio o texto (`source` e `provider`); cada conta tem até 60 feedbacks por dia e o servidor até 1.000; com erro de sintaxe não há feedback (proposta da Q-18 c).

## Sprint 17 — Painel de plágio

A Sprint 17 (S17-01 a S17-03) foi concluída em 02/10/2026: o motor segue a ADR-05 com a calibração do item 6, e o corpus de pares (`backend/tests/similarity/pares.yaml`) cobre nomes trocados (100%), espaços e comentários (100%), textos de strings trocados (100%), funções e blocos reordenados (100%), soluções independentes (abaixo de 80%) e exercícios diferentes; dois códigos de 50 KB são comparados em cerca de 0,2 s; as recusas de limite dizem qual código (A ou B) foi recusado; a API classifica pelo valor exibido, com uma casa decimal, e avisa quando o menor dos códigos tem menos de 60 tokens normalizados (ameaça 20); o plágio divide com a verificação o limite de 30 por minuto da conta e as vagas de análise; o item 22 da seção 8 roda pela borda, com cada entrada maliciosa em cada um dos dois códigos; a numeração de linhas do editor passou a ter contraste AA, que o axe cobrou no painel.

## Sprint 16 — Google, mesma origem e segurança da autenticação

A Sprint 16 (S16-01 a S16-03) foi concluída em 02/10/2026: o Google usa o Authlib (PKCE) e a joserfc, a implementação JOSE do Authlib, para validar o ID token pelo JWKS do Google (RS256, emissor, audiência, validade, `nonce` e `azp`), com as chaves em cache por até 1 hora e recarregadas quando aparece um `kid` desconhecido; o `state` fica num cookie `__Host-` e vale uma vez, por até 10 minutos, e os fluxos e cadastros em andamento ficam só na memória da instância única (ADR-03); o `hd` vai como `*` (contas de organizações), só como dica; um e-mail verificado é ligado à conta Google na primeira entrada, e outra conta Google com o mesmo e-mail é recusada (`outra_conta`); as recusas voltam à página como códigos em `/entrar?google=...`, sem dados pessoais; `GET /api/v1/auth/options` diz se o Google está configurado, e o botão só aparece nesse caso; no piloto, o build da Vercel lê `IPC_API_ORIGIN` só para o *rewrite*, a CSP fica com `connect-src 'self'`, e o pipeline aplica as migrações antes de cada deploy e confere login, verificação e saída pela origem da página com uma conta de verificação; a suíte de segurança da autenticação (itens 16 a 20 da seção 8) roda pela borda do compose, com um cliente por teste, e as recusas do Google ficam nos testes com o provedor OIDC falso.

## Sprint 15 — Cargos, aprovação e gerenciamento

A Sprint 15 (S15-01 a S15-03) foi concluída em 02/10/2026: a política é uma função pura testada pela matriz completa (4 cargos × 5 ações × 5 cargos-alvo × 7 status × 5 cargos pedidos); cada ação é aplicada por uma transição condicional no banco, e quem age depois de outra pessoa recebe 409 em vez de sobrescrevê-la; as ações respondem 204, e as listas trazem, para cada conta, as ações e os cargos que quem consulta pode usar e o status que a remoção daria; a resposta da conta traz `can_manage`, que mostra o link Gerenciar; as contas `inativo` (professores removidos) aparecem na mesma lista dos ex-monitores e conselheiros, para poderem ser reativadas; pela letra do FR-27 ("quem tem permissão sobre o cargo que ela vai receber"), um monitor-chefe pode reativar um professor removido como monitor ou monitor-chefe, nunca como professor; a remoção e a recusa pedem confirmação na tela; a tela passa no axe sem violações graves.

## Sprint 14 — Registro por e-mail, verificação e perfil

A Sprint 14 (S14-01 a S14-03) foi concluída em 02/10/2026, com estas decisões de implementação: o nome não pode conter `@`, para o login por nome nunca se confundir com o login por e-mail; registrar de novo um e-mail ainda não confirmado substitui os dados pendentes e invalida o link anterior; o reenvio do link responde sempre 202, sem revelar se a conta existe, e envia no máximo 1 por minuto e 5 por dia por conta; a confirmação é um `POST` feito pelo botão da página `/verificar`; a resposta da conta traz `has_password`, para o perfil pedir a senha atual só a quem tem senha; cinco senhas atuais erradas em 15 minutos bloqueiam novas tentativas de troca até a janela de 15 minutos liberar (429 `RATE_LIMITED`); o rodapé traz os créditos do autor, com GitHub e LinkedIn.

## Sprint 13 — Contas, sessão e login por senha

A Sprint 13 (S13-01 a S13-03) foi concluída em 02/10/2026; o limite por conta ficou em 30 por minuto (P-11 h), e os testes do banco rodam contra um PostgreSQL de verdade na CI.

## Sprint 12 — Liberação do piloto (Marco 2)

Concluída em 01/10/2026. O detalhe está nas tasks da sprint no blueprint (seção 7).

## Sprint 11 — Deploy do piloto (Render + Vercel) com isolamento por processo

Concluída em 01/10/2026. O detalhe está nas tasks da sprint no blueprint (seção 7).

## Sprint 10 — Limite de taxa, admissão e mensagens de espera

Concluída em 01/10/2026. O detalhe está nas tasks da sprint no blueprint (seção 7).

## Sprint 1 — Monorepo, CI e carregador do ruleset (R-03 a R-36)

Concluída em 01/10/2026. O detalhe está nas tasks da sprint no blueprint (seção 7).
