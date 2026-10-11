// Teste de carga do piloto, já com login (S12-02, refeito na S28-01; NFR-01, NFR-04, NFR-05).
//
// Entra uma vez com uma conta ativa (setup) e faz verificações de soluções reais da Lista 1 a uma
// taxa fixa, com o cookie da sessão, como a página faz. Cada verificação passa pelo middleware da
// sessão, que consulta o banco: a latência medida já inclui a distância até o banco (Q-20).
//
// Dois usos:
//
//   - capacidade, com o deploy/load/run_load.py, que sobe a imagem do piloto com a CPU e a memória
//     de um plano do Render e um banco local, e aumenta os limites por conta e por IP só ali;
//   - o piloto de verdade, pelo workflow "Carga no piloto" (.github/workflows/load.yml), com a
//     conta de verificação e uma taxa abaixo do limite de 30 verificações por minuto da conta.
//
// Cenários (SCENARIO; S34-03), só no run_load.py:
//
//   - vespera (padrão): taxa fixa, de um IP;
//   - nfr04: taxa fixa com 80% das verificações vindas de 4 IPs do campus (o NAT do CIn, P-04) e o
//     resto de IPs externos, cada uma com o seu X-Forwarded-For (a API confia em 1 proxy só ali);
//   - nfr05: a mesma mistura, acima da capacidade, seguida de 90 s a 20 por minuto para medir a
//     recuperação (o último erro depois do fim da sobrecarga).
//
// Variáveis: BASE_URL (endereço da página ou da API), LOGIN e PASSWORD (conta ativa), RATE
// (verificações por minuto), DURATION (ex.: 3m), ORIGIN (o Origin das requisições que mudam
// estado; padrão: a origem do BASE_URL), SCENARIO e SUMMARY (arquivo do resumo em JSON, opcional).
import http from "k6/http";
import exec from "k6/execution";
import { check, fail } from "k6";
import { Counter, Trend } from "k6/metrics";

const BASE_URL = (__ENV.BASE_URL || "http://127.0.0.1:10000").replace(/\/+$/, "");
const ORIGIN = __ENV.ORIGIN || BASE_URL.match(/^https?:\/\/[^/]+/)[0];
const RATE = Number(__ENV.RATE || 500);
const DURATION = __ENV.DURATION || "3m";
const COOKIES = ["__Host-ipc_session", "ipc_session"];
const SCENARIO = __ENV.SCENARIO || "vespera";
if (!["vespera", "nfr04", "nfr05"].includes(SCENARIO)) {
  throw new Error(`SCENARIO desconhecido: ${SCENARIO}`);
}
const MIXED_IPS = SCENARIO !== "vespera";
const RECOVERY = SCENARIO === "nfr05";
// O NAT do campus (P-04): 4 IPs públicos da UFPE, dentro de IPC_RATE_LIMIT_CAMPUS_CIDRS.
const CAMPUS_IPS = ["150.161.2.10", "150.161.2.11", "150.161.2.12", "150.161.2.13"];

function seconds(text) {
  const match = /^(\d+)([sm])$/.exec(text);
  if (!match) {
    throw new Error(`Use a duração como 90s ou 5m (recebido: ${text}).`);
  }
  return Number(match[1]) * (match[2] === "m" ? 60 : 1);
}

// 80% do campus e 20% de IPs externos, um diferente a cada verificação (192.0.2.0/24 e
// 198.51.100.0/24 são faixas de documentação, que nunca são do campus).
function forwardedFor() {
  if (Math.random() < 0.8) {
    return CAMPUS_IPS[Math.floor(Math.random() * CAMPUS_IPS.length)];
  }
  const net = Math.random() < 0.5 ? "192.0.2" : "198.51.100";
  return `${net}.${1 + Math.floor(Math.random() * 254)}`;
}

