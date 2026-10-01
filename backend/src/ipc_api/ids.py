"""Identificador de requisição no formato ULID (5.2.2): ordenável pelo tempo e sem dado pessoal."""

from __future__ import annotations

import secrets
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_request_id() -> str:
    """48 bits de milissegundos desde 1970 e 80 bits aleatórios, em 26 caracteres base32."""
    value = (time.time_ns() // 1_000_000) << 80 | secrets.randbits(80)
    return "".join(_CROCKFORD[(value >> shift) & 31] for shift in range(125, -1, -5))
