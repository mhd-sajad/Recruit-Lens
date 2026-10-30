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
    await page.getByRole("button", { name: "Candidates", exact: true }).click();
    await expect(page.getByRole("table")).toBeVisible({ timeout: 10000 });

    // Capture Screen 3: Candidates Table (Normal)
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "03_candidates_table.png"),
      fullPage: true,
    });

    // Toggle Blind Mode
    await page.getByRole("switch").click();
    await expect(page.getByText(/Candidate #/i).first()).toBeVisible({ timeout: 5000 });

    // Capture Screen 4: Ranked Table in Blind Mode
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "04_ranked_table_blind_mode.png"),
      fullPage: true,
    });

    // 4. Candidate Dossier Screen
    await page.getByRole("button", { name: "Dossier", exact: true }).click();
    await expect(page.getByText(/Match Score/i)).toBeVisible({ timeout: 10000 });

    // Capture Screen 5: Dossier Screen
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "05_candidate_dossier.png"),
      fullPage: true,
    });

    // 5. Hiring Pipeline Board
    await page.getByRole("button", { name: "Pipeline", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Pipeline Board" })).toBeVisible({ timeout: 10000 });

    // Capture Screen 6: Pipeline Kanban Board
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "06_pipeline_board.png"),
      fullPage: true,
    });
  });
});
