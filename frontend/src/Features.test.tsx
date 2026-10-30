import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RankedTableScreen } from "./components/screens/RankedTableScreen";
import { CandidateDossierScreen } from "./components/screens/CandidateDossierScreen";
import { EmailCenterScreen } from "./components/screens/EmailCenterScreen";
import { INITIAL_JOBS, INITIAL_CANDIDATES, SAMPLE_DOSSIER_6299 } from "./lib/mockData";
import * as AuthContextModule from "./context/AuthContext";

// Mock useAuth helper
const mockUseAuth = (isBlindMode: boolean) => {
  vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
    user: {
      id: "user-1",
      email: "recruiter@recruitlens.local",
      full_name: "Technical Recruiter",
      role: "recruiter",
      is_active: true,
      daily_token_usage: 0,
      created_at: new Date().toISOString(),
    },
    settings: null,
    isAuthenticated: true,
    isLoading: false,
    loading: false,
    jobs: [],
    activeJob: null,
    activeJobId: null,
    isDarkMode: true,
    isBlindMode,
    darkMode: true,
    blindMode: isBlindMode,
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

describe("Feature 1: What-If Simulator", () => {
  it("displays hypothetical simulation disclaimer and correctly computes score deltas", () => {
    mockUseAuth(false);
    render(
      <CandidateDossierScreen
        dossier={SAMPLE_DOSSIER_6299}
        candidatesList={INITIAL_CANDIDATES}
        onBack={vi.fn()}
        onNextCandidate={vi.fn()}
        onOpenEmail={vi.fn()}
      />
    );

    // Switch to Simulator & Questions tab (for responsive mobile/desktop testing)
    const prepTab = screen.getByRole("button", { name: /Simulator & Questions/i });
    fireEvent.click(prepTab);

    // 1. Mandatory disclaimer check
    expect(screen.getByText(/Hypothetical simulation/i)).toBeInTheDocument();
    expect(screen.getByText(/Never saved to candidate record/i)).toBeInTheDocument();

    // 2. Base score check (95)
    expect(screen.getByText("95 → 95")).toBeInTheDocument();
    expect(screen.getByText("No delta")).toBeInTheDocument();

    // 3. Toggle Cassandra checkbox (+5 pts)
    const cassandraCheckbox = screen.getByLabelText(/Add Cassandra experience \(\+5 pts\)/i);
    fireEvent.click(cassandraCheckbox);

    // Score becomes 95 -> 100 with delta indicator
    expect(screen.getByText("95 → 100")).toBeInTheDocument();
    expect(screen.getByText(/▲ \+5/i)).toBeInTheDocument();

    // 4. Reset simulation button
    const resetBtn = screen.getByRole("button", { name: /Reset simulation/i });
    expect(resetBtn).toBeInTheDocument();
    fireEvent.click(resetBtn);

    // Reverts to base score
    expect(screen.getByText("95 → 95")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reset simulation/i })).not.toBeInTheDocument();
  });
});

describe("Feature 2: Citation Highlighting & Verbatim Evidence", () => {
  it("renders citation pills and updates active state on click with screen reader announcement", () => {
    mockUseAuth(false);
    render(
      <CandidateDossierScreen
        dossier={SAMPLE_DOSSIER_6299}
        candidatesList={INITIAL_CANDIDATES}
        onBack={vi.fn()}
        onNextCandidate={vi.fn()}
        onOpenEmail={vi.fn()}
      />
    );

    // Ensure Evidence tab is active
    const evidenceTab = screen.getByRole("button", { name: /AI Briefing & Evidence/i });
    fireEvent.click(evidenceTab);

    // 1. Citation pills exist in AI Recruiter Briefing
    const pillC01 = screen.getByLabelText("View source evidence citation c_01");
    const pillC02 = screen.getByLabelText("View source evidence citation c_02");
    expect(pillC01).toBeInTheDocument();
    expect(pillC02).toBeInTheDocument();

    // 2. Verbatim evidence viewer displays character offsets
    expect(screen.getByText(/Chars: 20–187/i)).toBeInTheDocument();

    // 3. Clicking citation pill c_02 triggers focus
    fireEvent.click(pillC02);
    expect(screen.getByText(/Active: \[c_02\]/i)).toBeInTheDocument();
  });
});

