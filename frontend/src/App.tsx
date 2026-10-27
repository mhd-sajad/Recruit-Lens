import React, { useState } from "react";

interface SystemHealth {
  status: string;
  version: string;
  environment: string;
}

export const App: React.FC = () => {
  const [jobTitle, setJobTitle] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<string[]>([]);
  const [systemHealth] = useState<SystemHealth>({
    status: "ok",
    version: "0.1.0",
    environment: "development",
  });

  const handleSimulateBatch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobTitle.trim()) {
      setError("Job Title is required before starting candidate screening.");
      return;
    }

    setError(null);
    setLoading(true);

    setTimeout(() => {
      setLoading(false);
      setCandidates(["Sample Candidate 1 (Fit: Strong Fit)"]);
    }, 400);
  };

  const handleClear = () => {
    setJobTitle("");
    setJobDescription("");
    setCandidates([]);
    setError(null);
  };

  return (
    <div className="container">
      <header className="header" role="banner">
        <div>
          <h1>Recruit Lens</h1>
          <p>Explainable, Evidence-Grounded AI Recruiter Platform</p>
        </div>
        <div className="badge" aria-label="System status">
          <span>●</span>
          <span>
            {systemHealth.status.toUpperCase()} v{systemHealth.version}
          </span>
        </div>
      </header>

      <main role="main">
        {error && (
          <div className="state-error" role="alert" aria-live="assertive">
            <strong>Error:</strong> {error}
          </div>
        )}

        <section className="card" aria-labelledby="screening-heading">
          <h2 id="screening-heading" style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>
            Create Job Requirement
          </h2>

          <form onSubmit={handleSimulateBatch}>
            <div className="form-group">
              <label htmlFor="job-title-input">Job Title (Required)</label>
              <input
                id="job-title-input"
                name="jobTitle"
                type="text"
                placeholder="e.g. Senior Machine Learning Engineer"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                aria-required="true"
              />
            </div>

            <div className="form-group">
              <label htmlFor="job-desc-input">Job Description & Requirements</label>
              <textarea
                id="job-desc-input"
                name="jobDescription"
                rows={4}
                placeholder="Paste job description requirements, must-have skills, and qualifications..."
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
              <button
                type="submit"
                id="submit-job-btn"
                disabled={loading}
                aria-busy={loading}
              >
                {loading ? "Processing Batch..." : "Screen Resumes"}
              </button>

              <button
                type="button"
                id="clear-btn"
                onClick={handleClear}
                style={{ backgroundColor: "transparent", color: "var(--text-secondary)", border: "1px solid var(--border-color)" }}
              >
                Reset
              </button>
            </div>
          </form>
        </section>

        <section className="card" aria-labelledby="candidates-heading">
          <h2 id="candidates-heading" style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>
            Screened Candidates
          </h2>

          {loading && (
            <div className="state-loading" role="status" aria-live="polite">
              <span>Scanning resumes and ranking evidence chunks...</span>
            </div>
          )}

          {!loading && candidates.length === 0 && (
            <div className="state-empty" id="empty-state-notice">
              <p>No candidates processed yet.</p>
              <p style={{ fontSize: "0.85rem", marginTop: "0.35rem" }}>
                Enter job requirements above and submit to view ranked candidates and cited evidence.
              </p>
            </div>
          )}

          {!loading && candidates.length > 0 && (
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {candidates.map((cand, idx) => (
                <li
                  key={idx}
                  style={{
                    padding: "0.75rem 1rem",
                    backgroundColor: "var(--bg-input)",
                    borderRadius: "0.375rem",
                    border: "1px solid var(--border-color)",
                  }}
                >
                  {cand}
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
};
