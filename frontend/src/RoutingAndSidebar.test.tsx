import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { App } from "./App";
import * as AuthContextModule from "./context/AuthContext";

// Helper to mock auth state
const mockAuth = (isAuthenticated: boolean, email = "admin@recruitlens.local") => {
  vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
    user: isAuthenticated
      ? {
          id: "user-admin",
          email,
          full_name: "Technical Recruiter",
          role: "recruiter",
          is_active: true,
          daily_token_usage: 0,
          created_at: new Date().toISOString(),
        }
      : null,
    settings: null,
    isAuthenticated,
    isLoading: false,
    loading: false,
    jobs: [],
    activeJob: null,
    activeJobId: null,
    isDarkMode: false,
    isBlindMode: false,
    darkMode: false,
    blindMode: false,
    setActiveJob: vi.fn(),
    setActiveJobId: vi.fn(),
    setIsDarkMode: vi.fn(),
    setIsBlindMode: vi.fn(),
    refreshJobs: vi.fn().mockResolvedValue(undefined),
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn(),
    toggleBlindMode: vi.fn().mockResolvedValue(undefined),
    toggleDarkMode: vi.fn(),
    refreshProfile: vi.fn().mockResolvedValue(undefined),
  });
};

describe("Routing, Sidebar, and Access Verification Suite", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  // Test 1: Public '/' renders Home page by default without sidebar
  it("Scenario 1: Public '/' renders Home page by default without sidebar", () => {
    mockAuth(false);
    window.history.pushState({}, "", "/");
    render(<App />);

    expect(screen.getByText(/Screen resumes with evidence,/i)).toBeInTheDocument();
    expect(screen.getByText(/not black-box scores/i)).toBeInTheDocument();
    expect(screen.getByText(/Candidate #6299/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "How it Works" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log in" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign up" })).toBeInTheDocument();

    // No sidebar navigation element should exist on Home
    expect(screen.queryByRole("complementary", { name: /Main Navigation/i })).not.toBeInTheDocument();
  });

  // Test 2: Clicking logo navigates to '/' (Home)
  it("Scenario 2: Clicking logo navigates to '/' (Home)", () => {
    mockAuth(true);
    window.history.pushState({}, "", "/requisitions");
    render(<App />);

    const logoButton = screen.getAllByRole("button", { name: /Recruit Lens Home/i })[0]!;
    fireEvent.click(logoButton);

    expect(window.location.pathname).toBe("/");
    expect(screen.getByText(/Screen resumes with evidence,/i)).toBeInTheDocument();
  });

  // Test 3: Logged-in user visiting '/' sees 'Open workspace' and user email, and is NOT auto-redirected away
  it("Scenario 3: Logged-in user visiting '/' sees 'Open workspace' and user email, and is NOT auto-redirected away", () => {
    mockAuth(true, "recruiter@recruitlens.local");
    window.history.pushState({}, "", "/");
    render(<App />);

    // User is on Home page and NOT redirected
    expect(window.location.pathname).toBe("/");
    expect(screen.getByText(/Screen resumes with evidence,/i)).toBeInTheDocument();

    // Shows user email and Open workspace button
    expect(screen.getByText("recruiter@recruitlens.local")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Open workspace/i })).toBeInTheDocument();

    // Clicking Open workspace goes to /requisitions
    fireEvent.click(screen.getByRole("button", { name: /Open workspace/i }));
    expect(window.location.pathname).toBe("/requisitions");
  });

  // Test 4: Visiting protected route '/requisitions' while logged out redirects to '/login', and redirects back to '/requisitions' upon login
  it("Scenario 4: Visiting protected route '/requisitions' while logged out redirects to '/login'", async () => {
    mockAuth(false);
    window.history.pushState({}, "", "/requisitions");
    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe("/login");
      expect(window.location.search).toContain("redirect=%2Frequisitions");
    });
    expect(screen.getByRole("heading", { name: "Recruit Lens", level: 1 })).toBeInTheDocument();
  });

  // Test 5: Logged-in user visiting '/login' redirects to '/requisitions'
  it("Scenario 5: Logged-in user visiting '/login' redirects to '/requisitions'", async () => {
    mockAuth(true);
    window.history.pushState({}, "", "/login");
    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe("/requisitions");
    });
  });

  // Test 6: Public '/how-it-works' accessible without login, no sidebar
  it("Scenario 6: Public '/how-it-works' accessible without login, no sidebar", () => {
    mockAuth(false);
    window.history.pushState({}, "", "/how-it-works");
    render(<App />);

    expect(screen.getByText(/From job description to hired, in 8 steps/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Create a requisition/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Move through the pipeline and audit/i })).toBeInTheDocument();

    // No sidebar on How It Works
    expect(screen.queryByRole("complementary", { name: /Main Navigation/i })).not.toBeInTheDocument();
  });

  // Test 7: Unknown route '/invalid/path' renders 404 Not Found screen
  it("Scenario 7: Unknown route renders 404 Not Found screen", () => {
    mockAuth(true);
    window.history.pushState({}, "", "/unknown-random-route");
    render(<App />);

    expect(screen.getByText(/404 - Page Not Found/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Go to Home/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Go to Requisitions/i })).toBeInTheDocument();
  });

  // Test 8: Non-existent job '/jobs/non-existent-job' renders 404 screen
  it("Scenario 8: Non-existent job renders 404 screen", () => {
    mockAuth(true);
    window.history.pushState({}, "", "/jobs/non-existent-job");
    render(<App />);

    expect(screen.getByText(/404 - Page Not Found/i)).toBeInTheDocument();
    expect(screen.getByText(/Requisition "non-existent-job" could not be found/i)).toBeInTheDocument();
  });

  // Test 9: Candidate from another job renders 404 screen
  it("Scenario 9: Candidate from another job renders 404 screen", () => {
    mockAuth(true);
    // cand-6299 belongs to job-backend, NOT job-ml
    window.history.pushState({}, "", "/jobs/job-ml/candidates/cand-6299");
    render(<App />);

    expect(screen.getByText(/404 - Page Not Found/i)).toBeInTheDocument();
    expect(screen.getByText(/does not exist in requisition/i)).toBeInTheDocument();
  });

  // Test 10: Sidebar outside job shows Requisitions, Audit Log, Settings, How it Works, Recruiter profile, Theme toggle; no Guardrails card
  it("Scenario 10: Sidebar outside job shows required items without Guardrails card", () => {
    mockAuth(true);
    window.history.pushState({}, "", "/requisitions");
    render(<App />);

    const sidebar = screen.getByRole("complementary", { name: /Main Navigation/i });
    expect(sidebar).toBeInTheDocument();

    const sidebarScope = within(sidebar);
    expect(sidebarScope.getByRole("button", { name: /Requisitions/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /Audit Log/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /Settings/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /How it Works/i })).toBeInTheDocument();
    expect(sidebarScope.getByText("Recruiter")).toBeInTheDocument();
    expect(sidebarScope.getByText("admin@recruitlens.local")).toBeInTheDocument();

    // Theme toggle
    expect(sidebarScope.getByRole("button", { name: /Switch to Light Theme/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /Switch to Dark Theme/i })).toBeInTheDocument();

    // Guardrails card MUST NOT be present
    expect(screen.queryByText(/Guardrails/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Strict Mode Active/i)).not.toBeInTheDocument();
  });

  // Test 11: Sidebar inside job shows Back to Requisitions, Job title, Dashboard, Ranked Candidates, Add Candidates, Top Candidate, Email Center, Pipeline, Job Audit Log
  it("Scenario 11: Sidebar inside job shows all job-scoped items", () => {
    mockAuth(true);
    window.history.pushState({}, "", "/jobs/job-backend");
    render(<App />);

    const sidebar = screen.getByRole("complementary", { name: /Main Navigation/i });
    expect(sidebar).toBeInTheDocument();

    const sidebarScope = within(sidebar);
    expect(sidebarScope.getByRole("button", { name: /Back to Requisitions/i })).toBeInTheDocument();
    expect(sidebarScope.getByText("JOB WORKSPACE")).toBeInTheDocument();
    expect(sidebarScope.getByText(/REQ-BACKEND/i)).toBeInTheDocument();
    expect(sidebarScope.getByText(/Staff Backend Engineer – Distributed Systems/i)).toBeInTheDocument();

    expect(sidebarScope.getByRole("button", { name: /Job Dashboard/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /Ranked Candidates/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /Add Candidates/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /Top Candidate/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /Email Center/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /Hiring Pipeline/i })).toBeInTheDocument();
    expect(sidebarScope.getByRole("button", { name: /Job Audit Log/i })).toBeInTheDocument();
  });
});
