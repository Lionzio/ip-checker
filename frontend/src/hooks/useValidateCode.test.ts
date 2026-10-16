import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, type ValidationClient } from "../services/client";
import type { ValidateRequest, ValidateResponse } from "../types/api";
import { useValidateCode } from "./useValidateCode";

const REQUEST: ValidateRequest = { code: "x = 1", list_number: 1, question_id: null };
const RESPONSE: ValidateResponse = {
  request_id: "r1",
  ruleset_version: "2026.2.0",
  status: "valid",
  list_number: 1,
  question_id: null,
  notices: [],
  syntax_error: null,
  violations: [],
  truncated: false,
};

function clientWith(validate: ValidationClient["validate"]): ValidationClient {
  return {
    listLists: () => Promise.resolve([]),
    listPeriods: () => Promise.resolve([]),
    validate,
    validateBatch: () => Promise.reject(new Error("sem lote")),
  };
}

/** Uma requisição que só termina quando é cancelada. */
function neverEnding(signals: AbortSignal[] = []): ValidationClient["validate"] {
  return (_request, signal) =>
    new Promise((_resolve, reject) => {
      if (signal) signals.push(signal);
      signal?.addEventListener("abort", () => reject(signal.reason));
    });
}

afterEach(() => {
  vi.useRealTimers();
});

describe("useValidateCode", () => {
  it("guarda a resposta de sucesso", async () => {
    const { result } = renderHook(() => useValidateCode(clientWith(() => Promise.resolve(RESPONSE))));

    await act(() => result.current.validate(REQUEST));

    expect(result.current.state).toEqual({ kind: "success", response: RESPONSE });
  });

  it.each([
    [new ApiError(422, "INVALID_INPUT", "O código está vazio."), { kind: "rejected", code: "INVALID_INPUT" }],
    [new ApiError(413, "PAYLOAD_TOO_LARGE", "grande"), { kind: "rejected", code: "PAYLOAD_TOO_LARGE" }],
    [new ApiError(429, "RATE_LIMITED", "calma", 30), { kind: "busy", code: "RATE_LIMITED", retryAfterS: 30 }],
    [new ApiError(503, "OVERLOADED", "ocupado", 10), { kind: "busy", code: "OVERLOADED", retryAfterS: 10 }],
    [
      new ApiError(503, "DATABASE_UNAVAILABLE", "indisponível", 30),
      { kind: "busy", code: "DATABASE_UNAVAILABLE", retryAfterS: 30 },
    ],
    [new ApiError(401, "UNAUTHENTICATED", "Entre."), { kind: "unauthenticated", message: "Entre." }],
    [new TypeError("Failed to fetch"), { kind: "network" }],
  ])("traduz o erro %# para o estado certo", async (error, expected) => {
    const { result } = renderHook(() => useValidateCode(clientWith(() => Promise.reject(error))));

    await act(() => result.current.validate(REQUEST));

    expect(result.current.state).toMatchObject(expected);
  });

  it("cancela por tempo limite", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useValidateCode(clientWith(neverEnding()), 10_000));

    let pending: Promise<void> = Promise.resolve();
    act(() => {
      pending = result.current.validate(REQUEST);
    });
    expect(result.current.state).toEqual({ kind: "loading" });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
      await pending;
    });

    expect(result.current.state).toEqual({
      kind: "timeout",
      message: "O servidor não respondeu em 10 segundos.",
    });
  });

  it("ignora a resposta de uma requisição substituída", async () => {
    const signals: AbortSignal[] = [];
    let calls = 0;
    const validate: ValidationClient["validate"] = (request, signal) => {
      calls += 1;
      return calls === 1 ? neverEnding(signals)(request, signal) : Promise.resolve(RESPONSE);
    };
    const { result } = renderHook(() => useValidateCode(clientWith(validate)));

    let first: Promise<void> = Promise.resolve();
    act(() => {
      first = result.current.validate(REQUEST);
    });
    await act(() => result.current.validate(REQUEST));
    await act(() => first);

    expect(signals[0]?.aborted).toBe(true);
    expect(result.current.state).toEqual({ kind: "success", response: RESPONSE });
  });

  it("Cancelar interrompe a verificação e volta ao estado inicial (S36-05)", async () => {
    const signals: AbortSignal[] = [];
    const { result } = renderHook(() => useValidateCode(clientWith(neverEnding(signals))));

    let pending: Promise<void> = Promise.resolve();
    act(() => {
      pending = result.current.validate(REQUEST);
    });
    expect(result.current.state).toEqual({ kind: "loading" });

    act(() => result.current.cancel());
    await act(() => pending);

    expect(signals[0]?.aborted).toBe(true);
    expect(result.current.state).toEqual({ kind: "idle" });
  });

  it("repete a última requisição", async () => {
    const validate = vi.fn<ValidationClient["validate"]>(() => Promise.resolve(RESPONSE));
    const { result } = renderHook(() => useValidateCode(clientWith(validate)));

    await act(() => result.current.retry());
    expect(validate).not.toHaveBeenCalled();

    await act(() => result.current.validate(REQUEST));
    await act(() => result.current.retry());
    expect(validate).toHaveBeenCalledTimes(2);
    expect(validate).toHaveBeenLastCalledWith(REQUEST, expect.any(AbortSignal));
  });

  it("cancela a requisição ao desmontar", () => {
    const signals: AbortSignal[] = [];
    const { result, unmount } = renderHook(() => useValidateCode(clientWith(neverEnding(signals))));

    act(() => {
      void result.current.validate(REQUEST);
    });
    unmount();

    expect(signals[0]?.aborted).toBe(true);
  });
});
