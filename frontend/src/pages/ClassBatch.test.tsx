import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
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

// A Turma é carregada sob demanda (App.tsx): o módulo vem antes, para o primeiro teste não pagar a importação.
beforeAll(async () => {
  await import("./ClassBatch");
});

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

describe("Turma inteira: erros, cancelar e CSV (S39-03)", () => {
  const files = (count: number) => Array.from({ length: count }, (_, index) => new File([VALID], `aluno${index + 1}.py`));

  it("Cancelar para no meio e mantém o que já foi conferido", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const original = client.validateBatch;
    let calls = 0;
    client.validateBatch = (request, signal) => {
      calls += 1;
      if (calls === 1) return original(request, signal);
      // A segunda parte só termina quando a correção é cancelada.
      return new Promise((_resolve, reject) => signal?.addEventListener("abort", () => reject(new DOMException("", "AbortError"))));
    };
    const user = await ready(client);
    await pick(user, files(25));

    await user.click(screen.getByRole("button", { name: "Corrigir a turma" }));
    expect(await screen.findByText("20 de 25 arquivos conferidos.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(await screen.findByText("Correção cancelada: 20 de 25 arquivos foram conferidos.")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Resultado da turma" })).getAllByRole("row")).toHaveLength(21);
    expect(screen.getByRole("button", { name: "Corrigir a turma" })).toBeEnabled();
  });

  it("Baixar CSV salva um arquivo com o nome da lista", async () => {
    const created: Blob[] = [];
    const createObjectURL = vi.fn((blob: Blob) => {
      created.push(blob);
      return "blob:turma";
    });
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const downloads: string[] = [];
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      downloads.push(this.download);
    });
    const user = await ready();
    await pick(user, [new File([VALID], "ana.py")]);
    await user.click(screen.getByRole("button", { name: "Corrigir a turma" }));
    await screen.findByRole("region", { name: "Resultado da turma" });

    await user.click(screen.getByRole("button", { name: "Baixar CSV" }));

    expect(downloads).toEqual(["ip-checker-turma-lista-1.csv"]);
    expect(await created[0]?.text()).toContain("ana;Válida");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:turma");
    click.mockRestore();
  });

  it("aceita os arquivos arrastados para a área tracejada", async () => {
    await ready();
    const area = screen.getByText("Ou arraste os arquivos ou o .zip para cá.").parentElement as HTMLElement;
    const dropped = [new File([VALID], "ana.py"), new File([LOOP], "bruno.py")];

    const over = fireEvent.dragOver(area, { dataTransfer: { types: ["Files"], files: dropped } });
    fireEvent.drop(area, { dataTransfer: { types: ["Files"], files: dropped } });

    expect(over).toBe(false); // o dragOver aceita arquivos (preventDefault)
    expect(await screen.findByText("2 arquivos prontos.")).toBeInTheDocument();
  });

  it("uma recusa do servidor no meio diz quantos foram conferidos", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.validateBatch = () => Promise.reject(new ApiError(422, "INVALID_INPUT", "A lista mudou."));
    const user = await ready(client);
    await pick(user, files(2));

    await user.click(screen.getByRole("button", { name: "Corrigir a turma" }));

    expect(await screen.findByText("A lista mudou. 0 de 2 arquivos foram conferidos.")).toBeInTheDocument();
  });

  it("sem rede, avisa e mantém os resultados já recebidos", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.validateBatch = () => Promise.reject(new TypeError("Failed to fetch"));
    const user = await ready(client);
    await pick(user, files(1));

    await user.click(screen.getByRole("button", { name: "Corrigir a turma" }));

    expect(await screen.findByText(/Não foi possível falar com o servidor/)).toBeInTheDocument();
  });

  it("depois de 5 novas tentativas sem vaga, desiste com a mensagem do servidor", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    let calls = 0;
    client.validateBatch = () => {
      calls += 1;
      return Promise.reject(new ApiError(503, "OVERLOADED", "O serviço está ocupado.", 1));
    };
    const user = await ready(client);
    await pick(user, files(1));

    await user.click(screen.getByRole("button", { name: "Corrigir a turma" }));
    await vi.advanceTimersByTimeAsync(8000);

    expect(await screen.findByText("O serviço está ocupado. 0 de 1 arquivos foram conferidos.")).toBeInTheDocument();
    expect(calls).toBe(6); // a primeira e as 5 novas tentativas
    vi.useRealTimers();
  });

  it("leva para Entrar quando a sessão vence durante a correção", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.validateBatch = () => Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre de novo."));
    const user = await ready(client);
    await pick(user, files(1));

    await user.click(screen.getByRole("button", { name: "Corrigir a turma" }));

    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  it("avisa quando as listas não carregam", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.listLists = () => Promise.reject(new ApiError(503, "DATABASE_UNAVAILABLE", "Fora do ar."));
    render(
      <MemoryRouter initialEntries={["/turma"]}>
        <App client={client} />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Não foi possível carregar as listas.")).toBeInTheDocument();
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
