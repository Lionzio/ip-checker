"""O resultado da análise para o feedback, em memória (S38-04; US-22, US-32).

"Gerar feedback" e "Aprimorar com IA" vinham pedindo ao analisador a mesma análise que a
verificação acabara de fazer. Aqui fica só o resultado (o status e os itens, com os nomes legíveis
e as alternativas), por 10 minutos, pela chave do hash do código, da lista e da questão: o código
nunca entra no cache, nem o nome do aluno, a anotação ou o texto gerado. O cache é de um processo
só e some num reinício ou num deploy; sem ele, a API analisa como antes.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

#: Quanto tempo um resultado vale: o bastante para gerar, editar a anotação e gerar de novo.
TTL_S = 600.0
#: Quantos resultados no máximo; o mais antigo sai primeiro.
MAX_ENTRIES = 512


@dataclass(frozen=True, slots=True)
class CachedItem:
    kind: Literal["uso", "falta"]
    label: str
    alternative: str


@dataclass(frozen=True, slots=True)
class CachedResult:
    status: Literal["valid", "invalid"]
    items: tuple[CachedItem, ...]


def result_key(code: str, list_number: int, question_id: str | None) -> str:
    """O SHA-256 do código com a lista e a questão: a chave não deixa recuperar o código."""
    digest = hashlib.sha256()
    digest.update(f"{list_number}\x00{question_id or ''}\x00".encode())
    digest.update(code.encode("utf-8", "surrogatepass"))
    return digest.hexdigest()


class FeedbackResultCache:
    def __init__(
        self,
        *,
        ttl_s: float = TTL_S,
        max_entries: int = MAX_ENTRIES,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_s = ttl_s
        self._max = max_entries
        self._monotonic = monotonic
        self._entries: OrderedDict[str, tuple[float, CachedResult]] = OrderedDict()

    def get(self, key: str) -> CachedResult | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        stored_at, result = entry
        if self._monotonic() - stored_at > self._ttl_s:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return result

    def put(self, key: str, result: CachedResult) -> None:
        self._entries[key] = (self._monotonic(), result)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max:
            self._entries.popitem(last=False)

    def __len__(self) -> int:
        return len(self._entries)
