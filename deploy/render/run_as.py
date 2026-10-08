"""Inicia um serviço do piloto com o próprio usuário e o encerra sem ``CAP_KILL`` (S30-10, P-17).

O Render roda o contêiner sem a capacidade ``CAP_KILL``. Sem ela, um processo root não sinaliza
processos de outro usuário: o ``supervisord`` não conseguia parar a API (UID 10001) nem o
analisador (UID 10002) e registrava ``CRIT unknown problem killing ... PermissionError``. O sinal de
morte do pai (``PR_SET_PDEATHSIG``) também não serve: o kernel o entrega com a mesma checagem de
permissão do ``kill()`` (conferido em 08/10/2026 com ``docker run --cap-drop KILL``).

Por isso, nenhum sinal atravessa usuários. Três processos por serviço:

1. **Lançador** (este programa, root): o que o ``supervisord`` inicia e sinaliza (mesmo usuário).
   Cria um pipe, o "cano de vida", e guarda só a ponta de escrita.
2. **Guardião** (filho do lançador, já com o usuário do serviço): inicia o serviço e espera no cano.
   Quando o lançador recebe o ``SIGTERM`` (fecha o cano) ou morre (o kernel fecha o cano), o
   guardião manda ``SIGTERM`` ao serviço, que é do mesmo usuário, e espera ele sair.
3. **Serviço** (filho do guardião): o comando recebido, com o ambiente do lançador.

Se o serviço sai sozinho, o guardião e o lançador saem com o mesmo código, e o ``supervisord`` o
reinicia. O lançador e o guardião não atendem requisições nem leem entrada.

O ambiente é herdado: para o analisador, o ``env -i`` vem **antes** deste programa no
``supervisord.conf``, para que nenhum processo com o UID do analisador carregue os segredos.

Uso: ``run_as.py <usuário> -- <comando> [argumentos...]``
"""

from __future__ import annotations

import os
import pwd
import signal
import sys
import threading

CAP_KILL = 5
#: Um segundo a menos que o ``stopwaitsecs`` do supervisord, que depois mata o lançador.
STOP_WAIT_S = 14.0
#: O guardião não chegou a iniciar o serviço: usuário ou comando inválidos.
EXIT_SETUP_FAILED = 70


def _cap_kill() -> str:
    try:
        with open("/proc/self/status") as status:
            line = next(item for item in status if item.startswith("CapEff:"))
    except (OSError, StopIteration):
        return "desconhecida"
    return "presente" if int(line.split()[1], 16) >> CAP_KILL & 1 else "ausente"


def _exit_code(status: int) -> int:
    code = os.waitstatus_to_exitcode(status)
    return 128 - code if code < 0 else code  # morto por sinal: 128 + sinal, como no shell


def _guard(uid: int, gid: int, lifeline: int, command: list[str]) -> int:
    """No guardião: troca de usuário, inicia o serviço e o encerra quando o cano fechar."""
    os.setgroups([])
    os.setresgid(gid, gid, gid)
    os.setresuid(uid, uid, uid)
    service = os.fork()
    if service == 0:
        os.close(lifeline)
        try:
            os.execv(command[0], command)  # noqa: S606 - comando fixo do supervisord.conf
        finally:
            os._exit(EXIT_SETUP_FAILED)

    def watch() -> None:
        while os.read(lifeline, 64):
            pass  # ninguém escreve no cano; ler só espera ele fechar
        try:
            os.kill(service, signal.SIGTERM)  # mesmo usuário: não precisa de CAP_KILL
        except ProcessLookupError:
            return

    threading.Thread(target=watch, name="run_as-lifeline", daemon=True).start()
    _, status = os.waitpid(service, 0)
    return _exit_code(status)


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "--":
        print("uso: run_as.py <usuário> -- <comando> [argumentos...]", file=sys.stderr)
        return 2
    user, command = argv[0], argv[2:]
    entry = pwd.getpwnam(user)
    if entry.pw_uid == 0:
        print("run_as: o serviço não pode rodar como root", file=sys.stderr)
        return 2
    print(f"run_as {user}: CAP_KILL {_cap_kill()}", flush=True)

    read_end, write_end = os.pipe()
    guardian = os.fork()
    if guardian == 0:
        os.close(write_end)
        code = EXIT_SETUP_FAILED
        try:
            code = _guard(entry.pw_uid, entry.pw_gid, read_end, command)
        finally:
            os._exit(code)
    os.close(read_end)

    stopping = threading.Event()

    def stop(signum: int, _frame: object) -> None:
        if stopping.is_set():
            return
        stopping.set()
        os.close(write_end)  # o guardião vê o cano fechar e encerra o serviço
        # Se o serviço não sair a tempo, o lançador sai; o supervisord o mataria de qualquer jeito.
        timer = threading.Timer(STOP_WAIT_S, os._exit, args=(128 + signum,))
        timer.daemon = True
        timer.start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    _, status = os.waitpid(guardian, 0)
    return 0 if stopping.is_set() else _exit_code(status)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
