# Casos de teste das regras Python de ip-checker.yml (semgrep --test). Nunca é importado nem
# executado: só o Semgrep lê este arquivo. "ruleid" marca o que precisa ser achado e "ok", o que
# não pode.
# ruff: noqa
import os
import pickle
import ssl
import subprocess
import tempfile

import httpx
import yaml
from fastapi import Request


async def handler(request: Request, cursor, name: str) -> None:
    body = (await request.body()).decode()
    # ruleid: python-eval-exec
    eval(body)
    # ruleid: python-eval-exec
    exec(body)
    # ruleid: python-eval-exec
    compile(body, "<aluno>", "exec")
    # ok: python-eval-exec
    import ast

    ast.parse(body)

    # ruleid: python-shell-command
    subprocess.run(f"echo {name}", shell=True)
    # ruleid: python-shell-command
    os.system("ls " + name)
    # ok: python-shell-command
    subprocess.run(["echo", name], check=True)

    # ruleid: python-unsafe-deserialization
    pickle.loads(body.encode())
    # ruleid: python-unsafe-deserialization
    yaml.load(body, Loader=yaml.Loader)
    # ok: python-unsafe-deserialization
    yaml.safe_load(body)

    # ruleid: python-sql-built-from-strings
    cursor.execute(f"SELECT * FROM accounts WHERE email = '{name}'")
    # ruleid: python-sql-built-from-strings
    cursor.execute("SELECT * FROM accounts WHERE email = '%s'" % name)
    # ok: python-sql-built-from-strings
    cursor.execute("SELECT * FROM accounts WHERE email = %s", (name,))

    # ruleid: python-tls-verification-disabled
    httpx.get("https://exemplo.invalid", verify=False)
    # ruleid: python-tls-verification-disabled
    ssl._create_unverified_context()
    # ok: python-tls-verification-disabled
    httpx.get("https://exemplo.invalid")

    # ruleid: python-insecure-temp-file
    tempfile.mktemp()
    # ok: python-insecure-temp-file
    tempfile.mkstemp()
