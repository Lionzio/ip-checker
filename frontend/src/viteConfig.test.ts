// @vitest-environment node
import { describe, expect, it } from "vitest";
import config from "../vite.config";

describe("proxy do npm run dev", () => {
  it("preserva o Host, para a API reconhecer a própria origem nas requisições que mudam estado", () => {
    // Com changeOrigin, o Host viraria 127.0.0.1:8180 e o login pela 5180 seria recusado como
    // vindo de outro site (ORIGIN_MISMATCH, S13-02).
    const proxy = config.server?.proxy?.["/api"];

    expect(proxy).toMatchObject({ changeOrigin: false });
  });
});
