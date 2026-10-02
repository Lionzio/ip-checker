"""Senhas (FR-23, NFR-22): política e hash Argon2id.

A política é a mesma no frontend e no backend: pelo menos 9 caracteres, 1 letra maiúscula e 1
caractere especial. O teto de 128 caracteres impede que uma senha enorme vire um ataque de custo
contra o Argon2. O hash e a verificação rodam numa thread, para não travar o laço de eventos.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from starlette.concurrency import run_in_threadpool

MIN_LENGTH = 9
MAX_LENGTH = 128


def password_problems(password: str) -> list[str]:
    """O que falta na senha, em PT-BR; vazio quando ela cumpre a política."""
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"ter pelo menos {MIN_LENGTH} caracteres")
    if len(password) > MAX_LENGTH:
        problems.append(f"ter no máximo {MAX_LENGTH} caracteres")
    if not any(char.isupper() for char in password):
        problems.append("ter pelo menos 1 letra maiúscula")
    if not any(not char.isalnum() and not char.isspace() for char in password):
        problems.append("ter pelo menos 1 caractere especial")
    return problems


class Passwords:
    """Argon2id com os parâmetros mínimos da OWASP: 19 MiB, 2 iterações, paralelismo 1."""

    def __init__(self, *, memory_kib: int = 19 * 1024, iterations: int = 2) -> None:
        self._hasher = PasswordHasher(time_cost=iterations, memory_cost=memory_kib, parallelism=1)
        # Conta inexistente ou sem senha: verifica contra este hash para o tempo de resposta não
        # revelar se a conta existe.
        self._dummy = self._hasher.hash("conta-inexistente")

    def hash_sync(self, password: str) -> str:
        return self._hasher.hash(password)

    async def hash(self, password: str) -> str:
        return await run_in_threadpool(self._hasher.hash, password)

    async def verify(self, password_hash: str | None, password: str) -> bool:
        if len(password) > MAX_LENGTH:
            return False
        return await run_in_threadpool(
            self._verify, password_hash or self._dummy, password, password_hash is not None
        )

    def _verify(self, password_hash: str, password: str, real: bool) -> bool:
        try:
            ok = self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False
        return ok and real
