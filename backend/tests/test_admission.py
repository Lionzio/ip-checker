"""Controle de admissão (S10-01, NFR-05): vagas, fila de espera limitada e recusa rápida."""

from __future__ import annotations

import asyncio
import time

import pytest

from ipc_api.admission import Admission, AdmissionConfig, Overloaded


async def hold(admission: Admission, entered: asyncio.Event, release: asyncio.Event) -> None:
    async with admission.slot():
        entered.set()
        await release.wait()


def test_capacity_runs_at_the_same_time_and_the_next_waits() -> None:
    async def scenario() -> None:
        admission = Admission(AdmissionConfig(capacity=2, max_waiting=5, max_wait_s=5))
        release = asyncio.Event()
        entered = [asyncio.Event() for _ in range(3)]
        tasks = [asyncio.create_task(hold(admission, event, release)) for event in entered]

        await asyncio.wait_for(asyncio.gather(entered[0].wait(), entered[1].wait()), 1)
        await asyncio.sleep(0.05)
        assert not entered[2].is_set()
        assert admission.waiting == 1

        release.set()
        await asyncio.wait_for(asyncio.gather(*tasks), 1)
        assert entered[2].is_set()
        assert admission.waiting == 0

    asyncio.run(scenario())


def test_waiting_longer_than_the_limit_is_overloaded() -> None:
    async def scenario() -> float:
        admission = Admission(AdmissionConfig(capacity=1, max_waiting=5, max_wait_s=0.2))
        release, entered = asyncio.Event(), asyncio.Event()
        holder = asyncio.create_task(hold(admission, entered, release))
        await entered.wait()

        start = time.perf_counter()
        with pytest.raises(Overloaded):
            async with admission.slot():
                pytest.fail("não deveria ter conseguido a vaga")
        elapsed = time.perf_counter() - start

        assert admission.waiting == 0
        release.set()
        await holder
        return elapsed

    assert 0.15 <= asyncio.run(scenario()) < 1.0


def test_full_waiting_room_is_refused_immediately() -> None:
    async def scenario() -> float:
        admission = Admission(AdmissionConfig(capacity=1, max_waiting=2, max_wait_s=5))
        release = asyncio.Event()
        entered = [asyncio.Event() for _ in range(3)]
        tasks = [asyncio.create_task(hold(admission, event, release)) for event in entered]
        await entered[0].wait()
        await asyncio.sleep(0.05)
        assert admission.waiting == 2

        start = time.perf_counter()
        with pytest.raises(Overloaded):
            async with admission.slot():
                pytest.fail("não deveria ter conseguido a vaga")
        elapsed = time.perf_counter() - start

        release.set()
        await asyncio.gather(*tasks)
        return elapsed

    # NFR-05: sob sobrecarga, a recusa sai em menos de 100 ms.
    assert asyncio.run(scenario()) < 0.1


def test_slot_is_released_after_an_error() -> None:
    async def scenario() -> None:
        admission = Admission(AdmissionConfig(capacity=1, max_waiting=0, max_wait_s=0.1))
        with pytest.raises(RuntimeError, match="falhou"):
            async with admission.slot():
                raise RuntimeError("falhou")

        async with admission.slot():
            pass

    asyncio.run(scenario())


def test_cancelled_waiter_leaves_no_trace() -> None:
    async def scenario() -> None:
        admission = Admission(AdmissionConfig(capacity=1, max_waiting=5, max_wait_s=5))
        release, entered, never = asyncio.Event(), asyncio.Event(), asyncio.Event()
        holder = asyncio.create_task(hold(admission, entered, release))
        await entered.wait()
        waiter = asyncio.create_task(hold(admission, never, release))
        await asyncio.sleep(0.05)
        assert admission.waiting == 1

        waiter.cancel()  # o aluno fechou a página enquanto esperava
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert admission.waiting == 0

        release.set()
        await holder
        async with admission.slot():  # a vaga não ficou presa
            pass

    asyncio.run(scenario())


def test_zero_capacity_refuses_everything() -> None:
    async def scenario() -> None:
        admission = Admission(AdmissionConfig(capacity=0, max_waiting=0))
        with pytest.raises(Overloaded):
            async with admission.slot():
                pytest.fail("não deveria ter conseguido a vaga")

    asyncio.run(scenario())
