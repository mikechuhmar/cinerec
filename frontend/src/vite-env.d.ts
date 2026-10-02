/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend API base URL for static hosting. Falls back to "/api" when unset. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
