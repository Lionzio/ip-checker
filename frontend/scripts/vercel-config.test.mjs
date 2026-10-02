// @vitest-environment node
import { describe, expect, it } from "vitest";
import { HSTS, buildOutputConfig, contentSecurityPolicy, parseApiOrigin } from "./vercel-config.mjs";

const API = "https://ip-checker-api.onrender.com";

describe("parseApiOrigin", () => {
  it.each([
    [API, API],
    [`${API}/`, API],
    ["https://IP-Checker-API.onrender.com", API],
    ["https://api.example:8443", "https://api.example:8443"],
  ])("aceita %s", (value, origin) => {
    expect(parseApiOrigin(value)).toBe(origin);
  });

  it.each([
    undefined,
    "",
    "ip-checker-api.onrender.com",
    "http://ip-checker-api.onrender.com",
    `${API}/api/v1`,
    `${API}?x=1`,
    "https://user@ip-checker-api.onrender.com",
  ])("recusa %s, e o build falha", (value) => {
    expect(() => parseApiOrigin(value)).toThrow(/IPC_API_ORIGIN inválida/);
  });
});

describe("contentSecurityPolicy", () => {
  it("só deixa a página falar com ela mesma: a API chega pelo rewrite (S16-02)", () => {
    const csp = contentSecurityPolicy();

    expect(csp).toContain("connect-src 'self';");
    expect(csp).not.toContain(API);
    expect(csp).toContain("script-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).not.toContain("unsafe-inline");
    expect(csp).not.toContain("unsafe-eval");
    expect(csp).not.toContain("*");
  });
});

describe("buildOutputConfig", () => {
  const config = buildOutputConfig({ apiOrigin: API });
  const securityRoute = config.routes[0];

  it("usa a versão 3 da Build Output API", () => {
    expect(config.version).toBe(3);
  });

  it("manda os cabeçalhos de segurança em todas as respostas", () => {
    expect(securityRoute).toMatchObject({ src: "/(.*)", continue: true });
    expect(securityRoute.headers).toEqual({
      "Content-Security-Policy": contentSecurityPolicy(),
      "Strict-Transport-Security": HSTS,
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
      "Cross-Origin-Opener-Policy": "same-origin",
    });
  });

  it("serve os arquivos e devolve o index.html nos demais caminhos", () => {
    const handle = config.routes.findIndex((route) => route.handle === "filesystem");

    expect(handle).toBeGreaterThan(0);
    expect(config.routes.at(-1)).toEqual({ src: "/(.*)", dest: "/index.html" });
    // Antes dos arquivos, só cabeçalhos (que seguem adiante) e o rewrite da API, que termina ali.
    const before = config.routes.slice(0, handle).filter((route) => route.src !== "/api/(.*)");
    expect(before.every((route) => route.continue)).toBe(true);
  });

  it("não guarda em cache o arquivo de versão", () => {
    expect(config.routes).toContainEqual({
      src: "/version.json",
      headers: { "Cache-Control": "no-store" },
      continue: true,
    });
  });

  it("repassa /api/* ao Render antes de servir os arquivos (mesma origem, S16-02)", () => {
    const rewrite = config.routes.findIndex((route) => route.src === "/api/(.*)");
    const handle = config.routes.findIndex((route) => route.handle === "filesystem");

    expect(config.routes[rewrite]).toEqual({ src: "/api/(.*)", dest: `${API}/api/$1` });
    expect(rewrite).toBeLessThan(handle);
  });
});
