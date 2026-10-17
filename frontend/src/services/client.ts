import type {
  Account,
  ApiErrorCode,
  AuthOptions,
  CatalogResponse,
  ImportTokenCreated,
  ImportTokenInfo,
  FeedbackRequest,
  FeedbackResponse,
  GooglePending,
  GoogleSignup,
  ListInfo,
  ManagedAccount,
  ManagementLogEntry,
  MembersResponse,
  ProfileUpdate,
  RegisterRequest,
  Role,
  ClassSolution,
  SimilarityClassResponse,
  SimilarityResponse,
  ValidateRequest,
  ValidateResponse,
  ListPanel,
  PeriodInfo,
  SimilarityMatrixResponse,
  ValidateBatchRequest,
  ValidateBatchResponse,
} from "../types/api";

/** Verificação do código: o cliente HTTP real (S9-02) ou o simulado do modo demonstração. */
export interface ValidationClient {
  /** As listas do período (S43-02); sem período, as habilitadas do ativo. */
  listLists(signal?: AbortSignal, period?: string | null): Promise<ListInfo[]>;
  /** Os períodos carregados: o ativo e até 5 anteriores (S43-02). */
  listPeriods(signal?: AbortSignal): Promise<PeriodInfo[]>;
  validate(request: ValidateRequest, signal?: AbortSignal): Promise<ValidateResponse>;
  /** Uma parte da turma, até 20 arquivos (S40-01); a página divide a turma em partes. */
  validateBatch(request: ValidateBatchRequest, signal?: AbortSignal): Promise<ValidateBatchResponse>;
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
  /** Pede o link de "esqueci minha senha"; a resposta é a mesma, exista a conta ou não. */
  forgotPassword(email: string): Promise<void>;
  /** Define a senha nova pelo token do link; todas as sessões da conta caem. */
  resetPassword(token: string, newPassword: string): Promise<void>;
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
  /** Registro das ações (Sprint 23, REC-06), da mais recente: só desenvolvedor e professores. */
  managementLog(signal?: AbortSignal): Promise<ManagementLogEntry[]>;
  /** O painel de uma lista (S40-03): regras mais violadas, só com dados anônimos. */
  listPanel(listNumber: number, semester?: string | null, signal?: AbortSignal): Promise<ListPanel>;
}

/** Painel de plágio (Sprint 17): compara duas soluções no analisador isolado. */
export interface PlagiarismClient {
  /** Com a questão (S32-07, ADR-11), A e B também são comparados com o gabarito dela. */
  compare(
    codeA: string,
    codeB: string,
    signal?: AbortSignal,
    questionId?: string | null,
    period?: string | null,
  ): Promise<SimilarityResponse>;
  /** Uma solução contra até 100 da turma (Sprint 27): o que todos escrevem quase não conta. */
  compareClass(code: string, solutions: ClassSolution[], signal?: AbortSignal): Promise<SimilarityClassResponse>;
  /** Todos contra todos (S40-02): os pares mais parecidos e os grupos de soluções ligadas. */
  compareMatrix(solutions: ClassSolution[], signal?: AbortSignal): Promise<SimilarityMatrixResponse>;
}

/**
 * Feedback para o aluno (Sprint 19): o servidor analisa o código de novo e escreve o texto com a IA
 * principal, a de reserva ou, sem nenhuma, com modelos de texto.
 */
export interface FeedbackClient {
  feedback(request: FeedbackRequest, signal?: AbortSignal): Promise<FeedbackResponse>;
}

/** As listas do período, sincronizadas pela extensão do Dikastis (S50-06). */
export interface CatalogClient {
  catalog(period: string, signal?: AbortSignal): Promise<CatalogResponse>;
  /** O .zip dos enunciados das listas (chefia), para o gerador de referências. */
  statementsZip(period: string): Promise<Blob>;
}

/** O token de importação da extensão (S50-04): só a chefia e o desenvolvedor criam. */
export interface ImportTokenClient {
  listImportTokens(signal?: AbortSignal): Promise<ImportTokenInfo[]>;
  createImportToken(label: string): Promise<ImportTokenCreated>;
  revokeImportToken(id: string): Promise<void>;
}

export type ApiClient = ValidationClient &
  AuthClient &
  AdminClient &
  PlagiarismClient &
  FeedbackClient &
  CatalogClient &
  ImportTokenClient;

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
