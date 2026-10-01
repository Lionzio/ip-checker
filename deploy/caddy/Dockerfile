# syntax=docker/dockerfile:1
#
# Imagem da borda (S9-02): o build da SPA servido pelo Caddy. O contexto é a raiz do repositório:
#
#     docker build -f deploy/caddy/Dockerfile -t ip-checker-web .

# Imagens fixadas por digest, como as do backend.
# node:24-alpine (Node 24.21.0) e caddy:2-alpine (Caddy 2.11.4), multiarquitetura.
ARG NODE_IMAGE=node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1
ARG CADDY_IMAGE=caddy:2-alpine@sha256:6aeddd44c3078b0f9a35206472a11420648a79c184603ef95957d0a20044cb2b

FROM ${NODE_IMAGE} AS spa

WORKDIR /spa
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM ${CADDY_IMAGE}

COPY deploy/caddy/Caddyfile /etc/caddy/Caddyfile
COPY --from=spa /spa/dist /srv

# A imagem oficial dá ao binário a capability de abrir portas abaixo de 1024. Com cap_drop ALL e
# no-new-privileges, o kernel se recusa a executar um binário assim; como a porta é 8080, ela é
# removida e o Caddy roda sem root e sem nenhuma capability.
RUN setcap -r /usr/bin/caddy
USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
