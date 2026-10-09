"""Configuração do serviço do analisador, lida de variáveis de ambiente ``IPC_*``."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ipc_analyzer.runtime.limits import MIB, ResourceLimits
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.runtime.sandbox import SandboxMode

#: Raiz ``rulesets/`` do repositório, usada quando ``IPC_RULESET_PATH`` não é definida
#: (desenvolvimento). ``IPC_RULESET_PATH`` aceita a raiz (vale o período do arquivo ``ATIVO``,
#: S31-09), a pasta de um período ou o ``base.yaml`` dela.
_REPOSITORY_RULESETS = Path(__file__).resolve().parents[4] / "rulesets"


@dataclass(frozen=True, slots=True)
class AnalyzerSettings:
    ruleset_path: Path
    pool: PoolConfig
    #: Logs JSON no stdout (S9-01). Ligado por padrão; desligar só para depurar localmente.
    json_logs: bool = True

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AnalyzerSettings:
        env = os.environ if environ is None else environ
        defaults = PoolConfig()
        return cls(
            ruleset_path=Path(env.get("IPC_RULESET_PATH", str(_REPOSITORY_RULESETS))),
            pool=PoolConfig(
                workers=int(env.get("IPC_WORKERS", defaults.workers)),
                max_tasks=int(env.get("IPC_MAX_TASKS", defaults.max_tasks)),
                timeout_s=float(env.get("IPC_TIMEOUT_S", defaults.timeout_s)),
                limits=ResourceLimits(
                    memory_bytes=int(env.get("IPC_MEMORY_MB", defaults.limits.memory_bytes // MIB))
                    * MIB,
                ),
                sandbox=SandboxMode(env.get("IPC_SANDBOX", defaults.sandbox)),
            ),
            json_logs=env.get("IPC_JSON_LOGS", "1") != "0",
        )