describe("Feature 3: Blind-Mode Masking", () => {
  it("redacts candidate name, email, and PII to 'Candidate #NNNN' when Blind Mode is ON", () => {
    mockUseAuth(true); // Blind Mode = true
    render(
      <RankedTableScreen
        job={INITIAL_JOBS[0]!}
        candidates={INITIAL_CANDIDATES}
        onSelectCandidate={vi.fn()}
        onOpenEmail={vi.fn()}
        onExportAudit={vi.fn()}
        onNavigateRequisitions={vi.fn()}
      />
    );

    // Top candidate code is "6299"
    expect(screen.getByText("Candidate #6299")).toBeInTheDocument();
    // Candidate name "Alex Rivera" and email MUST NOT be rendered
    expect(screen.queryByText("Alex Rivera")).not.toBeInTheDocument();
    expect(screen.queryByText("alex.rivera@engineering.io")).not.toBeInTheDocument();
  });

  it("reveals candidate name when Blind Mode is OFF", () => {
    mockUseAuth(false); // Blind Mode = false
    render(
      <RankedTableScreen
        job={INITIAL_JOBS[0]!}
        candidates={INITIAL_CANDIDATES}
        onSelectCandidate={vi.fn()}
        onOpenEmail={vi.fn()}
        onExportAudit={vi.fn()}
        onNavigateRequisitions={vi.fn()}
      />
    );

    expect(screen.getByText("Alex Rivera")).toBeInTheDocument();
    expect(screen.getByText(/alex\.rivera@engineering\.io/i)).toBeInTheDocument();
  });
});

describe("Feature 4: Email Two-Step Approval Gate & Score-Free Rejection", () => {
  it("enforces two-step human gate: Step 2 Send is locked until Step 1 Approve is clicked; edits revoke approval", () => {
    mockUseAuth(false);
    render(<EmailCenterScreen />);

    // Initial state: Step 2 Send button is locked and disabled
    const sendButton = screen.getByRole("button", { name: /2\. Send Email/i });
    expect(sendButton).toBeDisabled();
    expect(screen.getByText(/2\. Send Email \(Locked\)/i)).toBeInTheDocument();

    // Step 1: Click Approve Draft
    const approveButton = screen.getByRole("button", { name: /1\. Approve Draft/i });
    fireEvent.click(approveButton);

    // Send button unlocks
    expect(screen.getByRole("button", { name: /2\. Send Email/i })).toBeEnabled();
    expect(screen.getByText("✓ Approved")).toBeInTheDocument();

    // Edit textarea -> Approval MUST be revoked
    const textarea = screen.getByLabelText(/Edit Email Body/i);
    fireEvent.change(textarea, { target: { value: "Modified invitation text." } });

    // Send button is locked again!
    expect(screen.getByRole("button", { name: /2\. Send Email/i })).toBeDisabled();
    expect(screen.getByText(/Pending Human Approval/i)).toBeInTheDocument();
  });

  it("strictly forbids numerical scores or rankings in adverse-action rejection drafts", () => {
    mockUseAuth(false);
    render(<EmailCenterScreen />);

    // Switch to Score-free rejection tab
    const rejectionTab = screen.getByRole("button", { name: /Score-free rejection/i });
    fireEvent.click(rejectionTab);

    // Policy banner must be present
    expect(screen.getByText(/Strict Rejection Policy Verified/i)).toBeInTheDocument();

    const textarea = screen.getByLabelText(/Edit Email Body/i) as HTMLTextAreaElement;
    // Check that initial draft does NOT contain scores, points, or rank numbers
    const scoreRegex = /\b(score|percentile|rank|pts|points)\b.*?\d+|\b\d+\s*(\/|out of)\s*100|\b(top|rank)\s*#?\d+/i;
    expect(scoreRegex.test(textarea.value)).toBe(false);

    // If user attempts to inject a score into the rejection email
    fireEvent.change(textarea, {
      target: { value: "We regret to inform you that your score was 42/100." },
    });

    // Policy violation banner triggers and approval is blocked
    expect(screen.getByText(/Policy Violation Block/i)).toBeInTheDocument();
    const approveButton = screen.getByRole("button", { name: /1\. Approve Draft/i });
    expect(approveButton).toBeDisabled();
  });
});

describe("Feature 5: Employer-Name Suppression", () => {
  it("ensures candidate lists and tables NEVER display employer or company names", () => {
    mockUseAuth(false);
    render(
      <RankedTableScreen
        job={INITIAL_JOBS[0]!}
        candidates={INITIAL_CANDIDATES}
        onSelectCandidate={vi.fn()}
        onOpenEmail={vi.fn()}
        onExportAudit={vi.fn()}
        onNavigateRequisitions={vi.fn()}
      />
    );

    // Table header explicitly states "Title only"
    expect(
      screen.getByRole("columnheader", { name: /Most recent role \(Title only\)/i })
    ).toBeInTheDocument();

    // Prestige banner explicitly reminds user
    expect(screen.getByText(/Prestige Bias Suppression Active/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Employer and company names are suppressed by design/i)
    ).toBeInTheDocument();

    // Common tech employer names must NOT appear
    const prohibitedCompanies = [
      "Google",
      "Amazon",
      "Meta",
      "Apple",
      "Netflix",
      "Microsoft",
      "Stripe",
      "Uber",
      "Airbnb",
      "Coinbase",
    ];

    prohibitedCompanies.forEach((company) => {
      expect(screen.queryByText(new RegExp(`\\b${company}\\b`, "i"))).not.toBeInTheDocument();
    });
  });
});
