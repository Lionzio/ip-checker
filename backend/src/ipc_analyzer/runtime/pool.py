"""Pool isolado de workers (ADR-01, S5-01).

Cada análise roda num processo filho do pool, nunca no processo que recebe a requisição:

- o worker nasce por ``forkserver`` (Linux) ou ``spawn`` (Windows), sem herdar sockets nem estado do
  processo principal, carrega o ruleset e então aplica os limites de recursos (``limits.py``);
- cada tarefa tem tempo de parede máximo; ao estourar, o Pebble mata o worker e cria outro;
- o worker é reciclado a cada ``max_tasks`` tarefas, para limitar vazamentos de memória;
- timeout, falta de memória e morte do worker viram ``AnalysisLimitError`` (422), nunca erro 5xx.
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
from collections.abc import Callable
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pebble import ProcessExpired, ProcessPool

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.guards import AnalysisLimitError
from ipc_analyzer.engine.models import AnalysisResult
from ipc_analyzer.engine.ruleset import CompiledRuleset, load_ruleset
from ipc_analyzer.runtime.limits import ResourceLimits, apply_limits
from ipc_analyzer.runtime.sandbox import SandboxMode, enforce

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PoolConfig:
    workers: int = 2
    #: Tarefas por worker antes de ele ser substituído por um novo.
    max_tasks: int = 500
    #: Tempo de parede máximo de uma análise, em segundos.
    timeout_s: float = 2.0
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    #: Filtro seccomp do worker (S11-01). As imagens usam REQUIRED.
    sandbox: SandboxMode = SandboxMode.OPTIONAL


# ---------------------------------------------------------------------------
# Código que roda dentro do worker.
# ---------------------------------------------------------------------------

_RULESET: CompiledRuleset | None = None


def _init_worker(ruleset_path: str, limits: ResourceLimits, sandbox: SandboxMode) -> None:
    """Carrega o ruleset e só então se fecha: limites de recursos e, por fim, o seccomp.

    A ordem importa: depois dos limites, abrir arquivos falha; depois do seccomp, criar
    sockets e executar programas falha. Com ``SandboxMode.REQUIRED``, um sistema que não
    permite o filtro impede o worker de nascer, e o serviço não fica pronto.
    """
    global _RULESET
    _RULESET = load_ruleset(Path(ruleset_path))
    if not apply_limits(limits):
        logger.warning("limites de recursos indisponíveis neste sistema; use Linux em produção")
    if not enforce(sandbox) and sandbox is SandboxMode.OPTIONAL:
        logger.warning("filtro seccomp indisponível neste sistema; use Linux em produção")


def _analyze_in_worker(source: str, list_number: int) -> AnalysisResult:
    if _RULESET is None:
        raise RuntimeError("worker sem ruleset carregado")
    return analyze_source(source, list_number=list_number, ruleset=_RULESET)


# ---------------------------------------------------------------------------
# Lado do processo principal.
# ---------------------------------------------------------------------------


def _start_method() -> str:
    return "forkserver" if "forkserver" in multiprocessing.get_all_start_methods() else "spawn"


class AnalyzerPool:
    def __init__(self, ruleset_path: Path, config: PoolConfig | None = None) -> None:
        self.config = config or PoolConfig()
        self._pool = ProcessPool(
            max_workers=self.config.workers,
            max_tasks=self.config.max_tasks,
            initializer=_init_worker,
            initargs=(str(ruleset_path), self.config.limits, self.config.sandbox),
            # O Pebble anota o contexto como módulo, mas aceita um contexto de multiprocessing.
            context=multiprocessing.get_context(_start_method()),  # type: ignore[arg-type]
        )

    @property
    def active(self) -> bool:
        return bool(self._pool.active)

    async def run[T](self, function: Callable[..., T], *args: Any) -> T:
        """Executa ``function(*args)`` num worker, com tempo limite e tradução de falhas."""
        future = self._pool.schedule(function, args=args, timeout=self.config.timeout_s)
        try:
            return await asyncio.wrap_future(future)
        except FuturesTimeoutError:
            logger.warning("análise excedeu %.1f s; worker substituído", self.config.timeout_s)
            raise AnalysisLimitError(
                f"A análise excedeu o tempo limite de {self.config.timeout_s:g} s."
            ) from None
        except MemoryError:
            logger.warning("análise excedeu o limite de memória do worker")
            raise AnalysisLimitError("O código exige memória demais para ser analisado.") from None
        except ProcessExpired as exc:
            logger.warning("worker encerrado durante a análise (código %s)", exc.exitcode)
            raise AnalysisLimitError(
                "A análise foi interrompida e não pôde ser concluída."
            ) from None

    async def analyze(self, source: str, list_number: int) -> AnalysisResult:
        return await self.run(_analyze_in_worker, source, list_number)

    def close(self) -> None:
        self._pool.close()  # type: ignore[no-untyped-call]
        self._pool.join(timeout=10)
        if self._pool.active:
            self._pool.stop()  # type: ignore[no-untyped-call]
            self._pool.join()
