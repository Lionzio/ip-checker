import { describe, expect, it } from "vitest";
import { ApiError } from "./client";
import { createMockClient } from "./mockClient";

const client = createMockClient({ latencyMs: 0 });
const request = (code: string, list_number = 1) => ({ code, list_number, question_id: null });

describe("cliente simulado", () => {
  it("lista só a Lista 1 no MVP", async () => {
    await expect(client.listLists()).resolves.toEqual([{ number: 1, title: "Comandos condicionais" }]);
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
      expect.objectContaining({ rule_id: "R-34", category: "FORA_DA_LISTA", line: 2, col: 3, end_col: 6 }),
    ]);
  });

  it("marca try e import como anulação", async () => {
    const response = await client.validate(request("import math\ntry:\n    x = 1\n"));

    expect(response.violations.map((v) => [v.rule_id, v.category])).toEqual([
      ["R-05", "ANULACAO"],
      ["R-06", "ANULACAO"],
    ]);
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

  it("recusa lista ainda não habilitada", async () => {
    await expect(client.validate(request("x = 1", 2))).rejects.toMatchObject({
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
});
