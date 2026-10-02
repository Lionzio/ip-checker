"""Senhas (S13-02; FR-23 e NFR-22): política e Argon2id."""

from __future__ import annotations

import pytest
from argon2 import PasswordHasher

from api_support import FAST_PASSWORDS
from ipc_api.accounts.passwords import MAX_LENGTH, Passwords, password_problems


@pytest.mark.parametrize(
    "password",
    ["Senha-forte-1", "ABCDEFGH!", "Çãéíóú?Xz", "Maiúscula com espaço!"],
)
def test_passwords_that_follow_the_policy(password: str) -> None:
    assert password_problems(password) == []


@pytest.mark.parametrize(
    ("password", "problem"),
    [
        ("Curta-1!", "ter pelo menos 9 caracteres"),
        ("sem-maiuscula-1", "ter pelo menos 1 letra maiúscula"),
        ("SemEspecial1", "ter pelo menos 1 caractere especial"),
        ("Com espaço apenas", "ter pelo menos 1 caractere especial"),  # espaço não conta
        ("A!" + "a" * MAX_LENGTH, f"ter no máximo {MAX_LENGTH} caracteres"),
    ],
)
def test_each_rule_of_the_policy_is_reported(password: str, problem: str) -> None:
    assert password_problems(password) == [problem]


def test_all_missing_rules_are_reported_at_once() -> None:
    assert password_problems("abc") == [
        "ter pelo menos 9 caracteres",
        "ter pelo menos 1 letra maiúscula",
        "ter pelo menos 1 caractere especial",
    ]


def test_production_hasher_uses_argon2id_with_the_owasp_minimum() -> None:
    hashed = Passwords().hash_sync("Senha-forte-1")

    assert hashed.startswith("$argon2id$v=19$m=19456,t=2,p=1$")


@pytest.mark.anyio
async def test_hash_and_verify() -> None:
    hashed = await FAST_PASSWORDS.hash("Senha-forte-1")

    assert "Senha-forte-1" not in hashed
    assert await FAST_PASSWORDS.verify(hashed, "Senha-forte-1")
    assert not await FAST_PASSWORDS.verify(hashed, "Senha-forte-2")
    assert hashed != await FAST_PASSWORDS.hash("Senha-forte-1")  # sal diferente a cada hash


@pytest.mark.anyio
async def test_missing_or_broken_hash_never_verifies() -> None:
    # Conta sem senha (só Google): a verificação roda contra um hash fictício e sempre falha.
    assert not await FAST_PASSWORDS.verify(None, "conta-inexistente")
    assert not await FAST_PASSWORDS.verify("isto-nao-e-um-hash", "Senha-forte-1")


@pytest.mark.anyio
async def test_oversized_password_is_refused_without_hashing() -> None:
    hashed = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1).hash("A!" + "a" * 200)

    assert not await FAST_PASSWORDS.verify(hashed, "A!" + "a" * 200)
