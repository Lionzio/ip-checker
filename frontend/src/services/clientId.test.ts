import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

/** Cada teste carrega o módulo de novo, para o identificador em memória começar vazio. */
async function loadGetClientId() {
  vi.resetModules();
  return (await import("./clientId")).getClientId;
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("getClientId", () => {
  it("gera um UUID v4 e o mantém durante a sessão", async () => {
    const getClientId = await loadGetClientId();

    const id = getClientId();

    expect(id).toMatch(UUID_V4);
    expect(getClientId()).toBe(id);
    expect((await loadGetClientId())()).toBe(id); // outra carga da página na mesma aba
  });

  it("guarda o identificador só no sessionStorage", async () => {
    const id = (await loadGetClientId())();

    expect(sessionStorage.getItem("ipc-client-id")).toBe(id);
    expect(localStorage.length).toBe(0);
    expect(document.cookie).toBe("");
  });

  it("gera um identificador novo em outra sessão", async () => {
    const first = (await loadGetClientId())();
    sessionStorage.clear(); // a aba foi fechada

    expect((await loadGetClientId())()).not.toBe(first);
  });

  it("substitui um valor adulterado no sessionStorage", async () => {
    sessionStorage.setItem("ipc-client-id", "<script>alert(1)</script>");

    const id = (await loadGetClientId())();

    expect(id).toMatch(UUID_V4);
    expect(sessionStorage.getItem("ipc-client-id")).toBe(id);
  });

  it("funciona em memória quando o sessionStorage é bloqueado", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    const getClientId = await loadGetClientId();

    const id = getClientId();

    expect(id).toMatch(UUID_V4);
    expect(getClientId()).toBe(id);
  });

  it("gera o UUID sem crypto.randomUUID (página fora de contexto seguro)", async () => {
    const getRandomValues = crypto.getRandomValues.bind(crypto);
    vi.stubGlobal("crypto", { getRandomValues });
    const getClientId = await loadGetClientId();

    const first = getClientId();
    sessionStorage.clear();

    expect(first).toMatch(UUID_V4);
    expect(getClientId()).toMatch(UUID_V4);
    expect(getClientId()).not.toBe(first);
  });
});
