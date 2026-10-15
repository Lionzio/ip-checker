/**
 * Contrato da API pública (5.2.2), derivado do `docs/openapi.json` versionado.
 *
 * `openapi.ts` é gerado por `npm run gen:api` e nunca é editado à mão; a CI falha se ele ficar
 * diferente do OpenAPI. Assim, uma mudança no contrato do backend quebra a compilação aqui.
 */
import type { components } from "./openapi";

type Schemas = components["schemas"];

export type ValidateRequest = Schemas["ValidateRequest"];
export type ValidateResponse = Schemas["ValidateResponse"];
/** Feedback para o aluno (Sprints 18 e 19). */
export type FeedbackRequest = Schemas["FeedbackRequest"];
export type FeedbackResponse = Schemas["FeedbackResponse"];
/** Painel de plágio (Sprint 17). */
export type SimilarityResponse = Schemas["SimilarityResponse"];
export type SimilarityBand = Schemas["SimilarityBand"];
/** Métricas, trechos em comum e a comparação com a turma (Sprint 27, ADR-07). */
export type SimilarityMetrics = Schemas["SimilarityMetrics"];
export type SimilarityMatch = Schemas["SimilarityMatch"];
export type ClassSolution = Schemas["ClassSolution"];
export type SimilarityClassResponse = Schemas["SimilarityClassResponse"];
export type SimilarityClassItem = Schemas["SimilarityClassItem"];
export type Violation = Schemas["Violation"];
/** A turma inteira (Sprint 40). */
export type ValidateBatchRequest = Schemas["ValidateBatchRequest"];
export type ValidateBatchResponse = Schemas["ValidateBatchResponse"];
export type BatchResult = Schemas["BatchResult"];
export type BatchFile = Schemas["BatchFile"];
export type SimilarityMatrixResponse = Schemas["SimilarityMatrixResponse"];
export type MatrixPair = Schemas["MatrixPair"];
export type MatrixSolution = Schemas["MatrixSolution"];
export type ListPanel = Schemas["ListPanelResponse"];
/** Indícios de uso de IA, só para a equipe (Sprint 29, ADR-08). */
export type Indicators = Schemas["Indicators"];
export type Indicator = Schemas["Indicator"];
export type SyntaxErrorInfo = Schemas["SyntaxErrorInfo"];
export type ListInfo = Schemas["ListInfo"];
/** Uma questão com regra específica cadastrada no período (R-01, Sprint 24). */
export type QuestionInfo = Schemas["QuestionInfo"];
export type GabaritoComparison = Schemas["GabaritoComparison"];
export type SimilarityGabarito = Schemas["SimilarityGabarito"];
export type ErrorResponse = Schemas["ErrorResponse"];
/** A conta logada (Sprint 13). O tratamento só aparece para o próprio titular. */
export type Account = Schemas["AccountResponse"];
export type RegisterRequest = Schemas["RegisterRequest"];
/** Formas de entrar disponíveis no servidor e o cadastro pelo Google (Sprint 16). */
export type AuthOptions = Schemas["AuthOptions"];
export type GooglePending = Schemas["GooglePending"];
export type GoogleSignup = Schemas["GoogleSignup"];
export type ProfileUpdate = Schemas["ProfileUpdate"];
export type Treatment = Account["treatment"];
export type Role = Account["role"];
/** Uma conta vista no gerenciamento (Sprint 15). Nunca traz o tratamento. */
export type ManagedAccount = Schemas["ManagedAccount"];
export type MembersResponse = Schemas["MembersResponse"];
/** Uma ação do registro de gerenciamento (Sprint 23, REC-06). */
export type ManagementLogEntry = Schemas["ManagementLogEntry"];
export type AccountStatus = ManagedAccount["status"];

export type Category = Violation["category"];
export type ValidationStatus = ValidateResponse["status"];
export type Notice = ValidateResponse["notices"][number];
export type ApiErrorCode = Schemas["ErrorCode"];
