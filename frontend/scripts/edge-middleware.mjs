/**
 * Middleware da Vercel para `/api/*` (S30-03): só a página fala com a API do piloto.
 *
 * O Render é público e acrescenta ao `X-Forwarded-For` sem limpá-lo, e a Vercel não assina o que
 * repassa. Por isso a página manda junto um segredo que só ela e a API conhecem
 * (`IPC_EDGE_SECRET`, cadastrado nos dois painéis) e o IP do cliente que a própria Vercel
 * determinou. A API recusa `/api/*` sem o segredo certo e usa esse IP no limite por IP.
 *
 * Valores com esses nomes vindos do cliente são sempre descartados. Sem o segredo configurado, o
 * middleware só faz isso, e a API, sem o segredo dela, continua como antes: os dois lados podem ser
 * ligados um de cada vez.
 *
 * O build copia este arquivo para `.vercel/output/functions/_middleware.func/index.js` (Build Output
 * API v3, Edge Runtime). Os cabeçalhos `x-middleware-*` são o formato que o `next()` do
 * `@vercel/functions` usa para trocar os cabeçalhos da requisição repassada.
 */

export const SECRET_HEADER = "x-ipc-edge-secret";
export const CLIENT_HEADER = "x-ipc-client-ip";

/**
 * @param {Request} request
 * @param {string | undefined} secret
 * @returns {Response}
 */
export function forwardToApi(request, secret) {
  const headers = new Headers(request.headers);
  headers.delete(SECRET_HEADER);
  headers.delete(CLIENT_HEADER);
  if (secret) {
    headers.set(SECRET_HEADER, secret);
    // O x-real-ip é escrito pela Vercel com o IP de quem se conectou a ela.
    const client = request.headers.get("x-real-ip");
    if (client) headers.set(CLIENT_HEADER, client);
  }
  const instructions = new Headers({ "x-middleware-next": "1" });
  for (const [name, value] of headers) {
    instructions.set(`x-middleware-request-${name}`, value);
  }
  instructions.set("x-middleware-override-headers", [...headers.keys()].join(","));
  return new Response(null, { headers: instructions });
}

/**
 * @param {Request} request
 * @returns {Response}
 */
export default function middleware(request) {
  return forwardToApi(request, globalThis.process?.env?.IPC_EDGE_SECRET);
}
