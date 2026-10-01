/**
 * Identificador anônimo da sessão (5.2.1, C1): um UUID aleatório, guardado em `sessionStorage`,
 * enviado no cabeçalho `X-Client-Id`. Serve só ao limite de taxa da API (10 verificações por
 * minuto por cliente), para que um aluno não seja bloqueado pelos colegas que saem pelo mesmo IP.
 *
 * Não identifica ninguém: some quando a aba é fechada, não vai para `localStorage` e a API não o
 * grava em lugar nenhum.
 */

const STORAGE_KEY = "ipc-client-id";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Usado quando o `sessionStorage` não está disponível (navegação privada restrita, por exemplo). */
let memoryId: string | null = null;

function randomUuid(): string {
  // `randomUUID` só existe em contexto seguro (HTTPS ou localhost).
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = ((bytes[6] ?? 0) & 0x0f) | 0x40; // versão 4
  bytes[8] = ((bytes[8] ?? 0) & 0x3f) | 0x80; // variante RFC 4122
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function getClientId(): string {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (stored !== null && UUID.test(stored)) return stored;
    const created = randomUuid();
    sessionStorage.setItem(STORAGE_KEY, created);
    return created;
  } catch {
    memoryId ??= randomUuid();
    return memoryId;
  }
}
