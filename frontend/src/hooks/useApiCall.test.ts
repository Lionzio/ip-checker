import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../services/client";
import { TIMEOUT_MESSAGE, useApiCall } from "./useApiCall";

function never(signal: AbortSignal): Promise<string> {
  return new Promise((_, reject) => {
    signal.addEventListener("abort", () => reject(new DOMException("cancelado", "AbortError")));
  });
}

afterEach(() => {
  vi.useRealTimers();
});

describe("useApiCall (S26-04)", () => {
  it("devolve o valor e para de carregar", async () => {
    const { result } = renderHook(() => useApiCall(1000, () => undefined));

    let outcome;
    await act(async () => {
      outcome = await result.current.run(() => Promise.resolve(42));
    });

    expect(outcome).toEqual({ ok: true, value: 42 });
    expect(result.current.loading).toBe(false);
  });

  it("transforma o prazo vencido em mensagem", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useApiCall(500, () => undefined));

    let pending: Promise<unknown> = Promise.resolve();
    act(() => {
      pending = result.current.run(never);
    });
    expect(result.current.loading).toBe(true);
    await act(async () => {
      vi.advanceTimersByTime(500);
      await pending;
    });

    await expect(pending).resolves.toMatchObject({ ok: false, message: TIMEOUT_MESSAGE });
    expect(result.current.loading).toBe(false);
  });

  it("cancelar não mostra erro nenhum", async () => {
    const { result } = renderHook(() => useApiCall(10_000, () => undefined));

    let pending: Promise<unknown> = Promise.resolve();
    act(() => {
      pending = result.current.run(never);
    });
    await act(async () => {
      result.current.cancel();
      await pending;
    });

    await expect(pending).resolves.toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("uma chamada nova substitui a anterior", async () => {
    const { result } = renderHook(() => useApiCall(10_000, () => undefined));

    let first: Promise<unknown> = Promise.resolve();
    let second: Promise<unknown> = Promise.resolve();
    await act(async () => {
      first = result.current.run(never);
      second = result.current.run(() => Promise.resolve("nova"));
      await Promise.all([first, second]);
    });

    await expect(first).resolves.toBeNull();
    await expect(second).resolves.toEqual({ ok: true, value: "nova" });
  });

  it("a sessão vencida vai para um lugar só", async () => {
    const expired = vi.fn();
    const { result } = renderHook(() => useApiCall(1000, expired));

    let outcome;
    await act(async () => {
      outcome = await result.current.run(() => Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre.")));
    });

    expect(outcome).toBeNull();
    expect(expired).toHaveBeenCalledOnce();
  });

  it("os outros erros trazem a mensagem da API", async () => {
    const { result } = renderHook(() => useApiCall(1000, () => undefined));

    let outcome;
    await act(async () => {
      outcome = await result.current.run(() => Promise.reject(new ApiError(503, "OVERLOADED", "Ocupado.", 10)));
    });

    expect(outcome).toMatchObject({ ok: false, message: "Ocupado." });
  });
});
