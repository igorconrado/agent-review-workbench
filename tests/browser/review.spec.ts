import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";

test("Portuguese errors are focused and expired sessions return to login", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Senha", { exact: true })
    .fill("incorrect-synthetic-password");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "Confira seu usuário e sua senha.",
  );
  await expect(page.locator(".feedback")).toBeFocused();
  await expect(page.getByRole("alert")).toBeInViewport();
  await page
    .getByLabel("Senha", { exact: true })
    .fill("Synthetic-Test-Password");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Atualizar dados", exact: true }),
  ).toBeVisible();
  await page.request.delete("/api/session", {
    headers: { origin: "http://127.0.0.1:3200" },
  });
  await page
    .getByRole("button", { name: "Atualizar dados", exact: true })
    .click();
  await expect(page.getByRole("alert")).toHaveText(
    "Sua sessão expirou ou foi revogada. Entre novamente.",
  );
  await expect(
    page.getByRole("button", { name: "Entrar", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Senha", { exact: true })).toHaveValue("");
  await expect(page.locator(".feedback")).toBeFocused();
});
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

test("cancelled uncertain action can be reconciled without a new effect", async ({
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
  await page.getByRole("button", { name: "Aprovar proposta" }).click();
  await expect(
    page.getByRole("button", { name: "Executar no sandbox" }),
  ).toBeVisible();
  const data = await (await page.request.get("/api/cases")).json();
  const caseId = data.cases[0].id;
  execFileSync(
    process.env.PYTHON ?? "python",
    [
      "-c",
      `
import sys
from workbench.execution import SyntheticSandbox, execute_approved
from workbench.store import database_url
assert database_url().endswith('workbench_test')
class Unavailable(SyntheticSandbox):
    def lookup(self, key):
        raise TimeoutError('Injected browser recovery fixture')
try:
    execute_approved('ana', sys.argv[1], Unavailable())
except TimeoutError:
    pass
`,
      caseId,
    ],
    { timeout: 15000 },
  );
  await page.reload();
  await page.getByRole("button", { name: "Cancelar novas ações" }).click();
  await expect(
    page.getByText(
      "O resultado da tentativa anterior ainda precisa ser verificado.",
      { exact: false },
    ),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Verificar resultado anterior" })
    .click();
  await expect(
    page.getByText("Não há resultados pendentes de verificação.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Executar no sandbox" }),
  ).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByText("Não há resultados pendentes de verificação.", {
      exact: false,
    }),
  ).toBeVisible();
});
