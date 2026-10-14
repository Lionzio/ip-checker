/**
 * O tema da página (S37-05): claro, escuro ou do sistema, guardado neste navegador em
 * `localStorage` ("ipc:tema"). O `public/theme.js` aplica a preferência antes da primeira pintura;
 * daqui em diante, este módulo mantém o `data-theme` do `<html>` em dia e avisa quem o usa.
 */
export type ThemePreference = "light" | "dark" | "system";
export type Theme = "light" | "dark";

export const THEME_KEY = "ipc:tema";
export const THEME_LABELS: Record<ThemePreference, string> = { light: "Claro", dark: "Escuro", system: "Do sistema" };
export const THEME_OPTIONS: ThemePreference[] = ["light", "dark", "system"];

const DARK_QUERY = "(prefers-color-scheme: dark)";
const listeners = new Set<() => void>();

function isPreference(value: unknown): value is ThemePreference {
  return value === "light" || value === "dark" || value === "system";
}

/** A preferência guardada; sem armazenamento ou sem escolha, "system". */
export function getPreference(): ThemePreference {
  try {
    const saved = window.localStorage.getItem(THEME_KEY);
    return isPreference(saved) ? saved : "system";
  } catch {
    return "system";
  }
}

/** O tema que vale para uma preferência: "system" segue o sistema operacional. */
export function resolveTheme(preference: ThemePreference): Theme {
  if (preference !== "system") return preference;
  return window.matchMedia?.(DARK_QUERY).matches ? "dark" : "light";
}

/** Põe o tema no `<html>`, como o `theme.js` fez na carga. */
export function applyTheme(preference: ThemePreference = getPreference()) {
  document.documentElement.dataset.theme = resolveTheme(preference);
}

export function setPreference(preference: ThemePreference) {
  try {
    if (preference === "system") window.localStorage.removeItem(THEME_KEY);
    else window.localStorage.setItem(THEME_KEY, preference);
  } catch {
    // Sem armazenamento (janela anônima, bloqueio): o tema vale só até a página recarregar.
  }
  applyTheme(preference);
  for (const listener of listeners) listener();
}

/** Avisa as telas que mostram a escolha (o Perfil e o menu da conta) quando ela muda. */
export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Com a preferência "do sistema", acompanha o sistema operacional enquanto a página está aberta. */
export function followSystem(): () => void {
  const media = window.matchMedia?.(DARK_QUERY);
  if (media === undefined) return () => undefined;
  const update = () => {
    if (getPreference() === "system") applyTheme("system");
  };
  media.addEventListener("change", update);
  return () => media.removeEventListener("change", update);
}
