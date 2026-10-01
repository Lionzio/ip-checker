/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" liga o modo demonstração, com o cliente simulado no lugar da API. */
  readonly VITE_DEMO_MODE?: string;
  /** Origem da API quando ela não está na mesma origem da página (piloto: Render). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
