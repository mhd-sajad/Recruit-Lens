import React, { useState } from "react";
import { Modal } from "../common/Modal";
import { api } from "../../lib/api";
import { EvaluationStage } from "../../types/api";
import { AlertCircle, CheckCircle2 } from "lucide-react";

interface DecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  evaluationId: string;
  candidateName: string;
  currentStage: string;
  onSuccess: () => void;
}

export const DecisionModal: React.FC<DecisionModalProps> = ({
  isOpen,
  onClose,
  evaluationId,
  candidateName,
  currentStage,
  onSuccess,
}) => {
  const [stage, setStage] = useState<string>(
    currentStage === "new" ? "shortlisted" : currentStage
  );
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!notes.trim()) {
      setError("A decision note is required for the immutable audit trail.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await api.updateCandidateStage(evaluationId, {
        stage: stage as EvaluationStage,
        notes: notes.trim(),
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || "Failed to record stage transition.");
      } else {
        setError("Failed to record stage transition.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Record Recruiter Decision"
      description={`Record stage transition and rationale for candidate: ${candidateName}`}
      maxWidth="md"
      footer={
        <div className="flex items-center justify-end gap-2 w-full">
          <button
            type="button"
            disabled={loading}
            onClick={onClose}
            className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={handleSubmit}
            className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg shadow-sm transition flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Confirm Decision</span>
          </button>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div
            role="alert"
            aria-live="assertive"
            className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 rounded-lg text-xs flex items-center gap-2"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-1.5">
          <label
            htmlFor="decision-stage-select"
            className="text-xs font-semibold text-slate-700 dark:text-slate-300"
          >
            New Pipeline Stage <span className="text-rose-500">*</span>
          </label>
          <select
            id="decision-stage-select"
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
          >
            <option value="screened">Screened (Under Review)</option>
            <option value="shortlisted">Shortlisted</option>
            <option value="interview">Interview Scheduled</option>
            <option value="offered">Offer Extended</option>
            <option value="hired">Hired</option>
            <option value="rejected">Rejected</option>
            <option value="withdrawn">Withdrawn</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <label
            htmlFor="decision-notes-field"
            className="text-xs font-semibold text-slate-700 dark:text-slate-300"
          >
            Recruiter Rationale & Audit Notes <span className="text-rose-500">*</span>
          </label>
          <textarea
            id="decision-notes-field"
            rows={4}
            required
            placeholder="Explain the reasoning for this stage transition (e.g. passed technical screen, matched all required skills)..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full text-xs p-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[11px] text-slate-400">
            Recorded to immutable audit log with your authenticated user ID and timestamp.
          </p>
        </div>
      </form>
    </Modal>
  );
};
