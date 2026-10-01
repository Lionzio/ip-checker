/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" liga o modo demonstração, com o cliente simulado no lugar da API. */
  readonly VITE_DEMO_MODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
