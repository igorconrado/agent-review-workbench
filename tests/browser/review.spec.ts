import { test, expect } from "@playwright/test";
test("review and execute a synthetic effect with persisted result", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Senha", { exact: true })
    .fill("Synthetic-Test-Password");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await page.getByRole("button", { name: "Criar caso", exact: true }).click();
  await page
    .getByRole("button", { name: "Reunir evidências e propor" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Sinalizar reembolso" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Aprovar proposta" }).click();
  await page.getByRole("button", { name: "Executar no sandbox" }).click();
  await expect(
    page.getByText("Efeito idempotente registrado e verificado.", {
      exact: false,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Efeito verificado" }),
  ).toBeVisible();
});
test("missing evidence abstains and keyboard login works", async ({ page }) => {
  await page.goto("/");
  await page
    .getByLabel("Senha", { exact: true })
    .fill("Synthetic-Test-Password");
  await page.getByLabel("Senha", { exact: true }).press("Enter");
  await page.getByLabel("Cenário").selectOption("unknown");
  await page.getByRole("button", { name: "Criar caso", exact: true }).click();
  await page
    .getByRole("button", { name: "Reunir evidências e propor" })
    .click();
  await expect(page.getByRole("heading", { name: "Abster-se" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Aprovar proposta" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Rejeitar", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Rejeitado" })).toBeVisible();
});
