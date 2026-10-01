"""Logs JSON do analyzer (S9-01, NFR-11): uma linha por análise, sem código e sem IP.

A saída passa por uma lista de permissão: só os campos de ``LOG_FIELDS`` são escritos, e de
qualquer outro campo sobra apenas o nome, em ``dropped_fields``. Assim, um descuido como
``log.info("x", code=...)`` nunca grava o código do aluno. Exceções viram só o nome do tipo, sem
traceback nem mensagem, porque a mensagem de uma exceção pode carregar dados da entrada.

A API tem um módulo gêmeo (``ipc_api/logging.py``); os dois serviços não se importam, e o teste
de contrato confere que as listas de campos são iguais.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

SERVICE = "analyzer"

#: Esquema do log. Nenhum campo pode guardar código, IP, cabeçalhos ou corpo de requisição.
LOG_FIELDS = frozenset(
    {
        "timestamp",
        "level",
        "logger",
        "event",
        "service",
        "request_id",
        "method",
        "path",
        "status",
        "latency_ms",
        "payload_bytes",
        "list_number",
        "ruleset_version",
        "outcome",
        "violations",
        # Qual limite recusou a requisição: "client", "ip" ou "capacity". Nunca o IP.
        "rate_limit",
        "error_type",
        "dropped_fields",
    }
)

#: Loggers do uvicorn. O de acesso grava o IP do cliente e por isso fica desligado: a linha de
#: cada análise é escrita pelo próprio analyzer, sem IP.
_UVICORN = ("uvicorn", "uvicorn.error", "uvicorn.access")


def _exception_type_only(_logger: WrappedLogger, _method: str, event: EventDict) -> EventDict:
    exc_info = event.pop("exc_info", None)
    event.pop("exception", None)
    if exc_info:
        error = sys.exc_info()[1] if exc_info is True else exc_info
        if isinstance(error, tuple):
            error = error[1]
        if isinstance(error, BaseException):
            event["error_type"] = type(error).__name__
    return event


def keep_allowed_fields(
    _logger: WrappedLogger, _method: str, event: EventDict
) -> MutableMapping[str, Any]:
    """Descarta todo campo fora de ``LOG_FIELDS``; do descartado, fica só o nome."""
    dropped = sorted(name for name in event if name not in LOG_FIELDS)
    clean = {name: value for name, value in event.items() if name in LOG_FIELDS}
    if dropped:
        clean["dropped_fields"] = dropped
    return clean


def _add_service(_logger: WrappedLogger, _method: str, event: EventDict) -> EventDict:
    event.setdefault("service", SERVICE)
    return event


_SHARED: list[Processor] = [
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    _add_service,
    _exception_type_only,
]


class _StdoutHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Escreve no ``sys.stdout`` do momento, não no que existia quando o handler foi criado."""

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stdout
        super().emit(record)


def json_formatter() -> logging.Formatter:
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            keep_allowed_fields,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )


def configure_logging() -> None:
    """Uma única saída JSON no stdout para o analyzer, o structlog e o uvicorn (idempotente)."""
    structlog.configure(
        processors=[*_SHARED, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, "ipc_json", False)]:
        root.removeHandler(handler)
    handler = _StdoutHandler()
    handler.ipc_json = True  # type: ignore[attr-defined]
    handler.setFormatter(json_formatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    for name in _UVICORN:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
    # O httpx2 registra cada URL chamada em INFO; URL nunca vai para o log.
    logging.getLogger("httpx2").setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    """Logger structlog já marcado com o serviço, mesmo que outro serviço rode no mesmo processo.

    Os valores iniciais mantêm o logger preguiçoso: um ``bind()`` aqui, na importação, congelaria
    o structlog na configuração padrão, que escreve direto no stdout sem passar pelo filtro.
    """
    return structlog.stdlib.get_logger(name, service=SERVICE)
