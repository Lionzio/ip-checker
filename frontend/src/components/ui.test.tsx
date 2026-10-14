import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";
import { Button, Card, LineChip, SyntaxErrorBox } from "./ui";

describe("Button (S37-03)", () => {
  it("é um botão comum, de tipo button, com o tamanho de mesa a partir de sm", () => {
    render(<Button>Verificar</Button>);
    const button = screen.getByRole("button", { name: "Verificar" });

    expect(button).toHaveAttribute("type", "button");
    expect(button.className).toContain("min-h-11");
    expect(button.className).toContain("sm:min-h-9");
    expect(button.className).toContain("focus-visible:outline-2");
  });

  it("o tamanho sm cabe numa linha de tabela e mantém os 44 px no toque", () => {
    render(
      <Button size="sm" variant="danger">
        Remover
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Remover" });

    expect(button.className).toContain("min-h-11");
    expect(button.className).toContain("sm:min-h-8");
    expect(button.className).toContain("text-red-800");
  });

  it("a variante link tem cara de link e não ganha borda nem fundo", () => {
    render(<Button variant="link">Colar</Button>);
    const button = screen.getByRole("button", { name: "Colar" });

    expect(button.className).toContain("underline");
    expect(button.className).not.toContain("border");
    expect(button.className).not.toContain("bg-blue");
  });

  it("aceita type, disabled, ref e as classes extras", async () => {
    const onClick = vi.fn();
    const ref = createRef<HTMLButtonElement>();
    render(
      <Button type="submit" ref={ref} className="self-start" onClick={onClick}>
        Salvar
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Salvar" });

    expect(button).toHaveAttribute("type", "submit");
    expect(button.className).toContain("self-start");
    expect(ref.current).toBe(button);
    await userEvent.click(button);
    expect(onClick).toHaveBeenCalledOnce();
  });
});

describe("Card", () => {
  it("é uma seção com nome por padrão", () => {
    render(<Card aria-label="Resultado">conteúdo</Card>);

    expect(screen.getByRole("region", { name: "Resultado" }).className).toContain("p-4");
  });

  it("vira item de lista com o recuo menor e as classes extras", () => {
    render(
      <ul>
        <Card as="li" padding="sm" className="border-l-4">
          regra
        </Card>
      </ul>,
    );
    const item = screen.getByRole("listitem");

    expect(item.className).toContain("p-3");
    expect(item.className).toContain("border-l-4");
  });
});

describe("LineChip", () => {
  it("é um botão em fonte de código, com o rótulo acessível", async () => {
    const onClick = vi.fn();
    render(
      <LineChip aria-label="Linha 3, coluna 1: selecionar no editor" onClick={onClick}>
        Linha 3, coluna 1
      </LineChip>,
    );
    const chip = screen.getByRole("button", { name: "Linha 3, coluna 1: selecionar no editor" });

    expect(chip.className).toContain("font-mono");
    await userEvent.click(chip);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("sem mono, usa a fonte do texto e aceita aria-pressed", () => {
    render(
      <LineChip mono={false} aria-pressed>
        linhas 2–4
      </LineChip>,
    );
    const chip = screen.getByRole("button", { name: "linhas 2–4", pressed: true });

    expect(chip.className).not.toContain("font-mono");
  });
});

describe("SyntaxErrorBox", () => {
  it("com headingRef, o título é um h2 que pode receber o foco", () => {
    const ref = createRef<HTMLHeadingElement>();
    render(<SyntaxErrorBox title="Erro de sintaxe" line={4} col={7} message="faltou ':'" headingRef={ref} />);
    const heading = screen.getByRole("heading", { level: 2, name: "Erro de sintaxe" });

    expect(ref.current).toBe(heading);
    expect(heading).toHaveAttribute("tabindex", "-1");
    expect(screen.getByText("Linha 4, coluna 7: faltou ':'")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("como alerta, anuncia e usa um h3", () => {
    render(
      <SyntaxErrorBox title="O código A tem um erro de sintaxe" line={1} col={2} message="x" alert>
        <p>Os dois códigos precisam ser Python válido.</p>
      </SyntaxErrorBox>,
    );

    expect(screen.getByRole("alert")).toContainElement(screen.getByRole("heading", { level: 3 }));
    expect(screen.getByText("Os dois códigos precisam ser Python válido.")).toBeInTheDocument();
  });
});
