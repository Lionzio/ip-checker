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
// Variáveis: BASE_URL (endereço da página ou da API), LOGIN e PASSWORD (conta ativa), RATE
// (verificações por minuto), DURATION (ex.: 3m), ORIGIN (o Origin das requisições que mudam
// estado; padrão: a origem do BASE_URL) e SUMMARY (arquivo do resumo em JSON, opcional).
import http from "k6/http";
import { check, fail } from "k6";
import { Counter, Trend } from "k6/metrics";

const BASE_URL = (__ENV.BASE_URL || "http://127.0.0.1:10000").replace(/\/+$/, "");
const ORIGIN = __ENV.ORIGIN || BASE_URL.match(/^https?:\/\/[^/]+/)[0];
const RATE = Number(__ENV.RATE || 500);
const DURATION = __ENV.DURATION || "3m";
const COOKIES = ["__Host-ipc_session", "ipc_session"];

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

export const options = {
  scenarios: {
    vespera: {
      executor: "constant-arrival-rate",
      rate: RATE,
      timeUnit: "1m",
      duration: DURATION,
      preAllocatedVUs: Math.min(20, Math.max(2, Math.ceil(RATE / 30))),
      maxVUs: 400,
    },
  },
  thresholds: {
    // NFR-01: P95 <= 200 ms e P99 <= 500 ms, só nas verificações com sucesso.
    "http_req_duration{nome:verificar,expected_response:true}": ["p(95)<=200", "p(99)<=500"],
    // NFR-04: nenhuma resposta 5xx e menos de 0,1% de falhas.
    "http_req_failed{nome:verificar}": ["rate<0.001"],
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"],
};

// Um contador por status: o k6 não separa um contador por etiqueta no resumo.
const STATUSES = ["200", "401", "422", "429", "503"];
const byStatus = Object.fromEntries(
  [...STATUSES, "outro"].map((status) => [status, new Counter(`status_${status}`)]),
);
const sessionOnly = new Trend("sessao_ms", true);
const noDatabase = new Trend("sem_banco_ms", true);

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

export default function (session) {
  const headers = { "Content-Type": "application/json", Origin: ORIGIN, Cookie: session.cookie };
  const code = SOLUTIONS[Math.floor(Math.random() * SOLUTIONS.length)];
  const response = http.post(`${BASE_URL}/api/v1/validate`, JSON.stringify({ code, list_number: 1 }), {
    headers,
    timeout: "15s",
    responseCallback: http.expectedStatuses(200),
    tags: { nome: "verificar" },
  });
  byStatus[STATUSES.includes(String(response.status)) ? String(response.status) : "outro"].add(1);
  check(response, {
    "200": (r) => r.status === 200,
    "relatório válido": (r) => r.status !== 200 || ["valid", "invalid"].includes(r.json("status")),
  });
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
  return [
    `Verificações: ${RATE}/min por ${DURATION} em ${BASE_URL}`,
    `  P50 ${ms(validate.med)} · P95 ${ms(validate["p(95)"])} · P99 ${ms(validate["p(99)"])} · máx. ${ms(validate.max)}`,
    `  falhas: ${((failed.rate ?? 0) * 100).toFixed(2)}% · por status: ${statuses.join(", ") || "nenhuma"}`,
    `Só a sessão no banco (/auth/me): P50 ${ms(session.med)} · P95 ${ms(session["p(95)"])}`,
    `Sem banco (/auth/options): P50 ${ms(baseline.med)} · P95 ${ms(baseline["p(95)"])}`,
    "",
  ].join("\n");
}
