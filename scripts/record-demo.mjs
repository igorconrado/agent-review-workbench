import { chromium } from "@playwright/test";
import { mkdir, copyFile } from "node:fs/promises";
await mkdir(".tmp/video", { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 900 },
  recordVideo: { dir: ".tmp/video", size: { width: 1280, height: 900 } },
});
const page = await context.newPage();
await page.goto("http://127.0.0.1:3200");
await page.getByLabel("Senha", { exact: true }).fill("Synthetic-Test-Password");
await page.getByRole("button", { name: "Entrar", exact: true }).click();
await page.getByRole("button", { name: "Criar caso", exact: true }).click();
await page.getByRole("button", { name: "Reunir evidências e propor" }).click();
await page.getByRole("heading", { name: "Sinalizar reembolso" }).waitFor();
await page.screenshot({ path: ".tmp/desktop-review.png", fullPage: true });
await page.getByRole("button", { name: "Aprovar proposta" }).click();
await page.getByRole("button", { name: "Executar no sandbox" }).click();
await page.getByRole("heading", { name: "Efeito verificado" }).waitFor();
await page.reload();
await page.getByRole("heading", { name: "Efeito verificado" }).waitFor();
const video = page.video();
await context.close();
await copyFile(await video.path(), ".tmp/video/review-flow.webm");
const mobile = await browser.newContext({
  viewport: { width: 390, height: 844 },
});
const mobilePage = await mobile.newPage();
await mobilePage.goto("http://127.0.0.1:3200");
await mobilePage
  .getByLabel("Senha", { exact: true })
  .fill("Synthetic-Test-Password");
await mobilePage.getByRole("button", { name: "Entrar", exact: true }).click();
await mobilePage.getByRole("heading", { name: "Efeito verificado" }).waitFor();
await mobilePage.screenshot({ path: ".tmp/mobile-review.png", fullPage: true });
await browser.close();
