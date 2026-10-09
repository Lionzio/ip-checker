"""Cliente HTTP do ``analyzer`` (5.2.1, C3): timeout de 3 s e resposta validada.

Toda falha de comunicação vira ``AnalyzerUnavailable`` (503 para o aluno): conexão recusada,
tempo esgotado, status inesperado, resposta acima de 256 KB ou fora do esquema. Só os erros
documentados do analyzer (413 e 422 com o envelope de erro) chegam ao aluno como tais.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx2
from pydantic import BaseModel, ValidationError

from ipc_api.schemas import (
    AnalyzerClass,
    AnalyzerErrorResponse,
    AnalyzerFeedbackInput,
    AnalyzerHealth,
    AnalyzerManifest,
    AnalyzerResult,
    AnalyzerSimilarity,
)

#: Teto de uma resposta do analyzer. 200 violações com mensagens longas ficam bem abaixo disso.
MAX_RESPONSE_BYTES = 256 * 1024
#: A comparação com a turma (S27-02) analisa até 101 códigos: o analyzer tem 10 s para ela.
CLASS_TIMEOUT_S = 12.0
#: O manifesto só muda quando o analyzer é reimplantado com outro ruleset.
MANIFEST_TTL_S = 60.0
#: O analyzer descarta o pedido quando este tempo acaba (S25-04).
BUDGET_HEADER = "X-IPC-Budget-Ms"


class AnalyzerUnavailable(Exception):  # noqa: N818 - é um estado, não um erro de programação
    """O analyzer não respondeu ou respondeu algo em que a API não pode confiar."""


class AnalyzerRejected(Exception):  # noqa: N818
    """O analyzer recusou a entrada com um erro do contrato (413 ou 422)."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _parse[M: BaseModel](model: type[M], body: bytes) -> M:
    try:
        return model.model_validate_json(body)
    except ValidationError:
        raise AnalyzerUnavailable(
            f"resposta do analyzer fora do esquema {model.__name__}"
        ) from None


