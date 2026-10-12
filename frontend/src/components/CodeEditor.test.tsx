import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { lineBlock } from "../editorLines";
import { CodeEditor } from "./CodeEditor";

function Editor({ initial }: { initial: string }) {
  const [value, setValue] = useState(initial);
  return <CodeEditor value={value} onChange={setValue} label="Código" />;
}

function setup(initial: string) {
  const user = userEvent.setup();
  render(<Editor initial={initial} />);
  const area = screen.getByLabelText("Código") as HTMLTextAreaElement;
  return { user, area };
}

/** Seleciona do caractere `start` ao `end` e dá o foco ao editor. */
function select(area: HTMLTextAreaElement, start: number, end: number) {
  area.focus();
  area.setSelectionRange(start, end);
}

describe("linhas da seleção (S36-03)", () => {
  const text = "a\nbb\nccc";

  it("vai do início da primeira linha ao fim da última", () => {
    expect(lineBlock(text, 3, 7)).toEqual([2, 8]);
    expect(lineBlock(text, 0, 0)).toEqual([0, 1]);
  });

  it("uma seleção que termina logo depois de um Enter não leva a linha seguinte", () => {
    expect(lineBlock(text, 0, 5)).toEqual([0, 4]);
  });
});

describe("Editor: Tab e Shift+Tab (S36-03)", () => {
  it("Tab com 3 linhas selecionadas indenta as 3, e Shift+Tab desfaz", async () => {
    const code = "if x:\ny = 1\nz = 2\nw = 3";
    const { user, area } = setup(code);
    select(area, 6, code.length);

    await user.keyboard("{Tab}");
    expect(area).toHaveValue("if x:\n    y = 1\n    z = 2\n    w = 3");

    select(area, 6, area.value.length);
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(area).toHaveValue(code);
  });

  it("linhas vazias na seleção não ganham espaços", async () => {
    const code = "a = 1\n\nb = 2";
    const { user, area } = setup(code);
    select(area, 0, code.length);
    await user.keyboard("{Tab}");
    expect(area).toHaveValue("    a = 1\n\n    b = 2");
  });

  it("Shift+Tab sem seleção desindenta a linha do cursor e tira no máximo 4 espaços", async () => {
    const code = "if x:\n      y = 1";
    const { user, area } = setup(code);
    select(area, code.length, code.length);
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(area).toHaveValue("if x:\n  y = 1");
  });

  it("Tab sem seleção continua inserindo 4 espaços", async () => {
    const { user, area } = setup("");
    await user.click(area);
    await user.keyboard("x{Tab}");
    expect(area).toHaveValue("x    ");
  });

  it("Esc e depois Tab, ou Shift+Tab, saem do editor sem mudar o código", async () => {
    const code = "if x:\n    y = 1";
    const { user, area } = setup(code);
    select(area, 0, code.length);

    await user.keyboard("{Escape}{Tab}");
    expect(area).not.toHaveFocus();
    expect(screen.getByRole("button", { name: "Colar" })).toHaveFocus();
    expect(area).toHaveValue(code);

    select(area, 0, code.length);
    await user.keyboard("{Escape}{Shift>}{Tab}{/Shift}");
    expect(area).not.toHaveFocus();
    expect(area).toHaveValue(code);
  });
});
