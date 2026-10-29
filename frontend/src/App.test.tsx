import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { Badge } from "./components/common/Badge";
import { Modal } from "./components/common/Modal";
import { Drawer } from "./components/common/Drawer";
import { LoadingState, EmptyState, ErrorState } from "./components/common/StateViews";

describe("App & Login Screen", () => {
  it("renders heading and demo credentials banner when logged out", () => {
    localStorage.clear();
    render(<App />);
    expect(screen.getByRole("heading", { name: "Recruit Lens", level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/Demo Evaluation Credentials:/i)).toBeInTheDocument();
    expect(screen.getByText(/admin@recruitlens.local/i)).toBeInTheDocument();
  });

  it("renders accessible email and password inputs with labels", () => {
    localStorage.clear();
    render(<App />);
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign In to Recruiter Portal/i })).toBeInTheDocument();
  });
});

describe("UI Components", () => {
  it("renders Badge variants correctly", () => {
    const { rerender } = render(<Badge variant="tier" value="strong_fit" />);
    expect(screen.getByText("Strong Fit")).toBeInTheDocument();

    rerender(<Badge variant="tier" value="abstain" />);
    expect(screen.getByText("Insufficient Info")).toBeInTheDocument();

    rerender(<Badge variant="stage" value="interview" />);
    expect(screen.getByText("Interview")).toBeInTheDocument();

    rerender(<Badge variant="source" value="template" />);
    expect(screen.getByText("Template")).toBeInTheDocument();
  });

  it("renders Modal and handles close on ESC", () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose} title="Test Modal">
        <div>Modal Body Content</div>
      </Modal>
    );

    expect(screen.getByText("Test Modal")).toBeInTheDocument();
    expect(screen.getByText("Modal Body Content")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("renders Grounding Drawer with evidence items", () => {
    const onClose = vi.fn();
    const evidence = [
      {
        id: "ev-1",
        chunk_index: 2,
        section: "experience",
        text: "Built async services with FastAPI.",
        relevance_score: 0.94,
      },
    ];

    render(
      <Drawer
        isOpen={true}
        onClose={onClose}
        candidateName="Test Candidate"
        evidence={evidence}
      />
    );

    expect(screen.getByText(/Grounding Evidence & Citations/i)).toBeInTheDocument();
    expect(screen.getByText(/Built async services with FastAPI/i)).toBeInTheDocument();
    expect(screen.getByText(/Chunk #2/i)).toBeInTheDocument();
  });

  it("renders StateViews: LoadingState, EmptyState, ErrorState", () => {
    const { rerender } = render(<LoadingState message="Fetching data..." />);
    expect(screen.getByText("Fetching data...")).toBeInTheDocument();

    rerender(
      <EmptyState
        title="No candidates found"
        description="Try clearing your filters."
        action={{ label: "Reset", onClick: vi.fn() }}
      />
    );
    expect(screen.getByText("No candidates found")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset" })).toBeInTheDocument();

    rerender(
      <ErrorState
        title="Failed to load"
        message="Network error"
        onRetry={vi.fn()}
      />
    );
    expect(screen.getByText("Failed to load")).toBeInTheDocument();
    expect(screen.getByText("Network error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Try Again/i })).toBeInTheDocument();
  });
});
