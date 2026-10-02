import type {
  Account,
  ApiErrorCode,
  AuthOptions,
  GooglePending,
  GoogleSignup,
  ListInfo,
  ManagedAccount,
  MembersResponse,
  ProfileUpdate,
  RegisterRequest,
  Role,
  ValidateRequest,
  ValidateResponse,
} from "../types/api";

/** Verificação do código: o cliente HTTP real (S9-02) ou o simulado do modo demonstração. */
export interface ValidationClient {
  listLists(signal?: AbortSignal): Promise<ListInfo[]>;
  validate(request: ValidateRequest, signal?: AbortSignal): Promise<ValidateResponse>;
}

/** Sessão da equipe (Sprint 13): o cookie é HttpOnly, então a página só pergunta quem está logado. */
export interface AuthClient {
  /** A conta logada; `ApiError` 401 quando não há sessão. */
  me(signal?: AbortSignal): Promise<Account>;
  login(login: string, password: string): Promise<Account>;
  logout(): Promise<void>;
  /** Pede o cadastro (FR-23); devolve o e-mail para onde o link foi enviado. */
  register(request: RegisterRequest): Promise<string>;
  /** Confirma o e-mail pelo token do link. */
  verifyEmail(token: string): Promise<void>;
  /** Reenvia o link; a resposta é a mesma, exista a conta ou não. */
  resendVerification(email: string): Promise<void>;
  updateProfile(update: ProfileUpdate): Promise<Account>;
  /** Troca a senha (ou define uma, numa conta só do Google); as outras sessões caem. */
  changePassword(currentPassword: string | null, newPassword: string): Promise<void>;
  /** As formas de entrar configuradas no servidor (o Google pode estar desligado). */
  options(signal?: AbortSignal): Promise<AuthOptions>;
  /** O cadastro pelo Google em andamento neste navegador: e-mail e nome sugerido. */
  googlePending(signal?: AbortSignal): Promise<GooglePending>;
  /** Envia o formulário complementar do Google; devolve o e-mail do cadastro. */
  completeGoogle(request: GoogleSignup): Promise<string>;
}

/**
 * Gerenciamento da equipe (Sprint 15): só desenvolvedor, professor e monitor-chefe. Cada item
 * já traz as ações permitidas; o backend confere de novo a cada chamada.
 */
export interface AdminClient {
  listRequests(signal?: AbortSignal): Promise<ManagedAccount[]>;
  listMembers(signal?: AbortSignal): Promise<MembersResponse>;
  approve(id: string, role: Role): Promise<void>;
  reject(id: string): Promise<void>;
  changeRole(id: string, role: Role): Promise<void>;
  remove(id: string): Promise<void>;
  reactivate(id: string, role: Role): Promise<void>;
}

export type ApiClient = ValidationClient & AuthClient & AdminClient;

/** Erro no formato `{ error: { code, message, retry_after_s } }` do contrato (5.2.2). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly retryAfterS: number | null;

  constructor(status: number, code: ApiErrorCode, message: string, retryAfterS: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryAfterS = retryAfterS;
  }
}
