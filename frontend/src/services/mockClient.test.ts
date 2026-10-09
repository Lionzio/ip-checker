import { describe, expect, it } from "vitest";
import { ApiError } from "./client";
import { createMockClient, DEMO_ACCOUNT } from "./mockClient";

const client = createMockClient({ latencyMs: 0, signedIn: true });
const request = (code: string, list_number = 1) => ({ code, list_number, question_id: null });

describe("cliente simulado", () => {
  it("lista as Listas 1 a 6 (Sprint 23)", async () => {
    await expect(client.listLists()).resolves.toEqual([
      { number: 1, title: "Comandos condicionais" },
      { number: 2, title: "Laços de repetição" },
      { number: 3, title: "Listas e tuplas", questions: [{ id: "L3-Q1", title: "Questão de demonstração" }] },
      { number: 4, title: "Funções e escopo de variável" },
      { number: 5, title: "Dicionários" },
      { number: 6, title: "Recursão" },
    ]);
  });

  it("aplica a questão escolhida e recusa uma questão que não existe (R-01)", async () => {
    const withQuestion = await client.validate({ code: "v = [1]\nprint(v)\n", list_number: 3, question_id: "L3-Q1" });

    // Com a questão, o aviso de regras da questão não aplicadas some (FR-11).
    expect(withQuestion.question_id).toBe("L3-Q1");
    expect(withQuestion.notices).toEqual([]);
    await expect(
      client.validate({ code: "x = 1", list_number: 3, question_id: "L3-Q9" }),
    ).rejects.toMatchObject({ status: 422, code: "UNKNOWN_QUESTION" });
  });

  it("nas Listas 5 e 6, o assunto exigido é um dicionário e a recursão (R-68)", async () => {
    const withDict = await client.validate(request("d = {}\nprint(d)\n", 5));
    const withoutDict = await client.validate(request("v = [1]\nprint(v)\n", 5));
    const recursive = "def f(n):\n    return 0 if n == 0 else f(n - 1)\nprint(f(3))\n";
    const withRecursion = await client.validate(request(recursive, 6));
    const withoutRecursion = await client.validate(request("def f(n):\n    return n\nprint(f(3))\n", 6));

    expect(withDict.status).toBe("valid");
    expect(withoutDict.violations[0]?.message).toContain("assunto da Lista 5");
    expect(withRecursion.status).toBe("valid");
    expect(withoutRecursion.violations.map((v) => [v.rule_id, v.construct])).toEqual([
      ["R-68", "requirement:R-68"],
    ]);
  });

  it("nas Listas 3 e 4, o assunto exigido é uma lista ou tupla e um def", async () => {
    const withList = await client.validate(request("v = [1, 2]\nprint(v)\n", 3));
    const withoutList = await client.validate(request("x = 1\nprint(x)\n", 3));
    const withDef = await client.validate(request("def f():\n    return 1\n", 4));
    const withoutDef = await client.validate(request("v = [1]\nprint(v)\n", 4));

    expect(withList.status).toBe("valid");
    expect(withoutList.violations[0]?.message).toContain("assunto da Lista 3");
    expect(withDef.status).toBe("valid");
    expect(withoutDef.violations[0]?.message).toContain("assunto da Lista 4");
  });

  it("na Lista 2, o for é permitido e o assunto exigido é um laço", async () => {
    const loop = await client.validate(request("for i in range(3):\n    print(i)\n", 2));
    const withoutLoop = await client.validate(request("x = int(input())\nif x > 0:\n    print(x)\n", 2));

    expect(loop.status).toBe("valid");
    expect(withoutLoop.violations.map((v) => v.rule_id)).toEqual(["R-02"]);
    expect(withoutLoop.violations[0]?.message).toContain("assunto da Lista 2");
  });

  it("aceita código sem os padrões simulados", async () => {
    const response = await client.validate(request("x = int(input())\nif x > 0:\n    print(x)\n"));

    expect(response.status).toBe("valid");
    expect(response.violations).toEqual([]);
    expect(response.notices).toEqual(["QUESTION_RULES_NOT_APPLIED"]);
  });

  it("aponta o for na linha e coluna certas", async () => {
    const response = await client.validate(request("x = 3\n  for i in x:\n    print(i)\n"));

    expect(response.status).toBe("invalid");
    expect(response.violations).toEqual([
      expect.objectContaining({ rule_id: "R-02", category: "EXIGENCIA", line: 1, col: 1 }),
      expect.objectContaining({ rule_id: "R-34", category: "FORA_DA_LISTA", line: 2, col: 3, end_col: 6 }),
    ]);
  });

  it("marca try e import como anulação", async () => {
    const response = await client.validate(request("import math\ntry:\n    x = 1\n"));

    expect(response.violations.map((v) => [v.rule_id, v.category])).toEqual([
      ["R-02", "EXIGENCIA"],
      ["R-05", "ANULACAO"],
      ["R-06", "ANULACAO"],
    ]);
  });

  it("simula a exigência da Lista 1 só quando falta o if", async () => {
    const comIf = await client.validate(request("x = 1\nif x:\n    print(x)\n"));
    const soComentario = await client.validate(request("# if x:\nprint(1)\n"));

    expect(comIf.status).toBe("valid");
    expect(soComentario.violations.map((v) => v.rule_id)).toEqual(["R-02"]);
  });

  it("simula erro de sintaxe para parêntese não fechado", async () => {
    const response = await client.validate(request("print('(oi)'\nx = (1 + 2)\n"));

    expect(response.status).toBe("syntax_error");
    expect(response.syntax_error).toEqual({ line: 1, col: 6, message: "o '(' foi aberto e nunca fechado" });
  });

  it.each([
    ["", 422, "INVALID_INPUT"],
    ["#" + "a".repeat(51_200), 413, "PAYLOAD_TOO_LARGE"],
  ])("recusa entrada inválida (%#)", async (code, status, errorCode) => {
    await expect(client.validate(request(code))).rejects.toMatchObject({ status, code: errorCode });
  });

  it("recusa lista que não está habilitada", async () => {
    await expect(client.validate(request("x = 1", 7))).rejects.toMatchObject({
      status: 422,
      code: "LIST_NOT_ENABLED",
    });
  });

  it.each([
    ["sobrecarga", 503, "OVERLOADED", 10],
    ["limite", 429, "RATE_LIMITED", 30],
    ["indisponivel", 503, "ANALYZER_UNAVAILABLE", 60],
  ])("simula o cenário %s", async (scenario, status, code, retryAfterS) => {
    const error = await client.validate(request(`# simular: ${scenario}\nx = 1`)).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status, code, retryAfterS });
  });

  it("simula falha de rede", async () => {
    await expect(client.validate(request("# simular: rede"))).rejects.toBeInstanceOf(TypeError);
  });

  it("respeita o cancelamento", async () => {
    const controller = new AbortController();
    controller.abort();

    await expect(createMockClient().validate(request("x = 1"), controller.signal)).rejects.toMatchObject({
      name: "AbortError",
    });
  });

  it("começa sem sessão e entra com qualquer nome e senha preenchidos", async () => {
    const auth = createMockClient({ latencyMs: 0 });

    await expect(auth.me()).rejects.toMatchObject({ status: 401, code: "UNAUTHENTICATED" });
    await expect(auth.login("", "x")).rejects.toMatchObject({ status: 422 });
    await expect(auth.login("demo", "x")).resolves.toEqual(DEMO_ACCOUNT);
    await expect(auth.me()).resolves.toEqual(DEMO_ACCOUNT);
    await auth.logout();
    await expect(auth.me()).rejects.toMatchObject({ status: 401 });
  });

  it("pode começar com sessão", async () => {
    await expect(createMockClient({ latencyMs: 0, signedIn: true }).me()).resolves.toEqual(DEMO_ACCOUNT);
  });

  it("exige a sessão, como a API (S26-04)", async () => {
    const anonymous = createMockClient({ latencyMs: 0 });
    const unauthenticated = { status: 401, code: "UNAUTHENTICATED" };

    await expect(anonymous.listLists()).rejects.toMatchObject(unauthenticated);
    await expect(anonymous.validate(request("x = 1"))).rejects.toMatchObject(unauthenticated);
    await expect(anonymous.compare("x = 1", "y = 2")).rejects.toMatchObject(unauthenticated);
    await expect(
      anonymous.feedback({
        code: "x = 1",
        list_number: 1,
        question_id: null,
        student_name: "Ana",
        annotation: null,
        enhance: false,
      }),
    ).rejects.toMatchObject(unauthenticated);
  });

  it("simula o relatório cortado, o limite de análise e o texto da IA (S26-04)", async () => {
    const truncated = await client.validate(request("# simular: truncado"));
    expect(truncated.truncated).toBe(true);
    expect(truncated.violations).toHaveLength(200);

    await expect(client.validate(request("# simular: limite_analise"))).rejects.toMatchObject({
      status: 422,
      code: "ANALYSIS_LIMIT",
    });

    const ai = await client.feedback({
      code: "if True:\n    print(1)\n",
      list_number: 1,
      question_id: null,
      student_name: "Ana",
      annotation: null,
      enhance: true,
    });
    expect(ai.source).toBe("llm");
    expect(ai.provider).toBe("gemini");
  });
});
