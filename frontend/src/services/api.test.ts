import { afterEach, describe, expect, it, vi } from "vitest";
import type { Account, ValidateResponse } from "../types/api";
import { createApiClient } from "./api";
import { ApiError } from "./client";

const ACCOUNT: Account = {
  name: "Vinícius Leôncio",
  email: "vlacg@cin.ufpe.br",
  course: "Não informado",
  treatment: "masculino",
  role: "desenvolvedor",
  role_label: "Monitor e desenvolvedor",
  has_password: true,
  can_manage: true,
};

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

  it("manda a sessão pelo cookie da mesma origem, sem X-Client-Id (S13-02)", async () => {
    const fetchMock = respond(200, RESPONSE);

    await createApiClient().validate({ code: "x = 1", list_number: 1, question_id: null });

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.credentials).toBe("same-origin");
    expect(init.headers).not.toHaveProperty("X-Client-Id");
  });

  it("pergunta quem está logado", async () => {
    const account = { ...ACCOUNT };
    const fetchMock = respond(200, account);

    await expect(createApiClient().me()).resolves.toEqual(account);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/me");
    expect(init.method).toBe("GET");
  });

  it("devolve 401 quando não há sessão", async () => {
    respond(401, { error: { code: "UNAUTHENTICATED", message: "Entre.", retry_after_s: null } });

    const error = await rejection(createApiClient().me());

    expect(error.status).toBe(401);
    expect(error.code).toBe("UNAUTHENTICATED");
  });

  it("entra com login e senha", async () => {
    const fetchMock = respond(200, ACCOUNT);

    await expect(createApiClient().login("vlacg@cin.ufpe.br", "Senha-forte-1")).resolves.toEqual(ACCOUNT);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/login");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ login: "vlacg@cin.ufpe.br", password: "Senha-forte-1" });
  });

  it("sai com um corpo vazio, que a borda aceita", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response(null, { status: 204 })));
    vi.stubGlobal("fetch", fetchMock);

    await createApiClient().logout();

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/logout");
    expect(init.method).toBe("POST");
    expect(init.body).toBe("");
  });

  it("lê o tempo de espera do limite de taxa", async () => {
    respond(429, {
      error: { code: "RATE_LIMITED", message: "Você fez muitas verificações em pouco tempo.", retry_after_s: 42 },
    });

    const error = await rejection(createApiClient().validate({ code: "x", list_number: 1, question_id: null }));

    expect(error.status).toBe(429);
    expect(error.code).toBe("RATE_LIMITED");
    expect(error.retryAfterS).toBe(42);
  });

  it("usa o cabeçalho Retry-After quando o corpo não traz a espera", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ error: { code: "OVERLOADED", message: "Ocupado.", retry_after_s: null } }), {
            status: 503,
            headers: { "Content-Type": "application/json", "Retry-After": "7" },
          }),
        ),
      ),
    );

    const error = await rejection(createApiClient().listLists());

    expect(error.retryAfterS).toBe(7);
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

  it("pergunta as formas de entrar e cuida do cadastro pelo Google", async () => {
    const fetchMock = respond(200, { google: true });
    await expect(createApiClient().options()).resolves.toEqual({ google: true });
    respond(200, { email: "g@cin.ufpe.br", name: "G" });
    await expect(createApiClient().googlePending()).resolves.toEqual({ email: "g@cin.ufpe.br", name: "G" });
    const complete = respond(201, { status: "aguardando_aprovacao", email: "g@cin.ufpe.br" });
    const request = { name: "G", course: "CC", treatment: "neutro" as const };

    await expect(createApiClient().completeGoogle(request)).resolves.toBe("g@cin.ufpe.br");
    expect((fetchMock.mock.calls[0] as unknown as [string])[0]).toBe("/api/v1/auth/options");
    const [url, init] = complete.mock.calls[0] as unknown as [string, RequestInit];
    expect([url, init.method, JSON.parse(init.body as string)]).toEqual(["/api/v1/auth/google/complete", "POST", request]);
  });

  it("compara dois códigos no painel de plágio", async () => {
    const fetchMock = respond(200, { status: "compared" });

    await createApiClient().compare("a = 1", "b = 2");

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect([url, init.method, JSON.parse(init.body as string)]).toEqual([
      "/api/v1/similarity",
      "POST",
      { code_a: "a = 1", code_b: "b = 2" },
    ]);
  });

  it("lê a fila e os membros do gerenciamento", async () => {
    const fetchMock = respond(200, { items: [] });

    await expect(createApiClient().listRequests()).resolves.toEqual([]);
    respond(200, { active: [], removed: [] });
    await expect(createApiClient().listMembers()).resolves.toEqual({ active: [], removed: [] });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect([url, init.method]).toEqual(["/api/v1/admin/requests", "GET"]);
  });

  it.each([
    ["approve", ["a b", "monitor"], "POST", "/api/v1/admin/requests/a%20b/approve", { role: "monitor" }],
    ["reject", ["id-1"], "POST", "/api/v1/admin/requests/id-1/reject", ""],
    ["changeRole", ["id-1", "professor"], "PATCH", "/api/v1/admin/members/id-1/role", { role: "professor" }],
    ["remove", ["id-1"], "POST", "/api/v1/admin/members/id-1/remove", ""],
    ["reactivate", ["id-1", "monitor_chefe"], "POST", "/api/v1/admin/members/id-1/reactivate", { role: "monitor_chefe" }],
  ] as const)("%s chama a rota do gerenciamento", async (method, args, verb, path, body) => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response(null, { status: 204 })));
    vi.stubGlobal("fetch", fetchMock);
    const client = createApiClient() as unknown as Record<string, (...values: string[]) => Promise<void>>;

    await client[method]?.(...args);

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect([url, init.method]).toEqual([path, verb]);
    // Sem cargo, o corpo vai vazio, mas presente: a borda recusa POST sem Content-Length (S10).
    expect(body === "" ? init.body : JSON.parse(init.body as string)).toEqual(body);
  });

  it("aceita uma URL base", async () => {
    const fetchMock = respond(200, []);

    await createApiClient({ baseUrl: "https://ip-checker.example" }).listLists();

    const [url] = fetchMock.mock.calls[0] as unknown as [string];
    expect(url).toBe("https://ip-checker.example/api/v1/lists");
  });
});
