"""Configuração do serviço do analisador, lida de variáveis de ambiente ``IPC_*``."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ipc_analyzer.runtime.limits import MIB, ResourceLimits
from ipc_analyzer.runtime.pool import PoolConfig

#: Ruleset do repositório, usado quando ``IPC_RULESET_PATH`` não é definida (desenvolvimento).
_REPOSITORY_RULESET = Path(__file__).resolve().parents[4] / "rulesets" / "2026.2" / "base.yaml"


@dataclass(frozen=True, slots=True)
class AnalyzerSettings:
    ruleset_path: Path
    pool: PoolConfig

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AnalyzerSettings:
        env = os.environ if environ is None else environ
        defaults = PoolConfig()
        return cls(
            ruleset_path=Path(env.get("IPC_RULESET_PATH", str(_REPOSITORY_RULESET))),
            pool=PoolConfig(
                workers=int(env.get("IPC_WORKERS", defaults.workers)),
                max_tasks=int(env.get("IPC_MAX_TASKS", defaults.max_tasks)),
                timeout_s=float(env.get("IPC_TIMEOUT_S", defaults.timeout_s)),
                limits=ResourceLimits(
                    memory_bytes=int(env.get("IPC_MEMORY_MB", defaults.limits.memory_bytes // MIB))
                    * MIB,
                ),
            ),
        )