class AnalyzerClient:
    def __init__(
        self,
        base_url: str,
        timeout_s: float,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx2.AsyncClient(
            base_url=base_url,
            timeout=httpx2.Timeout(timeout_s),
            transport=transport,
            follow_redirects=False,
            # Proxies do ambiente nunca valem para a rede interna.
            trust_env=False,
        )
        self._timeout_s = timeout_s
        self._manifest: tuple[float, AnalyzerManifest] | None = None

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        request_id: str | None = None,
        timeout_s: float | None = None,
    ) -> tuple[int, bytes]:
        timeout = timeout_s if timeout_s is not None else self._timeout_s
        # O mesmo request_id nos logs dos dois serviços liga a requisição à análise.
        headers = {BUDGET_HEADER: str(int(timeout * 1000))}
        if request_id:
            headers["X-Request-Id"] = request_id
        try:
            # O prazo vale para a chamada inteira, não para cada leitura: depois dele, a API
            # desiste, e o analyzer, que recebeu o mesmo prazo, também.
            async with (
                asyncio.timeout(timeout),
                self._http.stream(method, path, json=payload, headers=headers) as response,
            ):
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise AnalyzerUnavailable("resposta do analyzer acima de 256 KB")
                return response.status_code, bytes(body)
        except (httpx2.TimeoutException, TimeoutError):
            raise AnalyzerUnavailable("o analyzer não respondeu a tempo") from None
        except httpx2.HTTPError as exc:
            raise AnalyzerUnavailable(
                f"falha ao falar com o analyzer: {type(exc).__name__}"
            ) from None

    async def analyze(
        self,
        code: str,
        list_number: int,
        request_id: str | None = None,
        question_id: str | None = None,
        indicators: bool = False,
        gabarito: str | None = None,
    ) -> AnalyzerResult:
        payload: dict[str, Any] = {
            "code": code,
            "list_number": list_number,
            "question_id": question_id,
            "indicators": indicators,
        }
        if gabarito is not None:
            # O gabarito vai só ao analyzer, pela rede interna (ADR-11), e nunca volta.
            payload["gabarito"] = gabarito
        status, body = await self._request("POST", "/internal/analyze", payload, request_id)
        if status == 200:
            result = _parse(AnalyzerResult, body)
            if result.list_number != list_number:
                raise AnalyzerUnavailable("o analyzer respondeu sobre outra lista")
            return result
        if status in (413, 422):
            error = _parse(AnalyzerErrorResponse, body).error
            raise AnalyzerRejected(status, error.code, error.message)
        raise AnalyzerUnavailable(f"status inesperado do analyzer: {status}")

    async def feedback_input(
        self,
        code: str,
        list_number: int,
        request_id: str | None = None,
        question_id: str | None = None,
    ) -> AnalyzerFeedbackInput:
        status, body = await self._request(
            "POST",
            "/internal/feedback-input",
            {"code": code, "list_number": list_number, "question_id": question_id},
            request_id,
        )
        if status == 200:
            return _parse(AnalyzerFeedbackInput, body)
        if status in (413, 422):
            error = _parse(AnalyzerErrorResponse, body).error
            raise AnalyzerRejected(status, error.code, error.message)
        raise AnalyzerUnavailable(f"status inesperado do analyzer: {status}")

    async def similarity(
        self,
        first: str,
        second: str,
        request_id: str | None = None,
        gabarito: str | None = None,
    ) -> AnalyzerSimilarity:
        payload: dict[str, Any] = {"first": first, "second": second}
        if gabarito is not None:
            payload["gabarito"] = gabarito
        status, body = await self._request("POST", "/internal/similarity", payload, request_id)
        if status == 200:
            result = _parse(AnalyzerSimilarity, body)
            if (
                gabarito is not None
                and result.status == "compared"
                and (result.gabarito is None or len(result.gabarito) != 2)
            ):
                raise AnalyzerUnavailable("o analyzer não comparou os dois códigos com o gabarito")
            return result
        if status in (413, 422):
            error = _parse(AnalyzerErrorResponse, body).error
            raise AnalyzerRejected(status, error.code, error.message)
        raise AnalyzerUnavailable(f"status inesperado do analyzer: {status}")

    async def similarity_class(
        self, code: str, others: list[str], request_id: str | None = None
    ) -> AnalyzerClass:
        """Uma solução contra a turma (S27-02), com um prazo maior que o das outras chamadas."""
        status, body = await self._request(
            "POST",
            "/internal/similarity/class",
            {"code": code, "others": others},
            request_id,
            timeout_s=CLASS_TIMEOUT_S,
        )
        if status == 200:
            result = _parse(AnalyzerClass, body)
            if result.status == "compared" and len(result.results) != len(others):
                raise AnalyzerUnavailable("o analyzer respondeu sobre outra turma")
            return result
        if status in (413, 422):
            error = _parse(AnalyzerErrorResponse, body).error
            raise AnalyzerRejected(status, error.code, error.message)
        raise AnalyzerUnavailable(f"status inesperado do analyzer: {status}")

    async def health(self) -> AnalyzerHealth:
        status, body = await self._request("GET", "/internal/health")
        if status != 200:
            raise AnalyzerUnavailable(f"health do analyzer com status {status}")
        return _parse(AnalyzerHealth, body)

    async def manifest(self) -> AnalyzerManifest:
        now = time.monotonic()
        if self._manifest is not None and now - self._manifest[0] < MANIFEST_TTL_S:
            return self._manifest[1]
        status, body = await self._request("GET", "/internal/ruleset/manifest")
        if status != 200:
            raise AnalyzerUnavailable(f"manifesto do analyzer com status {status}")
        manifest = _parse(AnalyzerManifest, body)
        self._manifest = (now, manifest)
        return manifest
