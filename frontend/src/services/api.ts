/**
 * Cliente HTTP da API real (S9-02). A SPA e a API ficam na mesma origem: o Caddy serve a página e
 * repassa `/api/*` à API (Fases 0 e 2); no `npm run dev`, o proxy do Vite faz esse papel.
 *
 * Desde a Sprint 13, toda rota da equipe exige a sessão, que vai sozinha no cookie HttpOnly da
 * mesma origem: a página nunca vê nem guarda o identificador.
 */
import type {
  Account,
  ApiErrorCode,
  AuthOptions,
  FeedbackResponse,
  ErrorResponse,
  GooglePending,
  ListInfo,
  ManagedAccount,
  ManagementLogEntry,
  MembersResponse,
  ProfileUpdate,
  RegisterRequest,
  SimilarityClassResponse,
  SimilarityResponse,
  ValidateRequest,
  ValidateResponse,
} from "../types/api";
import { type ApiClient, ApiError } from "./client";

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

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export function createApiClient({ baseUrl = "" }: { baseUrl?: string } = {}): ApiClient {
  async function call<T>(path: string, init: RequestInit, signal?: AbortSignal): Promise<T> {
    // Erros de rede e cancelamento seguem como estão: o hook distingue rede, tempo e cancelamento.
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      signal,
      headers: { Accept: "application/json", ...init.headers },
      cache: "no-store",
      credentials: "same-origin",
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
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        },
        signal,
      );
    },
    me(signal) {
      return call<Account>("/api/v1/auth/me", { method: "GET" }, signal);
    },
    login(login, password) {
      return call<Account>("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login, password }),
      });
    },
    async logout() {
      // Corpo vazio, mas presente: a borda recusa POST sem Content-Length (S10).
      await call<null>("/api/v1/auth/logout", { method: "POST", body: "" });
    },
    async register(request: RegisterRequest) {
      const body = await call<{ email: string }>("/api/v1/auth/register", json("POST", request));
      return body.email;
    },
    async verifyEmail(token) {
      await call<unknown>("/api/v1/auth/verify", json("POST", { token }));
    },
    async resendVerification(email) {
      await call<null>("/api/v1/auth/verify/resend", json("POST", { email }));
    },
    async forgotPassword(email) {
      await call<null>("/api/v1/auth/password/forgot", json("POST", { email }));
    },
    async resetPassword(token, newPassword) {
      await call<null>("/api/v1/auth/password/reset", json("POST", { token, new_password: newPassword }));
    },
    updateProfile(update: ProfileUpdate) {
      return call<Account>("/api/v1/profile", json("PATCH", update));
    },
    async changePassword(currentPassword, newPassword) {
      await call<null>(
        "/api/v1/profile/password",
        json("POST", { current_password: currentPassword, new_password: newPassword }),
      );
    },
    feedback(request, signal) {
      return call<FeedbackResponse>("/api/v1/feedback", json("POST", request), signal);
    },
    compare(codeA, codeB, signal) {
      return call<SimilarityResponse>(
        "/api/v1/similarity",
        json("POST", { code_a: codeA, code_b: codeB }),
        signal,
      );
    },
    compareClass(code, solutions, signal) {
      return call<SimilarityClassResponse>(
        "/api/v1/similarity/batch",
        json("POST", { code, solutions }),
        signal,
      );
    },
    options(signal) {
      return call<AuthOptions>("/api/v1/auth/options", { method: "GET" }, signal);
    },
    googlePending(signal) {
      return call<GooglePending>("/api/v1/auth/google/pending", { method: "GET" }, signal);
    },
    async completeGoogle(request) {
      const body = await call<{ email: string }>("/api/v1/auth/google/complete", json("POST", request));
      return body.email;
    },
    async listRequests(signal) {
      const body = await call<{ items: ManagedAccount[] }>("/api/v1/admin/requests", { method: "GET" }, signal);
      return body.items;
    },
    listMembers(signal) {
      return call<MembersResponse>("/api/v1/admin/members", { method: "GET" }, signal);
    },
    async approve(id, role) {
      await call<null>(`/api/v1/admin/requests/${encodeURIComponent(id)}/approve`, json("POST", { role }));
    },
    async reject(id) {
      // Corpo vazio, mas presente: a borda recusa POST sem Content-Length (S10).
      await call<null>(`/api/v1/admin/requests/${encodeURIComponent(id)}/reject`, { method: "POST", body: "" });
    },
    async changeRole(id, role) {
      await call<null>(`/api/v1/admin/members/${encodeURIComponent(id)}/role`, json("PATCH", { role }));
    },
    async remove(id) {
      await call<null>(`/api/v1/admin/members/${encodeURIComponent(id)}/remove`, { method: "POST", body: "" });
    },
    async reactivate(id, role) {
      await call<null>(`/api/v1/admin/members/${encodeURIComponent(id)}/reactivate`, json("POST", { role }));
    },
    async managementLog(signal) {
      const body = await call<{ items: ManagementLogEntry[] }>("/api/v1/admin/log", { method: "GET" }, signal);
      return body.items;
    },
  };
}
