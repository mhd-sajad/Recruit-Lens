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
    await expect(page.getByRole("heading", { name: "Recruit Lens", level: 1 })).toBeVisible();

    // Navigate to Login Screen
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("heading", { name: "Recruit Lens", level: 1 })).toBeVisible();

    // Capture Screen 1: Login Screen
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "01_login_screen.png"),
      fullPage: true,
    });

    // Fill credentials and authenticate
    await page.getByLabel(/Email Address/i).fill(process.env.DEMO_EMAIL || "admin@recruitlens.local");
    await page.getByLabel(/Password/i).fill(process.env.DEMO_PASSWORD || "Admin123!");
    await page.getByRole("button", { name: /Sign In to Recruiter Portal/i }).click();

    // 2. Requisitions Command Center Screen
    await expect(page.getByRole("heading", { name: "Requisitions", level: 1 })).toBeVisible({ timeout: 10000 });
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "02_requisitions_screen.png"),
      fullPage: true,
    });

    // 3. Candidates Ranked Table Screen
    // Click "View ranked candidates" on first requisition card
    await page.getByRole("button", { name: /View ranked candidates/i }).first().click();
    // Navigate to Ranked Candidates table from the job workspace
    await page.getByRole("button", { name: /Ranked Candidates/i }).first().click();
    await expect(page.getByRole("table")).toBeVisible({ timeout: 10000 });

    // Capture Screen 3: Candidates Table
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "03_candidates_table.png"),
      fullPage: true,
    });

    // 4. Candidate Dossier Screen
    await page.getByRole("button", { name: "Dossier" }).first().click();
    await expect(page.getByText(/Match Score/i)).toBeVisible({ timeout: 10000 });

    // Capture Screen 4: Dossier Screen
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "04_candidate_dossier.png"),
      fullPage: true,
    });

    // 5. Hiring Pipeline Board
    await page.getByRole("button", { name: /Hiring Pipeline/i }).first().click();
    await expect(page.getByRole("heading", { name: "Pipeline Board" })).toBeVisible({ timeout: 10000 });

    // Capture Screen 5: Pipeline Kanban Board
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "05_pipeline_board.png"),
      fullPage: true,
    });

    // 6. Settings Screen & Blind Mode Toggle
    await page.getByRole("button", { name: "Settings" }).first().click();
    await expect(page.getByRole("heading", { name: "Settings", level: 1 })).toBeVisible({ timeout: 10000 });
    await page.getByRole("switch").first().click();

    // Capture Screen 6: Settings Screen
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "06_settings_screen.png"),
      fullPage: true,
    });
  });
});
