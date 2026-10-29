import React, { useState } from "react";
import { Modal } from "../common/Modal";
import { api } from "../../lib/api";
import { Mail, AlertCircle, CheckCircle2 } from "lucide-react";

interface EmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidateName: string;
  candidateEmail?: string;
  evaluationId: string;
}

export const EmailModal: React.FC<EmailModalProps> = ({
  isOpen,
  onClose,
  candidateName,
  candidateEmail = "candidate@example.com",
  evaluationId,
}) => {
  const [templateType, setTemplateType] = useState<"interview" | "rejection" | "followup">("interview");
  const [subject, setSubject] = useState(`Interview Invitation - Recruit Lens`);
  const [body, setBody] = useState(
    `Dear ${candidateName},\n\nWe were impressed by your background and experience in backend systems. We would love to invite you to a technical interview for our engineering team.\n\nPlease let us know your availability over the coming days.\n\nBest regards,\nRecruiting Team`
  );
  const [isEdited, setIsEdited] = useState(false);
  const [isDryRun, setIsDryRun] = useState(true);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleTemplateChange = (type: "interview" | "rejection" | "followup") => {
    setTemplateType(type);
    setIsEdited(false);
    if (type === "interview") {
      setSubject(`Interview Invitation - Recruit Lens`);
      setBody(
        `Dear ${candidateName},\n\nWe were impressed by your background and experience in backend systems. We would love to invite you to a technical interview for our engineering team.\n\nPlease let us know your availability over the coming days.\n\nBest regards,\nRecruiting Team`
      );
    } else if (type === "rejection") {
      setSubject(`Application Update - Recruit Lens`);
      setBody(
        `Dear ${candidateName},\n\nThank you for taking the time to speak with us. While your background is impressive, we have chosen to proceed with candidates whose skills more closely align with our current focus.\n\nWe wish you all the best in your search.\n\nBest regards,\nRecruiting Team`
      );
    } else {
      setSubject(`Following up on your application - Recruit Lens`);
      setBody(
        `Dear ${candidateName},\n\nWe are currently reviewing applications and will provide an update on your candidacy shortly.\n\nBest regards,\nRecruiting Team`
      );
    }
  };

  const handleSend = async () => {
    setError(null);
    setLoading(true);
    try {
      await api.sendEmail({
        evaluation_id: evaluationId,
        recipient: candidateEmail,
        subject: subject.trim(),
        body: body.trim(),
        dry_run: isDryRun,
      });

      setSuccessMessage(
        isDryRun
          ? `[DRY-RUN SUCCESS] Email simulated to ${candidateEmail}. No actual SMTP message dispatched.`
          : `Email successfully dispatched to ${candidateEmail} via SMTP.`
      );
      setShowConfirm(false);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || "Failed to dispatch email.");
      } else {
        setError("Failed to dispatch email.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Modal
        isOpen={isOpen && !showConfirm}
        onClose={onClose}
        title="Email Communication Center"
        description={`Draft, edit, and send communications to candidate: ${candidateName}`}
        maxWidth="2xl"
        footer={
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <span
                className={`text-xs px-2 py-0.5 rounded font-mono font-medium ${
                  isDryRun
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300"
                    : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                }`}
              >
                {isDryRun ? "MODE: DRY-RUN (Safe)" : "MODE: LIVE DISPATCH"}
              </span>
              <button
                type="button"
                onClick={() => setIsDryRun(!isDryRun)}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                Switch to {isDryRun ? "Live" : "Dry-run"}
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => setShowConfirm(true)}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition flex items-center gap-1.5"
              >
                <Mail className="w-3.5 h-3.5" />
                <span>Review & Dispatch →</span>
              </button>
            </div>
          </div>
        }
      >
        <div className="space-y-4">
          {successMessage && (
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-200 rounded-lg text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>{successMessage}</span>
            </div>
          )}

          {error && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 rounded-lg text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Template Selector & Status */}
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-500 mr-1">Template:</span>
              <button
                type="button"
                onClick={() => handleTemplateChange("interview")}
                className={`px-2.5 py-1 text-xs rounded-lg ${
                  templateType === "interview"
                    ? "bg-blue-50 text-blue-700 font-semibold"
                    : "text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                Interview
              </button>
              <button
                type="button"
                onClick={() => handleTemplateChange("rejection")}
                className={`px-2.5 py-1 text-xs rounded-lg ${
                  templateType === "rejection"
                    ? "bg-blue-50 text-blue-700 font-semibold"
                    : "text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                Rejection
              </button>
              <button
                type="button"
                onClick={() => handleTemplateChange("followup")}
                className={`px-2.5 py-1 text-xs rounded-lg ${
                  templateType === "followup"
                    ? "bg-blue-50 text-blue-700 font-semibold"
                    : "text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                Follow-Up
              </button>
            </div>

            <span className="text-[11px] font-mono text-slate-400">
              Status: {isEdited ? "Custom Edited" : "Original Template"}
            </span>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="email-recipient-field"
              className="text-xs font-semibold text-slate-700 dark:text-slate-300"
            >
              Recipient
            </label>
            <input
              id="email-recipient-field"
              type="email"
              disabled
              value={candidateEmail}
              className="w-full text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-500 font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="email-subject-field"
              className="text-xs font-semibold text-slate-700 dark:text-slate-300"
            >
              Subject
            </label>
            <input
              id="email-subject-field"
              type="text"
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value);
                setIsEdited(true);
              }}
              className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="email-body-field"
              className="text-xs font-semibold text-slate-700 dark:text-slate-300"
            >
              Message Body
            </label>
            <textarea
              id="email-body-field"
              rows={8}
              value={body}
              onChange={(e) => {
                setBody(e.target.value);
                setIsEdited(true);
              }}
              className="w-full text-xs p-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 leading-relaxed font-sans"
            />
          </div>
        </div>
      </Modal>

      {/* Confirmation Step Dialog (SPEC Requirement: No email sent without explicit human confirmation) */}
      <Modal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        title="Confirm Email Dispatch"
        description="Verify delivery details before initiating SMTP dispatch."
        maxWidth="md"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <button
              type="button"
              onClick={() => setShowConfirm(false)}
              className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400"
            >
              Back to Edit
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={handleSend}
              className={`px-4 py-1.5 text-xs font-semibold text-white rounded-lg shadow transition flex items-center gap-1.5 ${
                isDryRun
                  ? "bg-amber-600 hover:bg-amber-700"
                  : "bg-emerald-600 hover:bg-emerald-700"
              }`}
            >
              {loading ? (
                <span>Dispatching...</span>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Confirm and {isDryRun ? "Simulate Dry-Run" : "Send Live Email"}</span>
                </>
              )}
            </button>
          </div>
        }
      >
        <div className="space-y-3 text-xs text-slate-700 dark:text-slate-300">
          <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 space-y-1">
            <div><strong>Recipient:</strong> {candidateEmail}</div>
            <div><strong>Subject:</strong> {subject}</div>
            <div><strong>Mode:</strong> {isDryRun ? "DRY-RUN (Safe Simulation)" : "LIVE DISPATCH"}</div>
          </div>
          <p className="text-slate-500 text-[11px]">
            {isDryRun
              ? "This simulation logs the email generation to the audit trail without transmitting real network packets."
              : "Live email will be delivered to the recipient address via configured SMTP gateway."}
          </p>
        </div>
      </Modal>
    </>
  );
};
