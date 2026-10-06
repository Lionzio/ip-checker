import { test as setup } from "@playwright/test";

/**
 * Todos os testes usam a conta do desenvolvedor, que tem 30 verificações por minuto (P-11 h). Desde a
 * Sprint 23, o projeto principal sozinho chega perto desse teto; esta pausa deixa a janela de 60 s
 * do limite virar antes dos projetos "conta", "feedback" e "limite", que verificam de novo.
 */
setup("espera a janela do limite por conta virar", async () => {
  setup.setTimeout(90_000);
  await new Promise((resolve) => setTimeout(resolve, 61_000));
});
