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
export type Violation = Schemas["Violation"];
export type SyntaxErrorInfo = Schemas["SyntaxErrorInfo"];
export type ListInfo = Schemas["ListInfo"];
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
export type AccountStatus = ManagedAccount["status"];

export type Category = Violation["category"];
export type ValidationStatus = ValidateResponse["status"];
export type Notice = ValidateResponse["notices"][number];
export type ApiErrorCode = Schemas["ErrorCode"];
