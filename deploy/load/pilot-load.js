// Teste de carga curto do piloto (S12-02; NFR-01, NFR-04, NFR-05).
//
// "Véspera de prazo": verificações de soluções reais da Lista 1 a uma taxa fixa (padrão: 500 por
// minuto, o pico de referência da P-01), cada uma de um aluno diferente (X-Client-Id próprio).
// Roda com o deploy/load/run_load.py, que sobe a imagem do piloto com os recursos do plano do
// Render, ou direto contra um endereço:
//
//     k6 run -e BASE_URL=https://ip-checker-api.onrender.com deploy/load/pilot-load.js
//
// Variáveis: BASE_URL, RATE (verificações por minuto), DURATION (ex.: 3m).
import http from "k6/http";
import { check } from "k6";
import { Counter, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:10000";
const RATE = Number(__ENV.RATE || 500);
const DURATION = __ENV.DURATION || "3m";

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
      preAllocatedVUs: 20,
      maxVUs: 400,
    },
  },
  thresholds: {
    // NFR-01: P95 <= 200 ms e P99 <= 500 ms, só nas respostas de sucesso.
    "http_req_duration{expected_response:true}": ["p(95)<=200", "p(99)<=500"],
    // NFR-04: nenhuma resposta 5xx e menos de 0,1% de falhas.
    http_req_failed: ["rate<0.001"],
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"],
};

const byStatus = new Counter("respostas_por_status");
const analysisTime = new Trend("tempo_ate_resposta_ms", true);

function uuid() {
  const hex = () => Math.floor(Math.random() * 16).toString(16);
  const pick = (n) => Array.from({ length: n }, hex).join("");
  const variant = "89ab"[Math.floor(Math.random() * 4)];
  return `${pick(8)}-${pick(4)}-4${pick(3)}-${variant}${pick(3)}-${pick(12)}`;
}

export default function () {
  const code = SOLUTIONS[Math.floor(Math.random() * SOLUTIONS.length)];
  const response = http.post(
    `${BASE_URL}/api/v1/validate`,
    JSON.stringify({ code, list_number: 1 }),
    {
      headers: { "Content-Type": "application/json", "X-Client-Id": uuid() },
      timeout: "15s",
      responseCallback: http.expectedStatuses(200),
    },
  );
  byStatus.add(1, { status: String(response.status) });
  analysisTime.add(response.timings.duration);
  check(response, {
    "200": (r) => r.status === 200,
    "relatório válido": (r) => r.status !== 200 || ["valid", "invalid"].includes(r.json("status")),
  });
}
