# ADR-15 — Integração com o Dikastis por uma extensão do navegador

**Título:** Como o IP-Checker recebe as listas, as questões e os códigos do Dikastis sem depender da equipe nem do código do Dikastis.

**Status:** Aceito em 16/10/2026 (Sprint 50), depois de proposto no mesmo dia ([`plano-dikastis.md`](../plano-dikastis.md)) e aprovado pelo autor, com a autorização dos professores e dos monitores-chefes; Sprints 50, 52 e 54. **Na implementação (Sprint 50):** a extensão fica em `extensao/`, com o ID fixo `hbndgmplpohgfbmdemopbbibfocbkdhh` (o `key` do manifesto é só a chave pública, e o mesmo ID é o padrão de `IPC_IMPORT_EXTENSION_IDS`, sem nada no `render.yaml`); a API do Dikastis foi descoberta pelo JavaScript público, sem login (formatos em `extensao/docs/api-dikastis.md`); a extensão usa só quatro endereços (organização, turma, tarefa e problema) e pede só `storage` e os dois domínios (os `alarms` e as `notifications` ficam para a Sprint 54); o token do Dikastis é lido só no script da página; a origem da extensão vale só em `/api/v1/import/*`. Como o Dikastis não diz quando um problema mudou, uma verificação sem novidade lê cada questão uma vez (uma por questão, não uma por tarefa): cerca de 50 pedidos, 25 s, para as 28 questões de 2026.2. Revisa a ADR-09 (integração com outros projetos): o Dikastis passa a ser uma fonte de dados, lida pelo navegador de quem já tem acesso.

**Contexto:** Os enunciados das questões, os gabaritos da conta IP CC UFPE e os códigos dos alunos vivem no Dikastis, que é mantido por outra equipe, não tem exportação na interface e cujo repositório o autor não acessa. A página do Dikastis é um aplicativo que busca tudo numa API JSON no próprio domínio, com um token de sessão guardado pelo próprio site. Copiar à mão 28 enunciados por período é inviável a longo prazo, e os códigos de 240 alunos por lista não cabem em nenhum fluxo manual. O IP-Checker precisa dos enunciados para as referências de IA (Sprint 42), dos gabaritos para a comparação (ADR-11) e dos códigos para o plágio em escala (ADR-18).

**Decisão:**
1. **Uma extensão do navegador** (Manifest V3, no repositório, em `extensao/`), instalada pelo modo de desenvolvedor por quem já tem acesso ao Dikastis, roda na aba do Dikastis em que a pessoa está logada e lê, com a sessão dela, a mesma API que a página usa. Nenhuma senha passa pela extensão; o token do Dikastis nunca sai do domínio do Dikastis.
2. **Só leitura, em ritmo baixo e só o que mudou:** até 2 pedidos por segundo (NFR-33); um manifesto com hashes vai ao IP-Checker, que responde só o que falta; nenhuma escrita no Dikastis.
3. **O servidor do IP-Checker nunca fala com o Dikastis:** não há conta de serviço, senha nem token do Dikastis no Render. A extensão envia ao IP-Checker pelas rotas `/api/v1/import/*`, com um **token de importação** pessoal (criado no Perfil pela chefia ou pelo desenvolvedor, mostrado uma vez, guardado como hash, 90 dias, revogável) e com a origem `chrome-extension://<id>` conferida.
4. **Um adaptador único** conhece a API do Dikastis, confere o formato de cada resposta e para com uma mensagem clara, sem gravar meio resultado, se o formato mudar (NFR-34). Uma mudança na API é uma versão nova da extensão, sem tocar no servidor.
5. **Três modos de sincronização:** manual ("Verificar agora"), semi-automático (selo de novidades ao abrir o Dikastis) e automático (alarme a cada 6 horas, uma pessoa por vez), com o histórico de cada rodada em `import_runs`.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida: extensão do navegador | Usa a sessão de quem já tem acesso, sem senha; nenhuma dependência da equipe do Dikastis; a parte dos códigos não toca o disco do monitor | API não documentada, que pode mudar; instalação manual em cada máquina |
| B. Script com navegador automatizado (Playwright) | Roda pela linha de comando | Precisa de um perfil logado ou da senha; os códigos viram arquivos no disco |
| C. Cópia manual | Nenhum código novo | 28 cópias por período; inviável para os códigos |
| D. Exportação oficial pelos mantenedores do Dikastis | O caminho mais estável | Depende de outra equipe e do tempo dela; sem acesso ao repositório |
| E. O servidor chama o Dikastis | Nada a instalar | Credenciais de monitor no servidor; o IP-Checker passaria a puxar dados pessoais sozinho. Descartada |

**Consequências positivas:** os enunciados, os gabaritos e os códigos chegam sem cópia manual; a dependência do Dikastis fica isolada num módulo e numa extensão versionada; o servidor continua sem nenhuma credencial do Dikastis.

**Consequências negativas:** a extensão precisa ser instalada e atualizada à mão em cada máquina; a API do Dikastis pode mudar sem aviso (o adaptador para, e a correção é uma versão nova); o modo automático depende de um navegador aberto e logado.
