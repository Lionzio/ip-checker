import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { batchCsv, studentOf } from "../classBatch";
import { ApiError } from "../services/client";
import { createMockClient } from "../services/mockClient";
import type { BatchResult } from "../types/api";

const VALID = "x = int(input())\nif x > 0:\n    print(x)\n";
const LOOP = "n = int(input())\nfor i in range(n):\n    print(i)\n";

async function ready(client = createMockClient({ latencyMs: 0, signedIn: true })) {
  const user = userEvent.setup({ applyAccept: false });
  render(
    <MemoryRouter initialEntries={["/turma"]}>
      <App client={client} />
    </MemoryRouter>,
  );
  await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
  await user.selectOptions(screen.getByLabelText("Lista"), "1");
  return user;
}

const pick = (user: ReturnType<typeof userEvent.setup>, files: File[]) =>
  user.upload(screen.getByLabelText("Arquivos da turma (.py ou .zip)"), files);

beforeEach(() => {
  window.localStorage.clear();
});

describe("Turma inteira (S40-01)", () => {
  it("corrige os arquivos e mostra uma linha por aluno, com as violações por categoria", async () => {
    const user = await ready();
    await pick(user, [new File([VALID], "ana.py"), new File([LOOP], "bruno.py"), new File(["x = (1\n"], "carla.py")]);
    expect(screen.getByText("3 arquivos prontos.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Corrigir a turma" }));

    const table = within(await screen.findByRole("region", { name: "Resultado da turma" }));
    const rows = await table.findAllByRole("row");
    expect(rows.slice(1).map((row) => row.querySelector("th")?.textContent)).toEqual(["ana", "bruno", "carla"]);
    expect(rows[1]).toHaveTextContent("Válida");
    expect(rows[2]).toHaveTextContent("Com violações");
    expect(rows[3]).toHaveTextContent("Erro de sintaxe");
    expect(table.getByText(/1 válidas, 1 com violações, 1 com erro de sintaxe/)).toBeInTheDocument();
  });

  it("espera o tempo que o servidor pede e continua de onde parou", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const original = client.validateBatch;
    let calls = 0;
    client.validateBatch = (request, signal) => {
      calls += 1;
      if (calls === 1) return Promise.reject(new ApiError(429, "RATE_LIMITED", "Calma.", 2));
      return original(request, signal);
    };
    const user = await ready(client);
    await pick(user, [new File([VALID], "ana.py")]);

    await user.click(screen.getByRole("button", { name: "Corrigir a turma" }));
    expect(await screen.findByText(/O servidor pediu uma pausa: continua em 2 s/)).toBeInTheDocument();
    await vi.advanceTimersByTimeAsync(2500);

    await waitFor(() => expect(screen.getByRole("region", { name: "Resultado da turma" })).toHaveTextContent("ana"));
    expect(calls).toBe(2);
    vi.useRealTimers();
  });

  it("avisa o que ficou de fora e não manda nada sem lista", async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(
      <MemoryRouter initialEntries={["/turma"]}>
        <App client={createMockClient({ latencyMs: 0, signedIn: true })} />
      </MemoryRouter>,
    );
    await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
    await pick(user, [new File([VALID], "ana.py"), new File(["x"], "notas.txt")]);

    expect(screen.getByText("1 arquivo ficou de fora")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Corrigir a turma" })).toBeDisabled();
  });
});

describe("CSV da turma (S40-01)", () => {
  const result = (name: string, status: BatchResult["status"], extra: Partial<BatchResult> = {}): BatchResult => ({
    name,
    status,
    counts: {},
    rule_ids: [],
    syntax_error: null,
    message: null,
    gabarito_similarity: null,
    ...extra,
  });

  it("uma linha por aluno, com ponto e vírgula, BOM e sem código", () => {
    const csv = batchCsv(
      [
        result("ana.py", "valid", { gabarito_similarity: 87.5 }),
        result("bruno; o terceiro.py", "invalid", { counts: { ANULACAO: 2, FORA_DA_LISTA: 1 }, rule_ids: ["R-06", "R-34"] }),
      ],
      { list: "Lista 1: Comandos condicionais", questionId: "L1-Q2" },
    );

    expect(csv.startsWith("﻿")).toBe(true);
    expect(csv.split("\r\n").slice(0, 3)).toEqual([
      "﻿aluno;status;anulação;proibido na questão;exigência;fora da lista;não consta;regras;gabarito (%);lista;questão",
      "ana;Válida;0;0;0;0;0;;87,5;Lista 1: Comandos condicionais;L1-Q2",
      '"bruno; o terceiro";Com violações;2;0;0;1;0;R-06 R-34;;Lista 1: Comandos condicionais;L1-Q2',
    ]);
  });

  it("o aluno é o nome do arquivo sem o .py", () => {
    expect(studentOf("ana.py")).toBe("ana");
    expect(studentOf("ana.py (2)")).toBe("ana (2)");
    expect(studentOf("sem-extensao")).toBe("sem-extensao");
  });
});