// Soluções típicas da Lista 1 (todas com menos de 5 KB, como no NFR-01), com e sem violações.
const SOLUTIONS = [
  "nota = float(input())\nif nota >= 7:\n    print('Aprovado')\nelif nota >= 3:\n    print('Final')\nelse:\n    print('Reprovado')\n",
  "a = int(input())\nb = int(input())\nmaior = a if a > b else b\nprint(maior)\n",
  "x = int(input())\nif x % 2 == 0:\n    print('par')\nelse:\n    print('impar')\n",
  "n = int(input())\nfor i in range(n):\n    print(i)\n",
  "idade = int(input())\nif idade >= 18 and idade < 65:\n    print('adulto')\nelif idade >= 65:\n    print('idoso')\nelse:\n    print('menor')\n",
  "try:\n    x = int(input())\nexcept ValueError:\n    x = 0\nif x > 0:\n    print(x)\n",
  "s = input()\nif s.isnumeric():\n    print(int(s) * 2)\nelse:\n    print(s.upper())\n",
  // Uma solução mais longa, perto de 5 KB.
  Array.from({ length: 60 }, (_, i) => `v${i} = int(input())\nif v${i} > ${i}:\n    print(v${i} - ${i}, end=' ')\n`).join(""),
];

const scenarios = {
  [SCENARIO]: {
    executor: "constant-arrival-rate",
    rate: RATE,
    timeUnit: "1m",
    duration: DURATION,
    preAllocatedVUs: Math.min(20, Math.max(2, Math.ceil(RATE / 30))),
    maxVUs: 400,
  },
};
if (RECOVERY) {
  scenarios.recuperacao = {
    executor: "constant-arrival-rate",
    exec: "recovery",
    rate: 20,
    timeUnit: "1m",
    duration: "90s",
    startTime: DURATION,
    preAllocatedVUs: 2,
    maxVUs: 20,
  };
}

export const options = {
  scenarios,
  thresholds: {
    // NFR-01: P95 <= 200 ms e P99 <= 500 ms, só nas verificações com sucesso.
    "http_req_duration{nome:verificar,expected_response:true}": ["p(95)<=200", "p(99)<=500"],
    // NFR-04: nenhuma resposta 5xx e menos de 0,1% de falhas.
    "http_req_failed{nome:verificar}": ["rate<0.001"],
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"],
};

// Um contador por status: o k6 não separa um contador por etiqueta no resumo.
// "0" é a verificação que não teve resposta (timeout ou conexão perdida).
const STATUSES = ["0", "200", "401", "422", "429", "500", "502", "503", "504"];
const byStatus = Object.fromEntries(
  [...STATUSES, "outro"].map((status) => [status, new Counter(`status_${status}`)]),
);
const sessionOnly = new Trend("sessao_ms", true);
const noDatabase = new Trend("sem_banco_ms", true);
// NFR-05: quanto tempo o 503 leva para chegar e se ele traz o Retry-After.
const refusal = new Trend("recusa_ms", true);
const noRetryAfter = new Counter("recusa_sem_retry_after");
// Segundos entre o fim da sobrecarga e cada erro da fase de recuperação; o máximo é a recuperação.
const lastError = new Trend("recuperacao_erro_s");
const recoveryChecks = new Counter("recuperacao_verificacoes");

export function setup() {
  if (!__ENV.LOGIN || !__ENV.PASSWORD) {
    fail("Defina LOGIN e PASSWORD com uma conta ativa (no piloto, a conta de verificação).");
  }
  const response = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ login: __ENV.LOGIN, password: __ENV.PASSWORD }),
    { headers: { "Content-Type": "application/json", Origin: ORIGIN }, tags: { nome: "entrar" } },
  );
  if (response.status !== 200) {
    fail(`O login falhou com ${response.status}; confira a conta e o endereço.`);
  }
  const name = COOKIES.find((cookie) => response.cookies[cookie]?.length);
  if (name === undefined) {
    fail("O login não devolveu o cookie da sessão.");
  }
  return { cookie: `${name}=${response.cookies[name][0].value}` };
}

function validate(session, tags) {
  const headers = { "Content-Type": "application/json", Origin: ORIGIN, Cookie: session.cookie };
  if (MIXED_IPS) {
    headers["X-Forwarded-For"] = forwardedFor();
  }
  const code = SOLUTIONS[Math.floor(Math.random() * SOLUTIONS.length)];
  const response = http.post(`${BASE_URL}/api/v1/validate`, JSON.stringify({ code, list_number: 1 }), {
    headers,
    timeout: "15s",
    responseCallback: http.expectedStatuses(200),
    tags,
  });
  check(response, {
    "200": (r) => r.status === 200,
    "relatório válido": (r) => r.status !== 200 || ["valid", "invalid"].includes(r.json("status")),
  });
  if (response.status === 503) {
    refusal.add(response.timings.duration);
    if (!response.headers["Retry-After"]) {
      noRetryAfter.add(1);
    }
  }
  return response;
}

