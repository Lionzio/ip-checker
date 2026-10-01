"""Controle de admissão (S10-01, FR-19, NFR-05): a API nunca empilha mais análises do que o
analyzer consegue atender.

``capacity`` análises correm ao mesmo tempo (2 por worker do analyzer). As seguintes esperam uma
vaga por no máximo ``max_wait_s``; isso absorve rajadas curtas, como vários alunos clicando no
mesmo instante. Com a fila de espera cheia, a recusa é imediata: sob sobrecarga de verdade, o
aluno recebe o 503 ``OVERLOADED`` em milissegundos, em vez de esperar por um erro.

A vaga só é ocupada durante a chamada ao analyzer, depois de o corpo ter sido lido e validado:
uma conexão lenta ou uma entrada inválida nunca seguram uma vaga.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdmissionConfig:
    #: Análises simultâneas: 2 por worker do analyzer (2 workers por padrão).
    capacity: int = 4
    #: Requisições que podem esperar por uma vaga ao mesmo tempo.
    max_waiting: int = 64
    #: Espera máxima por uma vaga, em segundos.
    max_wait_s: float = 1.0


class Overloaded(Exception):  # noqa: N818 - é um estado, não um erro de programação
    """Não há vaga nem lugar na fila, ou a espera passou do limite."""


class Admission:
    """Tem de ser criado dentro do laço de eventos que vai usá-lo (no lifespan da aplicação)."""

    def __init__(self, config: AdmissionConfig) -> None:
        self._config = config
        self._semaphore = asyncio.Semaphore(config.capacity)
        self._waiting = 0

    @property
    def waiting(self) -> int:
        return self._waiting

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        if self._semaphore.locked():
            if self._waiting >= self._config.max_waiting:
                raise Overloaded
            self._waiting += 1
            try:
                await asyncio.wait_for(self._semaphore.acquire(), self._config.max_wait_s)
            except TimeoutError:
                raise Overloaded from None
            finally:
                self._waiting -= 1
        else:
            await self._semaphore.acquire()
        try:
            yield
        finally:
            self._semaphore.release()
