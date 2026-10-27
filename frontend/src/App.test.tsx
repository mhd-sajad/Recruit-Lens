import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App Component", () => {
  it("renders heading and system badge", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Recruit Lens", level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/OK v0.1.0/i)).toBeInTheDocument();
  });

  it("displays empty state when no candidates are processed", () => {
    render(<App />);
    expect(screen.getByText(/No candidates processed yet/i)).toBeInTheDocument();
  });

  it("has accessible labelled inputs", () => {
    render(<App />);
    const titleInput = screen.getByLabelText(/Job Title \(Required\)/i);
    expect(titleInput).toBeInTheDocument();
    expect(titleInput).toHaveAttribute("id", "job-title-input");

    const descInput = screen.getByLabelText(/Job Description & Requirements/i);
    expect(descInput).toBeInTheDocument();
  });

  it("displays error state when submitting empty job title", async () => {
    const user = userEvent.setup();
    render(<App />);
    const submitBtn = screen.getByRole("button", { name: /Screen Resumes/i });
    await user.click(submitBtn);

    expect(
      screen.getByText(/Job Title is required before starting candidate screening/i)
    ).toBeInTheDocument();
  });

  it("handles valid submission through loading to candidate list state", async () => {
    const user = userEvent.setup();
    render(<App />);
    const titleInput = screen.getByLabelText(/Job Title \(Required\)/i);
    await user.type(titleInput, "Senior Backend Engineer");

    const submitBtn = screen.getByRole("button", { name: /Screen Resumes/i });
    await user.click(submitBtn);

    expect(screen.getByRole("status")).toBeInTheDocument();

    await waitFor(
      () => {
        expect(screen.getByText(/Sample Candidate 1/i)).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });
});
