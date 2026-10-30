import React, { useState, useEffect } from "react";
import {
  Mail,
  Lock,
  CheckCircle2,
  RotateCcw,
  Send,
  ShieldCheck,
  ShieldAlert,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { INITIAL_EMAILS, type EmailDraftItem } from "../../lib/mockData";

interface EmailCenterScreenProps {
  initialCandidateCode?: string;
  onSendSuccess?: (emailId: string) => void;
}

export const EmailCenterScreen: React.FC<EmailCenterScreenProps> = ({
  onSendSuccess,
}) => {
  const { isBlindMode } = useAuth();
  const [emails, setEmails] = useState<EmailDraftItem[]>(INITIAL_EMAILS);
  const [selectedEmailType, setSelectedEmailType] = useState<"interview" | "hold" | "rejection">("interview");
  const [dryRun, setDryRun] = useState<boolean>(true);
  const [sendSuccessMessage, setSendSuccessMessage] = useState<string | null>(null);

  // Active email item
  const fallbackEmail: EmailDraftItem = INITIAL_EMAILS[0]!;
  const currentEmail = emails.find((e) => e.type === selectedEmailType) ?? fallbackEmail;

  // Current editable text
  const [editText, setEditText] = useState<string>(currentEmail.user_edit);
  const [isApproved, setIsApproved] = useState<boolean>(currentEmail.is_approved);

  // Keep state synced when switching templates
  useEffect(() => {
    setEditText(currentEmail.user_edit);
    setIsApproved(currentEmail.is_approved);
    setSendSuccessMessage(null);
  }, [selectedEmailType, currentEmail]);

  // NON-NEGOTIABLE CHECK: Rejection email MUST NEVER contain any score, percentile, or rank numbers
  const rejectionContainsScore = React.useMemo(() => {
    if (selectedEmailType !== "rejection") return false;
    // Regex checking for score patterns like "score of 95", "score: 95", "95/100", "top 5%", "ranked #1"
    const scoreRegex = /\b(score|percentile|rank|pts|points)\b.*?\d+|\b\d+\s*(\/|out of)\s*100|\b(top|rank)\s*#?\d+/i;
    return scoreRegex.test(editText);
  }, [editText, selectedEmailType]);

  // Recruiter edits draft: immediately revokes approval
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setEditText(val);
    if (isApproved) {
      setIsApproved(false);
      // Update in stored emails list
      setEmails((prev) =>
        prev.map((item) =>
          item.id === currentEmail.id
            ? { ...item, user_edit: val, is_approved: false, approved_at: undefined }
            : item
        )
      );
    }
  };

  // Step 1: Human Approval Gate
  const handleApprove = () => {
    if (rejectionContainsScore) return;
    setIsApproved(true);
    setEmails((prev) =>
      prev.map((item) =>
        item.id === currentEmail.id
          ? {
              ...item,
              user_edit: editText,
              is_approved: true,
              approved_at: new Date().toISOString(),
            }
          : item
      )
    );
  };

  // Step 2: Send Email Execution
  const handleSend = () => {
    if (!isApproved || rejectionContainsScore) return;
    setEmails((prev) =>
      prev.map((item) =>
        item.id === currentEmail.id
          ? { ...item, is_sent: true, is_dry_run: dryRun }
          : item
      )
    );
    const modeLabel = dryRun ? "Dry-run simulated delivery" : "Live delivery";
    setSendSuccessMessage(
      `✓ Successfully sent (${modeLabel}) to ${
        isBlindMode ? `Candidate #${currentEmail.to_candidate_code}` : currentEmail.to_candidate_email
      }. Immutable audit entry logged.`
    );
    if (onSendSuccess) onSendSuccess(currentEmail.id);
  };

  const handleResetToAI = () => {
    setEditText(currentEmail.ai_draft);
    setIsApproved(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[var(--border-default)] pb-4">
        <div className="flex items-center gap-2">
          <Mail className="w-5 h-5 text-blue-500" />
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Email Center
          </h1>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          AI drafts communications. Nothing is sent until a recruiter explicitly approves the final text.
        </p>
      </div>

      {/* Template Selector Tabs & Recipient Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[var(--surface)] border border-[var(--border-default)]">
        {/* Template Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
          {[
            { id: "interview" as const, label: "Interview invite" },
            { id: "hold" as const, label: "Application hold" },
            { id: "rejection" as const, label: "Score-free rejection" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setSelectedEmailType(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                selectedEmailType === tab.id
                  ? "bg-blue-600 text-white font-semibold shadow-xs"
                  : "bg-[var(--subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-default)]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Recipient info with Blind Screening Masking */}
        <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-secondary)] bg-[var(--subtle)] px-3 py-1.5 rounded-lg border border-[var(--border-default)]">
          <span className="font-sans font-medium text-[var(--text-primary)]">To:</span>
          {isBlindMode ? (
            <span className="inline-flex items-center gap-1 font-bold text-blue-500">
              <Lock className="w-3.5 h-3.5" />
              Candidate #{currentEmail.to_candidate_code} (PII Redacted)
            </span>
          ) : (
            <span className="text-[var(--text-primary)]">
              {currentEmail.to_candidate_name} &lt;{currentEmail.to_candidate_email}&gt;
            </span>
          )}
        </div>
      </div>

      {/* Safety Alert for Rejection Template score-free compliance */}
      {selectedEmailType === "rejection" && (
        <div className="flex items-start gap-2.5 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-800 dark:text-emerald-300">
          <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
          <div>
            <strong>Strict Rejection Policy Verified:</strong> Rejection communications are
            prohibited from containing scores, percentiles, or numerical rank positions to ensure
            fair, compliant adverse-action communications.
          </div>
        </div>
      )}

      {/* Violation Alert if recruiter typed a score into rejection */}
      {rejectionContainsScore && (
        <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-500/15 border border-red-500/30 text-xs text-red-700 dark:text-red-300">
          <ShieldAlert className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
          <div>
            <strong>Policy Violation Block:</strong> The rejection email draft contains a score or
            rank figure. Approval is disabled until all numerical scores are removed.
          </div>
        </div>
      )}

      {/* Side-by-Side Drafting View */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-stretch">
        {/* Left: AI-generated Draft (Read-only) */}
        <div className="flex flex-col justify-between rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-xs">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[var(--border-default)]">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                AI-Generated Draft (Read-Only)
              </span>
              <span className="text-[10px] text-blue-500 font-mono">GPT-4o Mini / Deterministic</span>
            </div>

            <div className="rounded-lg bg-[var(--canvas)] p-4 border border-[var(--border-default)] text-xs font-sans whitespace-pre-wrap leading-relaxed text-[var(--text-secondary)] min-h-[300px]">
              {currentEmail.ai_draft}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[var(--border-default)] text-[11px] text-[var(--text-secondary)] font-mono flex items-center justify-between">
            <span>Evidence used: resume match score 95, skills Go, Kafka, AWS</span>
            <button
              type="button"
              onClick={handleResetToAI}
              className="inline-flex items-center gap-1 text-blue-500 hover:underline"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset edit to this</span>
            </button>
          </div>
        </div>

        {/* Right: Editable Draft */}
        <div className="flex flex-col justify-between rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-xs">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[var(--border-default)]">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                Your Edit (Recruiter Review)
              </span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  isApproved
                    ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                    : "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                }`}
              >
                {isApproved ? "✓ Approved" : "Pending Human Approval"}
              </span>
            </div>

            <label htmlFor="email-editor" className="sr-only">
              Edit Email Body
            </label>
            <textarea
              id="email-editor"
              value={editText}
              onChange={handleTextChange}
              rows={14}
              className="w-full rounded-lg bg-[var(--canvas)] p-4 border border-[var(--border-default)] text-xs font-sans leading-relaxed text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none min-h-[300px]"
              placeholder="Review and polish candidate email text..."
            />
          </div>

          <div className="mt-4 pt-3 border-t border-[var(--border-default)] text-[11px] text-[var(--text-secondary)]">
            Editing text automatically revokes prior approval to ensure rigorous human governance.
          </div>
        </div>
      </div>

      {/* Two-Step Human Approval Gate Bar */}
      <div className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border-default)] flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Dry-run Safety Checkbox */}
        <div className="flex items-center gap-2">
          <input
            id="dry-run-checkbox"
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
            className="rounded border-[var(--border-default)] text-blue-600 focus:ring-blue-500 cursor-pointer"
          />
          <label htmlFor="dry-run-checkbox" className="text-xs font-medium text-[var(--text-primary)] cursor-pointer select-none">
            Dry-run (no live send) — Recommended for verification
          </label>
        </div>

        {/* Buttons for Step 1 & Step 2 */}
        <div className="flex items-center gap-3">
          {/* Step 1: Approve Draft */}
          <button
            type="button"
            onClick={handleApprove}
            disabled={isApproved || rejectionContainsScore}
            className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg shadow-sm transition-colors cursor-pointer ${
              isApproved
                ? "bg-[var(--subtle)] text-[var(--text-secondary)] border border-[var(--border-default)] cursor-not-allowed"
                : rejectionContainsScore
                ? "bg-red-500/20 text-red-400 border border-red-500/30 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 text-white"
            }`}
          >
            {isApproved ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>1. Draft Approved</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                <span>1. Approve Draft</span>
              </>
            )}
          </button>

          {/* Step 2: Send Email (Locked until approved) */}
          <button
            type="button"
            onClick={handleSend}
            disabled={!isApproved || rejectionContainsScore}
            className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg shadow-sm transition-colors cursor-pointer ${
              !isApproved || rejectionContainsScore
                ? "bg-[var(--subtle)] text-[var(--text-secondary)] border border-[var(--border-default)] opacity-60 cursor-not-allowed"
                : "bg-emerald-600 hover:bg-emerald-700 text-white"
            }`}
          >
            {isApproved ? (
              <>
                <Send className="w-4 h-4" />
                <span>2. Send Email</span>
              </>
            ) : (
              <>
                <Lock className="w-4 h-4 text-[var(--text-secondary)]" />
                <span>2. Send Email (Locked)</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Success Notification */}
      {sendSuccessMessage && (
        <div
          role="status"
          className="p-3.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-xs font-medium text-emerald-700 dark:text-emerald-300 flex items-center gap-2"
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
          <span>{sendSuccessMessage}</span>
        </div>
      )}
    </div>
  );
};
