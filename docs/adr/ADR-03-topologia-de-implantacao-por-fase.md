# ADR-03 — Topologia de implantação por fase

**Por que está entre as três mais críticas:** é nas vésperas de prazo que os alunos mais precisam da ferramenta, e a hospedagem define latência, disponibilidade, custo e quanto do isolamento do ADR-01 pode ser aplicado.

**Título:** Implantação em três fases: Docker Compose local, Vercel + Render no piloto de 2027.1 e Docker Compose no servidor do CIn.

**Status:** Aceito em 01/10/2026 (Q-10). A Fase 2 depende dos critérios de eficácia (P-09) e dos requisitos em Q-12, adiada para depois do piloto. O plano do Render foi revisto na S28-01 (07/10/2026), com login: ver "Medição da S28-01" no fim. Medido no Render de verdade na S30-09 (08/10/2026) e decidido pelo autor na S30-11: fica no **plano gratuito** (ver "Medição da S30-09 e decisão do plano" no fim).

**Contexto:** O projeto tem um único desenvolvedor com 4 a 8 h por semana (P-02, Q-13) e pouco orçamento. O servidor do CIn só será usado depois de comprovada a eficácia (P-03). O pico de referência é de 500 req/min (P-01), com P95 ≤ 200 ms. O `analyzer` precisa ficar separado de dados e credenciais (ADR-01). O rate limit em memória só é consistente com uma única instância da `api`, o que vale em todas as fases.

**Decisão:**
- **Fase 0 (desenvolvimento, até fevereiro de 2027):** Docker Compose local com `caddy`, `api` e `analyzer`, redes `edge_net` e `analyzer_net` (`internal: true`), sem custo.
- **Fase 1 (piloto em 2027.1):** SPA estática na Vercel (plano Hobby) e backend em 1 serviço Docker no Render, com dois processos sob `supervisord`. A `api` roda com UID 10001 e é a única com a credencial da telemetria. O `analyzer` roda com UID 10002, ambiente vazio, escuta só em `127.0.0.1` e seus workers aplicam seccomp sem sockets de rede nem `execve`. O CORS aceita só a origem da SPA, e o deploy é disparado por *deploy hook* depois que a CI passa.
- **Plano do Render:** começa no gratuito, que dorme após 15 min sem tráfego. Para evitar o cold start, o UptimeRobot acessa `/ready` a cada 5 min, o que mantém o serviço acordado e ainda mede a disponibilidade. Um serviço acordado o mês inteiro usa até 744 h, dentro das 750 h/mês do plano gratuito; por isso não pode haver um segundo serviço gratuito sempre ativo. O gratuito tem só 0,1 CPU: se o teste de carga da Sprint 12 ou o P95 numa véspera de prazo passar de 200 ms, o backend migra para o Starter (cerca de US$ 7 por mês, 0,5 CPU). **Medido na S12-02** (emulação local dos dois planos, `deploy/load/`): a 500 verificações por minuto, o gratuito teve P95 de 3 a 5 s e 13% a 42% de recusas `OVERLOADED`, sem nenhum erro genérico; o Starter teve P95 de 40 ms e nenhuma falha. O gratuito atende cerca de 150 verificações por minuto (P95 de 213 ms). Recomendação: Starter antes do primeiro prazo da Lista 1, a confirmar no Render de verdade. **Desde a P-13 (02/10/2026)**, só a equipe usa a ferramenta, e o pico esperado fica bem abaixo das 150 verificações por minuto que o gratuito atende: o piloto começa no gratuito, com o Starter de reserva, e a S28-01 mede de novo, com login. Com 512 MB, o analisador usa 2 workers de até 160 MB (calibrado na S11-01).
- **Fase 2 (servidor do CIn, após o piloto):** o mesmo Compose da Fase 0, com Caddy e redes segregadas; deploy *pull-based*, porque o acesso externo ao CIn exige VPN (Q-12).

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida para as Fases 0 e 2: Docker Compose numa máquina própria | Isolamento de rede declarativo e testável (NFR-07), sem cold start, ambiente reproduzível (NFR-20) | Exige administrar o sistema operacional, o que no piloto pesaria sobre um único desenvolvedor com 4 a 8 h por semana |
| B. Escolhida para a Fase 1: Vercel + Render (decisão do projeto, Q-10) | Custo baixo, TLS e deploy gerenciados, nenhum servidor para administrar | Sem rede interna nem flags de contêiner, então o isolamento passa a ser por processo (UID, ambiente vazio, seccomp). Exige CORS. No plano gratuito, a dormência é contornada pelo UptimeRobot, mas a CPU continua limitada (0,1 CPU) |
| C. Cloud Run com `min-instances=1` e sandbox gVisor | Isolamento gVisor gerenciado e escala automática | Conta e faturamento GCP, IAM e VPC complexos para um único desenvolvedor, custo variável |

**Consequências positivas:** o piloto começa em 2027.1 sem servidor próprio para administrar. A migração para o CIn reaproveita as imagens e o Compose da Fase 0.

