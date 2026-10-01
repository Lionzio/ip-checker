import { afterEach, describe, expect, it, vi } from "vitest";
import type { ValidateResponse } from "../types/api";
import { createApiClient } from "./api";
import { ApiError } from "./client";

const RESPONSE: ValidateResponse = {
  request_id: "01J9Z0000000000000000000",
  ruleset_version: "2026.2.0",
  status: "valid",
  list_number: 1,
  question_id: null,
  notices: ["QUESTION_RULES_NOT_APPLIED"],
  syntax_error: null,
  violations: [],
  truncated: false,
};

function respond(status: number, body: unknown, contentType = "application/json") {
  const text = typeof body === "string" ? body : JSON.stringify(body);
  const fetchMock = vi.fn(() =>
    Promise.resolve(new Response(text, { status, headers: { "Content-Type": contentType } })),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  const error = await promise.catch((caught: unknown) => caught);
  expect(error).toBeInstanceOf(ApiError);
  return error as ApiError;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("createApiClient", () => {
  it("envia o código para /api/v1/validate na mesma origem", async () => {
    const fetchMock = respond(200, RESPONSE);
    const controller = new AbortController();

    const response = await createApiClient().validate(
      { code: "x = 1", list_number: 1, question_id: null },
      controller.signal,
    );

    expect(response).toEqual(RESPONSE);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/validate");
    expect(init.method).toBe("POST");
    expect(init.signal).toBe(controller.signal);
    expect(init.cache).toBe("no-store");
    expect(JSON.parse(init.body as string)).toEqual({ code: "x = 1", list_number: 1, question_id: null });
  });

  it("busca as listas habilitadas", async () => {
    respond(200, [{ number: 1, title: "Comandos condicionais" }]);

    await expect(createApiClient().listLists()).resolves.toEqual([
      { number: 1, title: "Comandos condicionais" },
    ]);
  });

  it("transforma o envelope de erro do contrato em ApiError", async () => {
    respond(422, {
      error: { code: "LIST_NOT_ENABLED", message: "A Lista 2 ainda não está habilitada.", retry_after_s: null },
    });

    const error = await rejection(createApiClient().validate({ code: "x", list_number: 2, question_id: null }));

    expect(error.status).toBe(422);
    expect(error.code).toBe("LIST_NOT_ENABLED");
    expect(error.message).toBe("A Lista 2 ainda não está habilitada.");
    expect(error.retryAfterS).toBeNull();
  });

  it("guarda a espera sugerida dos erros 503", async () => {
    respond(503, {
      error: { code: "ANALYZER_UNAVAILABLE", message: "Indisponível.", retry_after_s: 30 },
    });

    const error = await rejection(createApiClient().listLists());

    expect(error.code).toBe("ANALYZER_UNAVAILABLE");
    expect(error.retryAfterS).toBe(30);
  });

  it.each([
    [502, "<html>Bad Gateway</html>", "text/html"],
    [500, "", "text/plain"],
    [404, { detail: "Not Found" }, "application/json"],
  ])("trata uma resposta %i fora do contrato como serviço indisponível", async (status, body, type) => {
    respond(status, body, type);

    const error = await rejection(createApiClient().listLists());

    expect(error.code).toBe("ANALYZER_UNAVAILABLE");
    expect(error.status).toBe(status >= 500 ? status : 503);
  });

  it("deixa erros de rede e cancelamento seguirem como estão", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))));

    await expect(createApiClient().listLists()).rejects.toBeInstanceOf(TypeError);
  });

  it("aceita uma URL base", async () => {
    const fetchMock = respond(200, []);

    await createApiClient({ baseUrl: "https://ip-checker.example" }).listLists();

    const [url] = fetchMock.mock.calls[0] as unknown as [string];
    expect(url).toBe("https://ip-checker.example/api/v1/lists");
  });
});
