"""Filtro seccomp dos workers (S11-01; NFR-07 na Fase 1; ameaças 2 e 6).

No piloto (Render) não há rede interna nem flags de contêiner: o isolamento do worker que roda
o parser passa a ser feito por ele mesmo. Depois de carregar o ruleset e aplicar os limites de
recursos, o worker instala um filtro seccomp que faz estas chamadas falharem com ``EPERM``:

- ``socket`` e ``socketpair``: nenhuma conexão de rede nova, nem para fora nem para o loopback;
- ``execve`` e ``execveat``: nenhum programa executado;
- desde a S25-04, as portas usadas em fugas do kernel e para espiar outros processos:
  ``io_uring_*``, ``ptrace``, ``process_vm_readv``/``process_vm_writev``, ``bpf``,
  ``userfaultfd``, ``unshare`` e ``setns``.

As quatro primeiras são obrigatórias. As demais entram quando a libseccomp do sistema as
conhece; uma libseccomp antiga que não saiba o nome de uma delas não impede o worker de nascer.

O filtro não pode ser removido depois de instalado, nem pelo próprio processo, e vale para
qualquer processo que ele venha a criar. O worker continua usando os pipes que o pool abriu
antes do filtro. Nas Fases 0 e 2 ele soma com o isolamento do contêiner (defesa em profundidade).
"""

from __future__ import annotations

import errno
from enum import StrEnum

#: Chamadas de sistema negadas ao worker; sem uma delas, o filtro não vale.
BLOCKED_SYSCALLS = ("socket", "socketpair", "execve", "execveat")
#: Negadas também, quando a libseccomp do sistema conhece o nome (S25-04).
HARDENING_SYSCALLS = (
    "io_uring_setup",
    "io_uring_enter",
    "io_uring_register",
    "ptrace",
    "process_vm_readv",
    "process_vm_writev",
    "bpf",
    "userfaultfd",
    "unshare",
    "setns",
)


class SandboxMode(StrEnum):
    #: Não instala o filtro (testes que precisam de sockets no worker).
    OFF = "off"
    #: Instala se o sistema permitir; senão, segue com um aviso (desenvolvimento no Windows).
    OPTIONAL = "optional"
    #: Instala ou recusa iniciar o worker: o serviço não fica pronto sem o filtro (imagens).
    REQUIRED = "required"


class SandboxUnavailable(RuntimeError):  # noqa: N818 - é um estado, não um erro de programação
    """O modo exige o filtro, mas o sistema não permitiu instalá-lo."""


def apply_sandbox() -> bool:
    """Instala o filtro no processo atual; devolve ``False`` quando o sistema não permite."""
    try:
        # libseccomp via ctypes: só existe em Linux, e a importação falha sem a biblioteca.
        import pyseccomp as seccomp
    except (ImportError, OSError):
        return False
    try:
        syscall_filter = seccomp.SyscallFilter(defaction=seccomp.ALLOW)
        for name in BLOCKED_SYSCALLS:
            syscall_filter.add_rule(seccomp.ERRNO(errno.EPERM), name)
        for name in HARDENING_SYSCALLS:
            try:
                syscall_filter.add_rule(seccomp.ERRNO(errno.EPERM), name)
            except (OSError, RuntimeError, ValueError):
                continue  # nome desconhecido desta libseccomp: a chamada também não existe aqui
        syscall_filter.load()
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def enforce(mode: SandboxMode) -> bool:
    """Aplica o filtro conforme o modo; devolve se ele está ativo."""
    if mode is SandboxMode.OFF:
        return False
    if apply_sandbox():
        return True
    if mode is SandboxMode.REQUIRED:
        raise SandboxUnavailable(
            "o filtro seccomp do worker é obrigatório (IPC_SANDBOX=required), mas o sistema não "
            "permitiu instalá-lo"
        )
    return False
