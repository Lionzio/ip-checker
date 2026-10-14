import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { applyTheme, followSystem, getPreference, resolveTheme, setPreference, subscribe, THEME_KEY } from "./theme";

/** O tema (S37-05): a preferência deste navegador e o `data-theme` do `<html>`. */
function mockSystem(dark: boolean) {
  const listeners = new Set<() => void>();
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: dark && query.includes("dark"),
    media: query,
    addEventListener: (_: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_: string, listener: () => void) => listeners.delete(listener),
  }));
  return { change: (nowDark: boolean) => (mockSystem(nowDark), listeners.forEach((listener) => listener())) };
}

beforeEach(() => {
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("tema (S37-05)", () => {
  it("sem escolha, segue o sistema", () => {
    mockSystem(true);

    expect(getPreference()).toBe("system");
    expect(resolveTheme("system")).toBe("dark");
    applyTheme();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("a escolha fica neste navegador e vale sobre o sistema", () => {
    mockSystem(true);

    setPreference("light");

    expect(window.localStorage.getItem(THEME_KEY)).toBe("light");
    expect(getPreference()).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");

    setPreference("system");
    expect(window.localStorage.getItem(THEME_KEY)).toBeNull();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("ignora um valor estranho guardado", () => {
    window.localStorage.setItem(THEME_KEY, "roxo");

    expect(getPreference()).toBe("system");
  });

  it("avisa quem escuta quando a escolha muda", () => {
    const listener = vi.fn();
    const stop = subscribe(listener);

    setPreference("dark");
    expect(listener).toHaveBeenCalledOnce();

    stop();
    setPreference("light");
    expect(listener).toHaveBeenCalledOnce();
  });

  it("com 'do sistema', acompanha o sistema enquanto a página está aberta", () => {
    const system = mockSystem(false);
    applyTheme();
    const stop = followSystem();
    expect(document.documentElement.dataset.theme).toBe("light");

    system.change(true);
    expect(document.documentElement.dataset.theme).toBe("dark");

    setPreference("light");
    system.change(false);
    expect(document.documentElement.dataset.theme).toBe("light");
    stop();
  });

  it("sem armazenamento, o tema vale só até recarregar, sem erro", () => {
    mockSystem(false);
    const broken = { getItem: () => { throw new Error("bloqueado"); }, setItem: () => { throw new Error("bloqueado"); }, removeItem: () => { throw new Error("bloqueado"); } };
    vi.stubGlobal("localStorage", broken);

    expect(getPreference()).toBe("system");
    expect(() => setPreference("dark")).not.toThrow();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
