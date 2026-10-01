"""O que a borda faria no piloto (S11-02, NFR-10): CORS restrito e cabeçalhos de segurança.

Nas Fases 0 e 2 o Caddy serve a página e a API na mesma origem: não há CORS. No piloto (Fase 1)
a página está na Vercel e a API no Render, em origens diferentes, e a borda do Render não
acrescenta cabeçalhos. Por isso a própria API:

- aceita chamadas do navegador só da origem da página (``IPC_CORS_ORIGINS``), sem cookies, e
  deixa a página ler ``Retry-After`` e ``X-Request-Id``;
- manda ``X-Content-Type-Options: nosniff`` sempre e, com ``IPC_HSTS=1``, o HSTS.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

#: Um ano, como o ``max-age`` mínimo exigido para a lista de pré-carga dos navegadores.
HSTS_VALUE = "max-age=31536000; includeSubDomains"
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1"})


def parse_origins(value: str) -> tuple[str, ...]:
    """Converte ``"https://a.vercel.app, http://localhost:5180"`` em origens; recusa o resto.

    Uma origem é esquema, host e porta, sem caminho nem curinga. Fora de ``localhost``, só
    HTTPS: uma página servida em HTTP poderia ser adulterada no caminho até o aluno.
    """
    origins: list[str] = []
    for item in value.split(","):
        text = item.strip().rstrip("/")
        if not text:
            continue
        parts = urlsplit(text)
        host = parts.hostname or ""
        valid = (
            parts.scheme in {"https", "http"}
            and bool(host)
            and "*" not in text
            and not parts.path
            and not parts.query
            and not parts.fragment
            and not parts.username
            and (parts.scheme == "https" or host in _LOCAL_HOSTS)
        )
        if not valid:
            raise ValueError(
                f"IPC_CORS_ORIGINS inválida: {item.strip()!r}. Use origens como "
                "https://ip-checker.vercel.app, sem caminho nem curinga (HTTP só em localhost)."
            )
        origins.append(f"{parts.scheme}://{parts.netloc.lower()}")
    return tuple(dict.fromkeys(origins))


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                if self.hsts:
                    headers["Strict-Transport-Security"] = HSTS_VALUE
            await send(message)

        await self.app(scope, receive, send_with_headers)
