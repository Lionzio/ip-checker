/**
 * Cliente HTTP da API real (S9-02). A SPA e a API ficam na mesma origem: o Caddy serve a página e
 * repassa `/api/*` à API (Fases 0 e 2); no `npm run dev`, o proxy do Vite faz esse papel.
 */
import type { ApiErrorCode, ErrorResponse, ListInfo, ValidateRequest, ValidateResponse } from "../types/api";
import { ApiError, type ValidationClient } from "./client";
import { getClientId } from "./clientId";

const UNAVAILABLE_MESSAGE = "O serviço está indisponível no momento. Tente de novo em alguns segundos.";

function isErrorResponse(body: unknown): body is ErrorResponse {
  if (typeof body !== "object" || body === null || !("error" in body)) return false;
  const error = (body as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { code?: unknown }).code === "string" &&
    typeof (error as { message?: unknown }).message === "string"
  );
}

function retryAfterHeader(response: Response): number | null {
  const value = response.headers.get("Retry-After");
  return value !== null && /^\d+$/.test(value) ? Number(value) : null;
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export function createApiClient({ baseUrl = "" }: { baseUrl?: string } = {}): ValidationClient {
  async function call<T>(path: string, init: RequestInit, signal?: AbortSignal): Promise<T> {
    // Erros de rede e cancelamento seguem como estão: o hook distingue rede, tempo e cancelamento.
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      signal,
      headers: { Accept: "application/json", ...init.headers },
      cache: "no-store",
    });
    const body = await readJson(response);
    if (response.ok) return body as T;
    if (isErrorResponse(body)) {
      const { code, message, retry_after_s: retryAfterS } = body.error;
      // O tempo de espera vem no corpo e no cabeçalho Retry-After; vale o que estiver presente.
      throw new ApiError(response.status, code, message, retryAfterS ?? retryAfterHeader(response));
    }
    // Resposta fora do contrato (por exemplo, um proxy sem a API atrás): trata como indisponível.
    const code: ApiErrorCode = "ANALYZER_UNAVAILABLE";
    throw new ApiError(response.status >= 500 ? response.status : 503, code, UNAVAILABLE_MESSAGE);
  }

  return {
    listLists(signal) {
      return call<ListInfo[]>("/api/v1/lists", { method: "GET" }, signal);
    },
    validate(request: ValidateRequest, signal) {
      return call<ValidateResponse>(
        "/api/v1/validate",
        {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Client-Id": getClientId() },
          body: JSON.stringify(request),
        },
        signal,
      );
    },
  };
}
