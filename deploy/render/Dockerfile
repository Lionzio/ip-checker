# syntax=docker/dockerfile:1
#
# Imagem do piloto no Render (Fase 1, 2027.1; S11-01, ADR-03): a API e o analisador no mesmo
# contêiner, sob o supervisord, cada um com o próprio usuário. O contexto é a raiz do repositório:
#
#     docker build -f deploy/render/Dockerfile -t ip-checker-pilot .
#
# Nas Fases 0 e 2 cada serviço tem o próprio contêiner (backend/Dockerfile e deploy/compose.yaml).

# As mesmas imagens fixadas por digest do backend/Dockerfile.
ARG PYTHON_IMAGE=python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.21

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS build

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src

# Dependências de produção mais o grupo "pilot" (supervisor), travadas com hash no uv.lock.
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group pilot --no-install-project

COPY backend/src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group pilot --no-editable

FROM ${PYTHON_IMAGE} AS runtime

# O runtime não instala nada: sem o pip da imagem base (e as bibliotecas que ele embute, que o
# Trivy aponta), nem o pacote do ensurepip (S31-03).
RUN rm -rf /usr/local/lib/python3.13/site-packages/pip \
    /usr/local/lib/python3.13/site-packages/pip-*.dist-info \
    /usr/local/lib/python3.13/ensurepip/_bundled /usr/local/bin/pip /usr/local/bin/pip3*

# Um usuário sem login para cada processo: o analisador (10002) não lê o ambiente da API (10001).
RUN groupadd --system --gid 10001 ipc-api \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent \
       --shell /usr/sbin/nologin ipc-api \
    && groupadd --system --gid 10002 ipc-analyzer \
    && useradd --system --uid 10002 --gid 10002 --no-create-home --home-dir /nonexistent \
       --shell /usr/sbin/nologin ipc-analyzer

COPY --from=build /opt/venv /opt/venv
COPY rulesets /opt/ip-checker/rulesets
# Migrações do banco de contas (S13-01): aplicadas antes do deploy, com a credencial de admin.
COPY database/migrations /opt/ip-checker/database/migrations
COPY deploy/render/supervisord.conf /etc/ipc/supervisord.conf
# Lançador de cada serviço (S30-10): troca de usuário e desligamento sem CAP_KILL.
COPY deploy/render/run_as.py /etc/ipc/run_as.py

# PORT é a porta pública que o Render informa (10000 é o padrão dele).
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    IPC_MIGRATIONS_DIR=/opt/ip-checker/database/migrations \
    PORT=10000

WORKDIR /opt/ip-checker
EXPOSE 10000

# O Render usa o healthCheckPath do render.yaml; este healthcheck serve aos testes locais.
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:%s/ready' % os.environ['PORT'], timeout=3).status != 200)"]

# Único processo como root: só inicia a API e o analisador, cada um com o seu usuário.
CMD ["supervisord", "-c", "/etc/ipc/supervisord.conf"]
