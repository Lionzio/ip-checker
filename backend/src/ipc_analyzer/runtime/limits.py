"""Limites de recursos aplicados a cada worker no momento em que ele nasce (ADR-01, NFR-08).

Os limites só podem ser reduzidos, nunca aumentados de volta: depois do initializer, nem o código
do próprio worker consegue desfazê-los. O módulo ``resource`` só existe em sistemas Unix; no
Windows (ambiente de desenvolvimento) os limites não são aplicados, e a produção roda em Linux.
"""

from __future__ import annotations

import signal
from dataclasses import dataclass

MIB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    #: Espaço de endereçamento virtual do worker (RLIMIT_AS). Calibrado na S5-01 (P-04): o
    #: worker usa ~50 MB em repouso e ~74 MB no pior caso de 50 KB.
    memory_bytes: int = 256 * MIB
    #: Arquivos abertos ao mesmo tempo (RLIMIT_NOFILE); o worker só usa os pipes do pool.
    max_open_files: int = 32


def apply_limits(limits: ResourceLimits) -> bool:
    """Aplica os limites ao processo atual; devolve ``False`` quando o sistema não os suporta."""
    try:
        import resource  # só existe em Unix
    except ImportError:
        return False
    resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))
    # Tamanho máximo de arquivo 0: o worker não consegue gravar nada em disco.
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits.max_open_files, limits.max_open_files))
    # Sem isto, tentar gravar um arquivo mataria o worker com SIGXFSZ; assim, a gravação falha
    # com erro e o restante do worker continua previsível.
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    return True
