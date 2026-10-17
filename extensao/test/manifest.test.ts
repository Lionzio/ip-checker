import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const raiz = resolve(import.meta.dirname, "..");
const manifest = JSON.parse(readFileSync(resolve(raiz, "manifest.json"), "utf8")) as {
  manifest_version: number;
  key: string;
  version: string;
  permissions: string[];
  host_permissions: string[];
  optional_host_permissions: string[];
  content_scripts: { matches: string[]; js: string[] }[];
  background: { service_worker: string; type: string };
};

/** O ID que o Chrome deriva da chave pública: SHA-256 do DER, 32 dígitos hex em a–p. */
function idDaChave(chave: string): string {
  const hex = createHash("sha256").update(Buffer.from(chave, "base64")).digest("hex").slice(0, 32);
  return [...hex].map((c) => String.fromCharCode(97 + parseInt(c, 16))).join("");
}

describe("o manifesto da extensão", () => {
  it("tem o ID fixo que a API aceita como origem", () => {
    const settings = readFileSync(resolve(raiz, "../backend/src/ipc_api/settings.py"), "utf8");
    const padrao = /DEFAULT_EXTENSION_ID = "([a-p]{32})"/.exec(settings)?.[1];

    expect(idDaChave(manifest.key)).toBe("hbndgmplpohgfbmdemopbbibfocbkdhh");
    expect(padrao).toBe(idDaChave(manifest.key));
  });

  it("pede só as permissões mínimas", () => {
    expect(manifest.manifest_version).toBe(3);
    expect(manifest.permissions).toEqual(["storage"]);
    expect(manifest.host_permissions).toEqual([
      "https://dikastis.com.br/*",
      "https://ip-checker-red-phi.vercel.app/*",
    ]);
    expect(manifest.optional_host_permissions).toEqual(["http://127.0.0.1/*", "http://localhost/*"]);
    expect(JSON.stringify(manifest)).not.toMatch(/<all_urls>|"tabs"|"cookies"|"scripting"/);
  });

  it("o script da página roda só no Dikastis, e a versão é a do package.json", () => {
    const pacote = JSON.parse(readFileSync(resolve(raiz, "package.json"), "utf8")) as {
      version: string;
    };

    expect(manifest.content_scripts).toEqual([
      { matches: ["https://dikastis.com.br/*"], js: ["content.js"], run_at: "document_idle" },
    ]);
    expect(manifest.background).toEqual({ service_worker: "background.js", type: "module" });
    expect(manifest.version).toBe(pacote.version);
  });
});
