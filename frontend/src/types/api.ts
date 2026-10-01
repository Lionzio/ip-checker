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

export type Category = Violation["category"];
export type ValidationStatus = ValidateResponse["status"];
export type Notice = ValidateResponse["notices"][number];
export type ApiErrorCode = Schemas["ErrorCode"];
