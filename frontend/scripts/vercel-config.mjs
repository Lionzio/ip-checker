/**
 * Configuração da página no piloto (Vercel, Fase 1; S11-02, NFR-10), no formato da Build Output
 * API v3 (`.vercel/output/config.json`).
 *
 * Os cabeçalhos de segurança dependem do endereço da API no Render (a CSP só deixa a página falar
 * com ele). Por isso são gerados no build, a partir da mesma variável que a página usa
 * (`VITE_API_BASE_URL`): o endereço da API fica num lugar só.
 */

/** Um ano, como na API e na borda do compose. */
export const HSTS = "max-age=31536000; includeSubDomains";

/**
 * Valida o endereço da API e devolve a origem (esquema, host e porta).
 * @param {string | undefined} value
 * @returns {string}
 */
export function parseApiOrigin(value) {
  let url;
  try {
    url = new URL(value ?? "");
  } catch {
    throw new Error(`VITE_API_BASE_URL inválida: ${JSON.stringify(value ?? "")}. Use, por exemplo, https://ip-checker-api.onrender.com`);
  }
  const extra = (url.pathname !== "/" && url.pathname !== "") || url.search || url.hash || url.username;
  if (url.protocol !== "https:" || extra) {
    throw new Error(`VITE_API_BASE_URL inválida: ${JSON.stringify(value)}. Use só a origem HTTPS da API, sem caminho.`);
  }
  return url.origin;
}

/**
 * @param {string} apiOrigin
 * @returns {string}
 */
export function contentSecurityPolicy(apiOrigin) {
  return [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    `connect-src 'self' ${apiOrigin}`,
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "upgrade-insecure-requests",
  ].join("; ");
}

/**
 * @param {{ apiOrigin: string }} options
 */
export function buildOutputConfig({ apiOrigin }) {
  return {
    version: 3,
    routes: [
      {
        src: "/(.*)",
        headers: {
          "Content-Security-Policy": contentSecurityPolicy(apiOrigin),
          "Strict-Transport-Security": HSTS,
          "X-Content-Type-Options": "nosniff",
          "Referrer-Policy": "no-referrer",
          "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
          "Cross-Origin-Opener-Policy": "same-origin",
        },
        continue: true,
      },
      // Arquivos com hash no nome nunca mudam; o resto é revalidado a cada visita.
      {
        src: "/assets/(.*)",
        headers: { "Cache-Control": "public, max-age=31536000, immutable" },
        continue: true,
      },
      { src: "/version.json", headers: { "Cache-Control": "no-store" }, continue: true },
      { handle: "filesystem" },
      // Página única: qualquer outro caminho devolve o index.html.
      { src: "/(.*)", dest: "/index.html" },
    ],
  };
}