**Consequências negativas:** na Fase 1, o isolamento é mais fraco que nas Fases 0 e 2 (risco residual em 5.4, ameaças 2, 6 e 12) e depende de o Render permitir seccomp. No plano gratuito, 0,1 CPU pode não atender o NFR-01 no pico (gatilho para migrar ao Starter), e o keep-alive depende de os termos do plano gratuito do Render continuarem permitindo pings de monitoramento, o que precisa ser confirmado. Reinícios e deploys ainda causam alguns segundos de indisponibilidade. O plano Hobby da Vercel é para uso não comercial, o que precisa ser confirmado para o projeto. Há um único ponto de falha em todas as fases, e um DDoS distribuído excede a capacidade (REC-01).

## Medição da S28-01 (07/10/2026): carga com login

O `deploy/load/run_load.py` passou a subir um PostgreSQL, aplicar as migrações e entrar com uma
conta antes de verificar: cada verificação agora passa pela sessão no banco, como no piloto.
Emulação local dos planos com `--cpus` e `--memory` do Docker, 3 minutos por rodada, soluções reais
da Lista 1 (até 5 KB):

| Plano | Taxa | Falhas | P50 | P95 | P99 | Observação |
|---|---|---|---|---|---|---|
| Gratuito (0,1 CPU) | 500/min | 14,8% (503 `OVERLOADED`) | 118 ms | 1.895 ms | 3.833 ms | Degrada como o NFR-05 pede, sem 500/502/504 |
| Gratuito (0,1 CPU) | 150/min | 0% | 12 ms | 493 ms | 1.344 ms | Na S12-02, sem login, o P95 foi 213 ms |
| Gratuito (0,1 CPU) | 60/min | 0% | 10 ms | 405 ms | 697 ms | |
| Gratuito (0,1 CPU) | 30/min | 0% | 12 ms | 383 ms | 484 ms | |
| Starter (0,5 CPU) | 500/min | 0% | 7 ms | 28 ms | 54 ms | Sessão no banco (`/auth/me`): P95 3 ms |

**Leitura:** com login, o plano gratuito não atende o P95 ≤ 200 ms do NFR-01 nem com pouco tráfego.
A mediana fica em cerca de 10 ms, mas 0,1 CPU é uma cota de 10 ms a cada 100 ms: qualquer rajada
(a verificação, a consulta da sessão, a gravação da telemetria) esgota a cota e espera o próximo
período, e é essa espera que aparece no P95. O Starter atende o pico de referência (500/min) com
folga. A distância até o banco (Q-20) não entra nesta emulação, porque o banco fica na mesma
máquina; ela é medida no Render de verdade pelo workflow "Carga no piloto" (`load.yml`), que
compara `/auth/me` (sessão no banco) com `/auth/options` (sem banco) pela página da Vercel e traz o
P95 do servidor (`/health/slo`).

**Recomendação (S28-01):** passar o backend para o **Starter** (cerca de US$ 7 por mês) antes do
primeiro prazo da Lista 1 em 2027.1, e não só no pico, como a S12-02 recomendava. Até lá, o piloto
pode seguir no gratuito para a configuração e os testes da equipe, sabendo que o `/health/slo`
vai acusar latência acima de 200 ms. A decisão de custo é do autor; o workflow "Carga no piloto",
rodado depois da conta de verificação, confirma ou desmente a emulação no Render de verdade.

## Medição da S30-09 e decisão do plano (08/10/2026)

O workflow "Carga no piloto" (`load.yml`) rodou no Render de verdade, plano gratuito, com login
pela conta de verificação e pela página da Vercel. O k6 mede do GitHub até a Vercel e o Render, com
a rede no meio; o P95 do servidor vem do `/health/slo`, consultado a cada 30 s durante a carga.

| Rodada | Taxa | Duração | Falhas | k6: P50 / P95 / P99 | Servidor: P95 | `/auth/me` P95 | `/auth/options` P95 |
|---|---|---|---|---|---|---|---|
| 1 | 20/min | 5 min | 0% (101 respostas 200) | 135 / 282 / 380 ms | 127 a 195 ms | 155 ms | 159 ms |
| 2 | 20/min | 10 min | 0% (201 respostas 200) | 96 / 272 / 366 ms | 181 a 195 ms | 118 ms | 104 ms |

**Leitura:** no Render de verdade, a 20 por minuto, o P95 do servidor ficou abaixo dos 200 ms do
NFR-01, melhor que a emulação da S28-01 (383 ms a 30 por minuto): o `--cpus 0.1` local é mais
pessimista que a cota do Render. A sessão no banco soma cerca de 10 ms (Q-20). O pico de 500 por
minuto não foi medido no piloto; na emulação, o gratuito degrada como o NFR-05 pede (14,8% de
`OVERLOADED`, sem 500/502/504).

**Decisão (S30-11, autor, 08/10/2026):** o backend fica no **plano gratuito**; não há orçamento
para o Starter. Consequências: o NFR-01 vale para o uso medido (até cerca de 20 por minuto); no pico
de referência (500 por minuto), o piloto recusa parte das verificações com `OVERLOADED` e uma
mensagem de tentar de novo, em vez de cair (NFR-05). A S34-03 mede os cenários do NFR-04 e do NFR-05
no piloto, e o `/health/slo` com o UptimeRobot avisa quando a latência passar da meta. A S34-01 deixa
de aplicar o Starter e passa a registrar o comportamento no pico com o plano gratuito.

