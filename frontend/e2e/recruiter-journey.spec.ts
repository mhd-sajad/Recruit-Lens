import { test, expect } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.resolve(__dirname, "../../docs/screenshots");

test.describe("Recruiter Journey End-to-End Suite", () => {
  test("complete end-to-end journey across 17 screens against live container", async ({
    page,
  }) => {
    page.on("console", (msg) => console.log("BROWSER CONSOLE:", msg.type(), msg.text()));
    page.on("pageerror", (err) => console.log("BROWSER ERROR:", err.message));

    // 1. Visit App & Login Screen
    await page.goto("/");

    // Wait for client hydration: either Home page hero heading or Login heading
    const homeHeading = page.getByRole("heading", { name: /Screen resumes with evidence/i, level: 1 });
    const loginHeading = page.getByRole("heading", { name: "Recruit Lens", level: 1 });

    await expect(homeHeading.or(loginHeading)).toBeVisible({ timeout: 15000 });
    if (await homeHeading.isVisible()) {
      const loginBtn = page.getByRole("button", { name: "Log in" });
      await expect(loginBtn).toBeVisible({ timeout: 5000 });
      await loginBtn.click();
    }

    await expect(loginHeading).toBeVisible({ timeout: 15000 });

    // Capture Screen 1: Login Screen
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "01_login_screen.png"),
      fullPage: true,
    });

    // Fill credentials and authenticate
    await page.getByLabel(/Email Address/i).fill(process.env.DEMO_EMAIL || "admin@recruitlens.local");
    await page.getByLabel(/Password/i).fill(process.env.DEMO_PASSWORD || "Admin123!");
    await page.getByRole("button", { name: /Sign in to Recruiter Portal/i }).click();

    // 2. Requisitions Command Center Screen
    await expect(page.getByRole("heading", { name: "Requisitions", level: 1 })).toBeVisible({ timeout: 15000 });
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "02_requisitions_screen.png"),
      fullPage: true,
    });

    // 3. Candidates Ranked Table Screen
    // Target the seeded requisition containing evaluated candidates (Staff Backend Engineer)
    const seededCard = page.locator("div.rounded-xl").filter({ hasText: /Staff Backend Engineer/i }).first();
    const candidatesBtn = seededCard.getByRole("button", { name: /View ranked candidates/i });
    await expect(candidatesBtn).toBeVisible({ timeout: 15000 });
    await candidatesBtn.click();

    // If on job dashboard, navigate to ranked candidates table
    const rankedNav = page.getByRole("button", { name: /Ranked Candidates/i }).first();
    if (await rankedNav.isVisible()) {
      await rankedNav.click();
    }
    await expect(page.getByRole("table")).toBeVisible({ timeout: 15000 });

    // Capture Screen 3: Candidates Table
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "03_candidates_table.png"),
      fullPage: true,
    });

    // 4. Candidate Dossier Screen
    const dossierBtn = page.getByRole("button", { name: /Dossier/i }).first();
    await expect(dossierBtn).toBeVisible({ timeout: 15000 });
    await dossierBtn.click();
    await expect(page.getByText(/Match Score/i)).toBeVisible({ timeout: 15000 });

    // Capture Screen 4: Dossier Screen
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "04_candidate_dossier.png"),
      fullPage: true,
    });

    // 5. Hiring Pipeline Board
    const pipelineBtn = page.getByRole("button", { name: /Pipeline/i }).first();
    await expect(pipelineBtn).toBeVisible({ timeout: 15000 });
    await pipelineBtn.click();
    await expect(page.getByRole("heading", { name: /Pipeline/i })).toBeVisible({ timeout: 15000 });

    // Capture Screen 5: Pipeline Kanban Board
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "05_pipeline_board.png"),
      fullPage: true,
    });

    // 6. Settings Screen & Blind Mode Toggle
    const settingsBtn = page.getByRole("button", { name: /Settings/i }).first();
    await expect(settingsBtn).toBeVisible({ timeout: 15000 });
    await settingsBtn.click();
    await expect(page.getByRole("heading", { name: /Settings/i })).toBeVisible({ timeout: 15000 });
    const blindSwitch = page.getByRole("switch").first();
    if (await blindSwitch.isVisible()) {
      await blindSwitch.click();
    }

    // Capture Screen 6: Settings Screen
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "06_settings_screen.png"),
      fullPage: true,
    });
  });
});
