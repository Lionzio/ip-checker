import { describe, expect, it } from "vitest";
import { passwordAccepted, passwordRules } from "./passwordPolicy";

// Os mesmos casos de backend/tests/test_passwords.py: as duas pontas têm a mesma política.
describe("política de senha (FR-23)", () => {
  it.each(["Senha-forte-1", "ABCDEFGH!", "Çãéíóú?Xz", "Maiúscula com espaço!"])("aceita %s", (password) => {
    expect(passwordAccepted(password)).toBe(true);
  });

  it.each([
    ["Curta-1!", 0],
    ["sem-maiuscula-1", 1],
    ["SemEspecial1", 2],
    ["Com espaço apenas", 2],
    ["A!" + "a".repeat(128), 0],
  ])("recusa %s pela regra %i", (password, rule) => {
    const rules = passwordRules(password);

    expect(rules[rule]?.met).toBe(false);
    expect(rules.filter((item) => !item.met)).toHaveLength(1);
    expect(passwordAccepted(password)).toBe(false);
  });
});
