import React, { useState } from "react";
import { Modal } from "../common/Modal";
import { api } from "../../lib/api";
import type { EvaluationStage } from "../../types/api";
import { Star, AlertCircle, CheckCircle2 } from "lucide-react";

interface ScorecardModalProps {
  isOpen: boolean;
  onClose: () => void;
  evaluationId: string;
  candidateName: string;
  onSuccess: () => void;
}

export const ScorecardModal: React.FC<ScorecardModalProps> = ({
  isOpen,
  onClose,
  evaluationId,
  candidateName,
  onSuccess,
}) => {
  const [techRating, setTechRating] = useState(4);
  const [designRating, setDesignRating] = useState(4);
  const [problemSolvingRating, setProblemSolvingRating] = useState(4);
  const [communicationRating, setCommunicationRating] = useState(4);

  const [recommendation, setRecommendation] = useState<
    "strong_hire" | "hire" | "lean_hire" | "lean_no_hire" | "strong_no_hire"
  >("hire");
  const [notes, setNotes] = useState("");
  const [reDecisionStage, setReDecisionStage] = useState<string>("offered");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!notes.trim()) {
      setError("Please provide scorecard interview feedback notes.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const overallRating = Number(
        ((techRating + designRating + problemSolvingRating + communicationRating) / 4).toFixed(1)
      );

      const recValue =
        recommendation === "strong_hire"
          ? "strong_hire"
          : recommendation === "hire" || recommendation === "lean_hire"
          ? "hire"
          : "no_hire";

      await api.submitInterviewFeedback(evaluationId, {
        interviewer_name: "Lead Technical Recruiter",
        overall_score: overallRating,
        technical_rating: techRating,
        communication_rating: communicationRating,
        recommendation: recValue,
        notes: `Technical: ${techRating}/5, Design: ${designRating}/5, Problem Solving: ${problemSolvingRating}/5, Communication: ${communicationRating}/5\n\nNotes: ${notes.trim()}`,
      });

      // Update stage if specified
      if (reDecisionStage) {
        await api.updateCandidateStage(evaluationId, {
          stage: reDecisionStage as EvaluationStage,
          notes: `Post-interview decision: ${recommendation.toUpperCase()} (Overall rating: ${overallRating}/5)`,
        });
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || "Failed to submit interview scorecard.");
      } else {
        setError("Failed to submit interview scorecard.");
      }
    } finally {
      setLoading(false);
    }
  };

  const renderStarSelector = (
    label: string,
    value: number,
    onChange: (val: number) => void
  ) => (
    <div className="flex items-center justify-between py-1">
      <span className="text-xs text-slate-700 dark:text-slate-300 font-medium">
        {label}
      </span>
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className={`p-1 rounded hover:scale-110 transition ${
              star <= value
                ? "text-amber-500 fill-amber-500"
                : "text-slate-300 dark:text-slate-600"
            }`}
          >
            <Star className="w-4 h-4 fill-current" />
          </button>
        ))}
        <span className="text-xs font-mono ml-1 text-slate-500 w-4 text-right">
          {value}
        </span>
      </div>
    </div>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Post-Interview Scorecard & Re-Decision"
      description={`Structured evaluation and stage calibration for: ${candidateName}`}
      maxWidth="lg"
      footer={
        <div className="flex items-center justify-end gap-2 w-full">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={handleSubmit}
            className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Submit Scorecard & Decision</span>
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

        {/* Rating categories */}
        <div className="p-4 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700/80 space-y-1">
          <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-2">
            Interview Rubric Ratings (1-5)
          </h4>
          {renderStarSelector("Technical Competency", techRating, setTechRating)}
          {renderStarSelector("System Design & Architecture", designRating, setDesignRating)}
          {renderStarSelector("Problem Solving & Algorithms", problemSolvingRating, setProblemSolvingRating)}
          {renderStarSelector("Communication & Collaboration", communicationRating, setCommunicationRating)}
        </div>

        {/* Hiring Recommendation */}
        <div className="space-y-1.5">
          <label
            htmlFor="scorecard-recommendation-select"
            className="text-xs font-semibold text-slate-700 dark:text-slate-300"
          >
            Hiring Recommendation
          </label>
          <select
            id="scorecard-recommendation-select"
            value={recommendation}
            onChange={(e) =>
              setRecommendation(
                e.target.value as "strong_hire" | "hire" | "lean_hire" | "lean_no_hire" | "strong_no_hire"
              )
            }
            className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
          >
            <option value="strong_hire">Strong Hire (High Priority)</option>
            <option value="hire">Hire</option>
            <option value="lean_hire">Lean Hire</option>
            <option value="lean_no_hire">Lean No Hire</option>
            <option value="strong_no_hire">Strong No Hire</option>
          </select>
        </div>

        {/* Stage Re-decision */}
        <div className="space-y-1.5">
          <label
            htmlFor="scorecard-next-stage-select"
            className="text-xs font-semibold text-slate-700 dark:text-slate-300"
          >
            Advance Pipeline Stage To
          </label>
          <select
            id="scorecard-next-stage-select"
            value={reDecisionStage}
            onChange={(e) => setReDecisionStage(e.target.value)}
            className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
          >
            <option value="offered">Offer Extended</option>
            <option value="hired">Hired</option>
            <option value="rejected">Rejected</option>
            <option value="interview">Keep in Interview Stage</option>
          </select>
        </div>

        {/* Detailed Feedback Notes */}
        <div className="space-y-1.5">
          <label
            htmlFor="scorecard-notes-field"
            className="text-xs font-semibold text-slate-700 dark:text-slate-300"
          >
            Scorecard Evaluation Notes <span className="text-rose-500">*</span>
          </label>
          <textarea
            id="scorecard-notes-field"
            rows={4}
            required
            placeholder="Detailed notes on candidate performance, key strengths, potential gaps, and feedback..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full text-xs p-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </form>
    </Modal>
  );
};
