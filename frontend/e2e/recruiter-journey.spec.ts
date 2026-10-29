import { test, expect } from "@playwright/test";
import path from "path";

import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.resolve(__dirname, "../../docs/screenshots");

test.describe("Recruiter Journey End-to-End Suite", () => {
  test("complete 17-screen journey: login, screening, blind mode, evidence drawer, what-if, and analytics", async ({
    page,
  }) => {
    page.on("console", (msg) => console.log("BROWSER CONSOLE:", msg.type(), msg.text()));
    page.on("pageerror", (err) => console.log("BROWSER ERROR:", err.message));

    // 1. Visit App & Login Screen
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Recruit Lens", level: 1 })).toBeVisible();
    await expect(page.getByText(/Demo Evaluation Credentials:/i)).toBeVisible();

    // Capture Screen 1: Login Screen
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "01_login_screen.png"),
      fullPage: true,
    });

    // Sign in using demo credentials
    await page.getByRole("button", { name: /Sign In to Recruiter Portal/i }).click();

    // 2. Dashboard Screen
    await expect(page.getByRole("heading", { name: "Recruiter Command Center" })).toBeVisible();
    await expect(page.getByText("Active Requisitions")).toBeVisible();

    // Capture Screen 2: Dashboard Command Center
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "02_dashboard_command_center.png"),
      fullPage: true,
    });

    // 3. Navigate to Candidates Ranked Table
    await page.getByRole("button", { name: "Candidates", exact: true }).click();
    await expect(page.getByRole("table")).toBeVisible();

    // Toggle Blind Review Mode
    await page.getByRole("button", { name: /Toggle Blind Mode/i }).click();
    await expect(page.getByText(/Candidate #/i).first()).toBeVisible();

    // Capture Screen 3: Ranked Candidates Table in Blind Mode
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "03_ranked_table_blind_mode.png"),
      fullPage: true,
    });

    // 4. Select Candidate & View Candidate Detail Screen
    await page.locator("tbody tr").first().click();
    await expect(page.getByRole("heading", { name: /Candidate #/i })).toBeVisible();
    await expect(page.getByText(/Fit Score & Deterministic Factors/i)).toBeVisible();
    await expect(page.getByText(/Verified Experience Timeline/i)).toBeVisible();

    // Open What-If Simulator
    await page.getByRole("button", { name: "Open" }).click();
    await expect(page.getByText("Experience Weight Multiplier")).toBeVisible();

    // Open Cited Evidence Drawer
    await page.getByRole("button", { name: /View Cited Evidence Chunks/i }).click();
    await expect(page.getByRole("dialog", { name: "Cited Explanation Evidence" })).toBeVisible();

    // Capture Screen 4: Candidate Detail with What-If & Grounding Drawer
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "04_candidate_detail_evidence.png"),
      fullPage: true,
    });

    // Close Evidence Drawer
    await page.getByRole("button", { name: /Close evidence panel/i }).click();

    // 5. Open Tailored Interview Questions Rubric
    await page.getByRole("button", { name: /Interview Rubric/i }).click();
    await expect(page.getByText("Tailored Interview Questions")).toBeVisible();
    await expect(page.getByText(/Architecture & Concurrency/i)).toBeVisible();

    // Capture Screen 5: Tailored Interview Questions
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "05_interview_rubric.png"),
      fullPage: true,
    });

    // Close Rubric
    await page.getByRole("button", { name: "Done" }).click();

    // 6. Navigate to Analytics Reports Screen
    await page.getByRole("button", { name: "Reports", exact: true }).click();
    await expect(page.getByText("Recruitment Analytics & Evaluation Report")).toBeVisible();
    await expect(page.getByText("System-Recruiter Agreement")).toBeVisible();

    // Capture Screen 6: Reports & Analytics
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "06_reports_and_analytics.png"),
      fullPage: true,
    });
  });
});