export default function (session) {
  const headers = { "Content-Type": "application/json", Origin: ORIGIN, Cookie: session.cookie };
  const response = validate(session, { nome: "verificar" });
  byStatus[STATUSES.includes(String(response.status)) ? String(response.status) : "outro"].add(1);
  if (MIXED_IPS) {
    return;
  }
  // Uma em cada quatro iterações também mede, pelo mesmo caminho, uma rota que consulta só a
  // sessão no banco (/auth/me) e uma que não consulta o banco (/auth/options). A diferença entre
  // as duas é a ida ao banco (Q-20); a diferença para a verificação, o tempo do analisador.
  if (Math.random() < 0.25) {
    const me = http.get(`${BASE_URL}/api/v1/auth/me`, { headers, tags: { nome: "sessao" } });
    if (me.status === 200) {
      sessionOnly.add(me.timings.duration);
    }
    // Um pote de cookies vazio: sem cookie, o middleware não consulta a sessão.
    const options = http.get(`${BASE_URL}/api/v1/auth/options`, {
      jar: new http.CookieJar(),
      tags: { nome: "sem_banco" },
    });
    if (options.status === 200) {
      noDatabase.add(options.timings.duration);
    }
  }
}

export function recovery(session) {
  const response = validate(session, { nome: "recuperacao" });
  recoveryChecks.add(1);
  if (response.status !== 200) {
    lastError.add(exec.instance.currentTestRunDuration / 1000 - seconds(DURATION));
  }
}

export function teardown(session) {
  http.post(`${BASE_URL}/api/v1/auth/logout`, null, {
    headers: { Origin: ORIGIN, Cookie: session.cookie },
    tags: { nome: "sair" },
  });
}

export function handleSummary(data) {
  const out = { stdout: textSummary(data) };
  if (__ENV.SUMMARY) {
    out[__ENV.SUMMARY] = JSON.stringify(data);
  }
  return out;
}

function textSummary(data) {
  const metric = (name) => data.metrics[name]?.values ?? {};
  const ms = (value) => (value === undefined ? "?" : `${Math.round(value)} ms`);
  const validate = metric("http_req_duration{nome:verificar,expected_response:true}");
  const failed = metric("http_req_failed{nome:verificar}");
  const session = metric("sessao_ms");
  const baseline = metric("sem_banco_ms");
  const statuses = [...STATUSES, "outro"]
    .filter((status) => metric(`status_${status}`).count)
    .map((status) => `${status}=${metric(`status_${status}`).count}`);
  const refused = metric("recusa_ms");
  const lines = [
    `Verificações (${SCENARIO}): ${RATE}/min por ${DURATION} em ${BASE_URL}`,
    `  P50 ${ms(validate.med)} · P95 ${ms(validate["p(95)"])} · P99 ${ms(validate["p(99)"])} · máx. ${ms(validate.max)}`,
    `  falhas: ${((failed.rate ?? 0) * 100).toFixed(2)}% · por status: ${statuses.join(", ") || "nenhuma"}`,
  ];
  if (refused.count) {
    lines.push(
      `  503: P50 ${ms(refused.med)} · P95 ${ms(refused["p(95)"])} · máx. ${ms(refused.max)} · ` +
        `sem Retry-After: ${metric("recusa_sem_retry_after").count ?? 0}`,
    );
  }
  if (RECOVERY) {
    const errors = metric("recuperacao_erro_s");
    lines.push(
      `Recuperação: ${metric("recuperacao_verificacoes").count ?? 0} verificações em 90 s; ` +
        (errors.max === undefined ? "nenhum erro" : `último erro ${errors.max.toFixed(1)} s depois da sobrecarga`),
    );
  }
  if (!MIXED_IPS) {
    lines.push(
      `Só a sessão no banco (/auth/me): P50 ${ms(session.med)} · P95 ${ms(session["p(95)"])}`,
      `Sem banco (/auth/options): P50 ${ms(baseline.med)} · P95 ${ms(baseline["p(95)"])}`,
    );
  }
  return [...lines, ""].join("\n");
}
