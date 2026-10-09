# syntax=docker/dockerfile:1
#
# Imagem do analyzer (S6-01, ADR-01, NFR-07). O contexto de build é a raiz do repositório, porque a
# imagem embute os rulesets:
#
#     docker build -f backend/Dockerfile -t ip-checker-analyzer .
#
# O endurecimento que depende do runtime (read_only, cap_drop, no-new-privileges, pids_limit,
# mem_limit e rede sem saída) fica em deploy/compose.yaml.

# Imagens fixadas por digest: uma atualização da base é sempre uma mudança revisada neste arquivo.
# python:3.13-slim (Python 3.13.15, Debian), multiarquitetura.
ARG PYTHON_IMAGE=python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.21

FROM ${UV_IMAGE} AS uv

# ---------------------------------------------------------------------------------------------
# Build: instala só as dependências de produção num ambiente virtual, sem as ferramentas de dev.
# ---------------------------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS build

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src

# Primeiro as dependências, que mudam pouco; assim a camada fica em cache entre builds.
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY backend/src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ---------------------------------------------------------------------------------------------
# Runtime: só o interpretador, o ambiente virtual e os rulesets. Sem uv, sem código-fonte do build,
# sem segredos e sem shell de login para o usuário do serviço.
# ---------------------------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime

# O runtime não instala nada: sem o pip da imagem base (e as bibliotecas que ele embute, que o
# Trivy aponta), nem o pacote do ensurepip (S31-03).
RUN rm -rf /usr/local/lib/python3.13/site-packages/pip \
    /usr/local/lib/python3.13/site-packages/pip-*.dist-info \
    /usr/local/lib/python3.13/ensurepip/_bundled /usr/local/bin/pip /usr/local/bin/pip3*

RUN groupadd --system --gid 10001 analyzer \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent \
       --shell /usr/sbin/nologin analyzer

COPY --from=build /opt/venv /opt/venv
COPY rulesets /opt/ip-checker/rulesets
# Migrações do banco de contas (S13-01), aplicadas pelo serviço migrate do compose.
COPY database/migrations /opt/ip-checker/database/migrations

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    IPC_RULESET_PATH=/opt/ip-checker/rulesets

USER 10001:10001
WORKDIR /opt/ip-checker

EXPOSE 8001

# Sem curl na imagem: o próprio Python consulta o health. Um worker preso ou um pool parado
# derrubam o status para unhealthy.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8001/internal/health', timeout=2).status != 200)"]

CMD ["uvicorn", "ipc_analyzer.service.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001", "--no-server-header", "--no-proxy-headers"]
