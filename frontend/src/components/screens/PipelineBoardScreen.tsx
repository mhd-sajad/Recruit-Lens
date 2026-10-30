import React, { useState } from "react";
import {
  Lock,
  MoreVertical,
  AlertTriangle,
  X,
} from "lucide-react";
import { TierBadge } from "../common/TierBadge";
import { useAuth } from "../../context/AuthContext";
import type { CandidateItem } from "../../lib/mockData";

interface PipelineBoardScreenProps {
  candidates: CandidateItem[];
  onSelectCandidate: (candidateId: string) => void;
  onUpdateCandidateStage: (candidateId: string, newStage: CandidateItem["stage"]) => void;
}

const STAGES: Array<CandidateItem["stage"]> = [
  "Screened",
  "Interview",
  "Technical assessment",
  "Offer",
];

export const PipelineBoardScreen: React.FC<PipelineBoardScreenProps> = ({
  candidates,
  onSelectCandidate,
  onUpdateCandidateStage,
}) => {
  const { isBlindMode } = useAuth();

  // Rationale modal state when moving low-score candidate to Offer
  const [rationaleModal, setRationaleModal] = useState<{
    candidate: CandidateItem;
    targetStage: CandidateItem["stage"];
    rationale: string;
  } | null>(null);

  // Active keyboard move menu open for a candidate
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const handleStageMove = (cand: CandidateItem, targetStage: CandidateItem["stage"]) => {
    // If advancing a Reject-tier or low score (<55) candidate to Offer, mandate rationale
    if (targetStage === "Offer" && (cand.tier === "Reject" || cand.match_score < 55)) {
      setRationaleModal({
        candidate: cand,
        targetStage,
        rationale: "",
      });
      return;
    }
    onUpdateCandidateStage(cand.id, targetStage);
    setActiveMenuId(null);
  };

  const handleConfirmRationale = () => {
    if (!rationaleModal || !rationaleModal.rationale.trim()) return;
    onUpdateCandidateStage(rationaleModal.candidate.id, rationaleModal.targetStage);
    setRationaleModal(null);
    setActiveMenuId(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-default)] pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Pipeline Board
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Visual recruitment pipeline with automated guardrails on low-score stage advancements.
          </p>
        </div>
        <div className="text-xs font-mono text-[var(--text-secondary)]">
          Total Candidates: <strong className="text-[var(--text-primary)]">{candidates.length}</strong>
        </div>
      </div>

      {/* Rationale Modal when moving a Reject-tier candidate to Offer */}
      {rationaleModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
        >
          <div className="w-full max-w-md rounded-xl bg-[var(--surface)] border border-[var(--border-default)] p-5 shadow-2xl space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 text-amber-500">
                <AlertTriangle className="w-5 h-5" />
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  Advancement Rationale Required
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setRationaleModal(null)}
                className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                aria-label="Close dialog"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-800 dark:text-amber-300">
              Low match score ({rationaleModal.candidate.match_score}) in tier{" "}
              <strong>{rationaleModal.candidate.tier}</strong>. Company policy requires recorded
              human justification before extending an offer to protect fairness and audit trails.
            </div>

            <div>
              <label
                htmlFor="rationale-input"
                className="block text-xs font-medium text-[var(--text-secondary)] mb-1"
              >
                Justification & Evidence for Advancement *
              </label>
              <textarea
                id="rationale-input"
                rows={3}
                value={rationaleModal.rationale}
                onChange={(e) =>
                  setRationaleModal({ ...rationaleModal, rationale: e.target.value })
                }
                placeholder="e.g. Candidate demonstrated deep proprietary streaming expertise in live pairing session..."
                className="w-full text-xs bg-[var(--canvas)] text-[var(--text-primary)] border border-[var(--border-default)] rounded-md p-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border-default)]">
              <button
                type="button"
                onClick={() => setRationaleModal(null)}
                className="px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-md border border-[var(--border-default)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmRationale}
                disabled={!rationaleModal.rationale.trim()}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md shadow-xs"
              >
                Record Override & Advance
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4 Pipeline Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-start">
        {STAGES.map((stage) => {
          const colCandidates = candidates.filter((c) => c.stage === stage);

          return (
            <div
              key={stage}
              className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] flex flex-col min-h-[500px]"
            >
              {/* Column Header */}
              <div className="p-3.5 border-b border-[var(--border-default)] flex items-center justify-between">
                <span className="text-xs font-bold text-[var(--text-primary)]">
                  {stage}
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--subtle)] text-[var(--text-secondary)] border border-[var(--border-default)]">
                  {colCandidates.length}
                </span>
              </div>

              {/* Cards List */}
              <div className="p-3 space-y-3 flex-1 overflow-y-auto">
                {colCandidates.length === 0 ? (
                  <div className="p-6 text-center text-xs text-[var(--text-secondary)] italic">
                    Drop candidates here
                  </div>
                ) : (
                  colCandidates.map((cand) => (
                    <div
                      key={cand.id}
                      className="p-3.5 rounded-lg border border-[var(--border-default)] bg-[var(--canvas)] hover:border-slate-500 shadow-xs transition-all space-y-2.5 relative group cursor-pointer"
                      onClick={() => onSelectCandidate(cand.id)}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") onSelectCandidate(cand.id);
                      }}
                    >
                      {/* Top Header: Candidate Name or #NNNN + Tier Badge */}
                      <div className="flex items-start justify-between gap-1">
                        <div>
                          {isBlindMode ? (
                            <div className="flex items-center gap-1 font-mono font-bold text-xs text-[var(--text-primary)]">
                              <Lock className="w-3 h-3 text-blue-500" />
                              <span>Candidate #{cand.code}</span>
                            </div>
                          ) : (
                            <div className="font-semibold text-xs text-[var(--text-primary)] group-hover:text-blue-500 transition-colors">
                              {cand.name}
                            </div>
                          )}
                          <p className="text-[11px] text-[var(--text-secondary)] line-clamp-1 mt-0.5">
                            {cand.most_recent_role}
                          </p>
                        </div>

                        <TierBadge tier={cand.tier} size="sm" />
                      </div>

                      {/* Score & Verified Experience row */}
                      <div className="flex items-center justify-between text-xs pt-1 border-t border-[var(--border-default)] font-mono">
                        <span className="font-bold text-[var(--text-primary)]">
                          Score: {cand.match_score}
                        </span>
                        <span className="text-[var(--text-secondary)]">
                          {cand.verified_experience}
                        </span>
                      </div>

                      {/* Keyboard Move Controls Menu */}
                      <div
                        className="flex items-center justify-between pt-1 text-[11px]"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span className="text-[10px] text-[var(--text-secondary)]">
                          Must-haves: {cand.must_have_coverage}
                        </span>

                        <div className="relative">
                          <button
                            type="button"
                            onClick={() =>
                              setActiveMenuId(activeMenuId === cand.id ? null : cand.id)
                            }
                            className="p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded hover:bg-[var(--subtle)] transition-colors"
                            aria-label={`Move stage for Candidate #${cand.code}`}
                          >
                            <MoreVertical className="w-3.5 h-3.5" />
                          </button>

                          {activeMenuId === cand.id && (
                            <div
                              className="absolute right-0 bottom-6 z-20 w-44 rounded-lg bg-[var(--surface)] border border-[var(--border-default)] shadow-xl p-1 text-xs"
                              role="menu"
                            >
                              <div className="px-2 py-1 text-[10px] uppercase font-semibold text-[var(--text-secondary)]">
                                Move to...
                              </div>
                              {STAGES.filter((s) => s !== stage).map((targetStage) => (
                                <button
                                  key={targetStage}
                                  type="button"
                                  onClick={() => handleStageMove(cand, targetStage)}
                                  className="w-full text-left px-2 py-1.5 rounded text-[var(--text-primary)] hover:bg-[var(--subtle)] transition-colors"
                                  role="menuitem"
                                >
                                  → {targetStage}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
