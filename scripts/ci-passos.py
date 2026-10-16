"""Impressão digital das entradas de cada passo da CI local (S49-01, ADR-20).

Cada passo do ``scripts/ci-local.sh`` declara os caminhos de que depende. Este script calcula um
hash do conteúdo desses caminhos (os arquivos rastreados e os não rastreados mas não ignorados,
pelo ``git ls-files``; o conteúdo pelo ``git hash-object``, o mesmo blob do Git) e guarda, em
``<git-common-dir>/ci-local-passos.json``, o par passo → hash → verde (``sha``, hora). Um passo
cujas entradas não mudaram desde um verde é pulado, e o resumo diz "igual ao verde de <sha>".

Só a biblioteca padrão; roda com o Python da máquina (``python scripts/ci-passos.py``), da raiz do
repositório ou de uma worktree. Nenhum conteúdo de arquivo é impresso: só hashes, nomes e datas.

Comandos::

    hash -- <caminhos>                 imprime o hash das entradas (pathspecs do Git; ../x para
                                       uma pasta fora do repositório, como os gabaritos)
    check <passo> <hash> [--max-age-days N]
                                       sai com 0 e imprime "sha hora" se há verde para o hash
    record <passo> <hash> <sha> [--manifest] -- <caminhos>
                                       grava o verde; com --manifest, guarda o blob de cada arquivo
    changed <passo> -- <caminhos>      imprime os arquivos cujo blob difere do manifesto gravado
                                       (todos, se não há manifesto); "." sozinho = sem mudança
    verify <passo>...                  sai com 0 se cada passo tem verde para as entradas atuais
                                       (recalculadas dos caminhos gravados); imprime o que falta
    forget [<passo>...]                apaga os registros (todos, sem argumentos)
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

RECORD_NAME = "ci-local-passos.json"
MISSING = "ausente"


def git(*args: str, cwd: Path | None = None, input_text: str | None = None) -> str:
    result = subprocess.run(  # noqa: S603 - argumentos fixos deste script
        ["git", *args],  # noqa: S607 - o git do PATH, como o resto da CI
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


def repo_root() -> Path:
    return Path(git("rev-parse", "--show-toplevel").strip())


def record_path() -> Path:
    common = Path(git("rev-parse", "--git-common-dir").strip())
    if not common.is_absolute():
        common = repo_root() / common
    return common / RECORD_NAME


def load_records() -> dict[str, dict[str, object]]:
    path = record_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_records(records: dict[str, dict[str, object]]) -> None:
    path = record_path()
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )


class RecordLock:
    """As faixas da CI gravam verdes ao mesmo tempo (S49-02): uma trava por arquivo, com O_EXCL,
    evita que uma grave por cima da outra. Uma trava esquecida há mais de um minuto é descartada."""

    def __init__(self) -> None:
        self.path = record_path().with_suffix(".lock")
        self.fd = -1

    def __enter__(self) -> RecordLock:
        for _ in range(200):
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > 60:
                        self.path.unlink()
                        continue
                except OSError:
                    pass
                time.sleep(0.05)
        raise RuntimeError(f"ci-passos: o registro está ocupado ({self.path})")

    def __exit__(self, *_: object) -> None:
        os.close(self.fd)
        with contextlib.suppress(OSError):
            self.path.unlink()


def list_files(root: Path, pathspecs: list[str]) -> list[str]:
    """Os arquivos das entradas, relativos à raiz do repositório, em ordem; um caminho fora do
    repositório (``../gabaritos``) é percorrido no disco, sem a pasta ``.git``."""
    inside = [spec for spec in pathspecs if not spec.startswith("../")]
    outside = [spec for spec in pathspecs if spec.startswith("../")]
    files: set[str] = set()
    if inside:
        out = git(
            "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *inside, cwd=root
        )
        files.update(part for part in out.split("\0") if part)
    for spec in outside:
        base = (root / spec).resolve()
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d != ".git")
            for name in sorted(filenames):
                full = Path(dirpath) / name
                files.add(os.path.relpath(full, root).replace(os.sep, "/"))
    return sorted(files)


def blobs(root: Path, files: list[str]) -> dict[str, str]:
    """O blob (como o Git o calcula) de cada arquivo; ``ausente`` para o que não existe mais."""
    present = [f for f in files if (root / f).is_file()]
    result: dict[str, str] = {f: MISSING for f in files if f not in present}
    if present:
        out = git("hash-object", "--stdin-paths", cwd=root, input_text="\n".join(present) + "\n")
        for name, blob in zip(present, out.split(), strict=True):
            result[name] = blob
    return result


def manifest_of(pathspecs: list[str]) -> dict[str, str]:
    root = repo_root()
    return blobs(root, list_files(root, pathspecs))


def hash_of(manifest: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(manifest):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(manifest[name].encode())
        digest.update(b"\n")
    return digest.hexdigest()


def cmd_hash(args: argparse.Namespace) -> int:
    print(hash_of(manifest_of(args.paths)))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    record = load_records().get(args.passo)
    if not record or record.get("hash") != args.hash:
        return 1
    when = str(record.get("quando", ""))
    if args.max_age_days is not None:
        try:
            stamp = datetime.fromisoformat(when)
        except ValueError:
            return 1
        if datetime.now(UTC) - stamp > timedelta(days=args.max_age_days):
            return 1
    print(f"{str(record.get('sha', ''))[:7]} {when[:16].replace('T', ' ')}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    entry: dict[str, object] = {
        "hash": args.hash,
        "sha": args.sha,
        "quando": datetime.now(UTC).isoformat(timespec="minutes"),
        "paths": list(args.paths),
    }
    if args.manifest:
        entry["manifest"] = manifest_of(args.paths)
    with RecordLock():
        records = load_records()
        records[args.passo] = entry
        save_records(records)
    return 0


def cmd_changed(args: argparse.Namespace) -> int:
    current = manifest_of(args.paths)
    record = load_records().get(args.passo) or {}
    stored = record.get("manifest")
    if not isinstance(stored, dict):
        for name in current:
            print(name)
        return 0
    changed = [
        name for name, blob in current.items() if stored.get(name) != blob and blob != MISSING
    ]
    if not changed:
        print(".")
    for name in changed:
        print(name)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    records = load_records()
    missing: list[str] = []
    for passo in args.passos:
        record = records.get(passo)
        paths = record.get("paths") if record else None
        if not record or not isinstance(paths, list):
            missing.append(f"{passo}: sem verde registrado")
            continue
        if hash_of(manifest_of([str(p) for p in paths])) != record.get("hash"):
            green = str(record.get("sha", ""))[:7]
            missing.append(f"{passo}: as entradas mudaram desde o verde de {green}")
    for line in missing:
        print(line)
    return 1 if missing else 0


def cmd_forget(args: argparse.Namespace) -> int:
    with RecordLock():
        records = load_records()
        if not args.passos:
            records = {}
        for passo in args.passos:
            records.pop(passo, None)
        save_records(records)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ci-passos.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("hash")
    p.add_argument("paths", nargs="+")
    p.set_defaults(func=cmd_hash)

    p = sub.add_parser("check")
    p.add_argument("passo")
    p.add_argument("hash")
    p.add_argument("--max-age-days", type=int, default=None)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("record")
    p.add_argument("passo")
    p.add_argument("hash")
    p.add_argument("sha")
    p.add_argument("--manifest", action="store_true")
    p.add_argument("paths", nargs="+")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("changed")
    p.add_argument("passo")
    p.add_argument("paths", nargs="+")
    p.set_defaults(func=cmd_changed)

    p = sub.add_parser("verify")
    p.add_argument("passos", nargs="+")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("forget")
    p.add_argument("passos", nargs="*")
    p.set_defaults(func=cmd_forget)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except subprocess.CalledProcessError as exc:
        print(f"ci-passos: git falhou: {exc.stderr.strip()}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
