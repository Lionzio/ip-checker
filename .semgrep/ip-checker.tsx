// Casos de teste das regras TypeScript de ip-checker.yml (semgrep --test). Nunca é compilado nem
// importado: só o Semgrep lê este arquivo.

export function Exemplo({ code, url }: { code: string; url: string }) {
  // ruleid: ts-eval
  eval(code);
  // ruleid: ts-eval
  const run = new Function(code);
  // ruleid: ts-eval
  setTimeout("alert(1)", 10);
  // ok: ts-eval
  setTimeout(() => run(), 10);

  const element = document.createElement("div");
  // ruleid: ts-raw-html
  element.innerHTML = code;
  // ruleid: ts-raw-html
  document.write(code);
  // ok: ts-raw-html
  element.textContent = code;

  // ruleid: ts-open-without-noopener
  window.open(url, "_blank");
  // ok: ts-open-without-noopener
  window.open(url, "_blank", "noopener,noreferrer");
  // ruleid: ts-open-without-noopener
  window.open(url, "_blank", "width=400");

  // ruleid: ts-raw-html
  const raw = <pre dangerouslySetInnerHTML={{ __html: code }} />;
  // ok: ts-raw-html
  const text = <pre>{code}</pre>;

  return (
    <div>
      {raw}
      {text}
    </div>
  );
}
