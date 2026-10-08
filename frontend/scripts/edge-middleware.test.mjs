// @vitest-environment node
import { describe, expect, it } from "vitest";
import { CLIENT_HEADER, SECRET_HEADER, forwardToApi } from "./edge-middleware.mjs";

const SECRET = "s".repeat(64);

function forwarded(response) {
  const names = response.headers.get("x-middleware-override-headers").split(",");
  return Object.fromEntries(
    names.map((name) => [name, response.headers.get(`x-middleware-request-${name}`)]),
  );
}

function request(headers) {
  return new Request("https://ip-checker.vercel.app/api/v1/auth/login", { method: "POST", headers });
}

describe("forwardToApi", () => {
  it("segue para o repasse com o segredo e o IP que a Vercel viu", () => {
    const response = forwardToApi(
      request({ "x-real-ip": "198.51.100.7", cookie: "__Host-ipc_session=abc", origin: "https://x" }),
      SECRET,
    );

    expect(response.headers.get("x-middleware-next")).toBe("1");
    const headers = forwarded(response);
    expect(headers[SECRET_HEADER]).toBe(SECRET);
    expect(headers[CLIENT_HEADER]).toBe("198.51.100.7");
    // Os demais cabeçalhos seguem como vieram: a troca substitui o conjunto inteiro.
    expect(headers.cookie).toBe("__Host-ipc_session=abc");
    expect(headers.origin).toBe("https://x");
  });

  it("descarta o segredo e o IP que o cliente mandou", () => {
    const forged = { [SECRET_HEADER]: "chute", [CLIENT_HEADER]: "203.0.113.9", "x-real-ip": "198.51.100.7" };

    expect(forwarded(forwardToApi(request(forged), SECRET))[CLIENT_HEADER]).toBe("198.51.100.7");
    expect(forwarded(forwardToApi(request(forged), SECRET))[SECRET_HEADER]).toBe(SECRET);
    const off = forwarded(forwardToApi(request(forged), undefined));
    expect(off[SECRET_HEADER]).toBeUndefined();
    expect(off[CLIENT_HEADER]).toBeUndefined();
  });

  it("sem o segredo configurado, só repassa", () => {
    const response = forwardToApi(request({ "x-real-ip": "198.51.100.7" }), undefined);

    expect(response.headers.get("x-middleware-next")).toBe("1");
    expect(forwarded(response)).toEqual({ "x-real-ip": "198.51.100.7" });
  });
});
