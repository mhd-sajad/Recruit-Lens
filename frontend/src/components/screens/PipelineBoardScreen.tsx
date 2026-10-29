import React from "react";
import type { EvaluationSummaryResponse, EvaluationStage } from "../../types/api";
import { Badge } from "../common/Badge";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";
import { Shield, ChevronRight, ChevronLeft } from "lucide-react";

interface PipelineBoardScreenProps {
  evaluations: EvaluationSummaryResponse[];
  onSelectCandidate: (id: string) => void;
  onRefresh: () => void;
  onOpenDecision: (candidate: EvaluationSummaryResponse) => void;
}

const PIPELINE_COLUMNS: { id: EvaluationStage; label: string; color: string }[] = [
  { id: "screened", label: "Screened", color: "border-indigo-400" },
  { id: "shortlisted", label: "Shortlisted", color: "border-sky-400" },
  { id: "interview_scheduled", label: "Interview", color: "border-blue-500" },
  { id: "offer_extended", label: "Offered", color: "border-amber-400" },
  { id: "hired", label: "Hired", color: "border-emerald-500" },
  { id: "rejected", label: "Rejected", color: "border-rose-400" },
];

export const PipelineBoardScreen: React.FC<PipelineBoardScreenProps> = ({
  evaluations,
  onSelectCandidate,
  onRefresh,
  onOpenDecision,
}) => {
  const { isBlindMode } = useAuth();

  const handleQuickAdvance = async (cand: EvaluationSummaryResponse, nextStage: EvaluationStage) => {
    try {
      await api.updateCandidateStage(cand.id, {
        stage: nextStage,
        notes: `Quick advanced on Kanban pipeline board to ${nextStage}`,
      });
      onRefresh();
    } catch (err) {
      console.error("Failed to advance stage:", err);
    }
  };

  const evalList = Array.isArray(evaluations) ? evaluations : [];

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            Hiring Pipeline Board
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Interactive stage progression across all active candidate evaluations
          </p>
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
          Total Candidates in Board: <strong className="text-slate-900 dark:text-slate-100">{evalList.length}</strong>
        </div>
      </div>

      {/* Kanban Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5 items-start">
        {PIPELINE_COLUMNS.map((col, colIdx) => {
          const colCandidates = evalList.filter((c) => {
            const st = (c.stage || "screened").toLowerCase();
            return st === col.id || (col.id === "screened" && st === "new");
          });

          return (
            <div
              key={col.id}
              className="bg-slate-50/70 dark:bg-slate-900/60 rounded-xl border border-slate-200 dark:border-slate-800 flex flex-col max-h-[78vh]"
            >
              {/* Column Header */}
              <div
                className={`p-3 border-t-4 rounded-t-xl bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between ${col.color}`}
              >
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  {col.label}
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  {colCandidates.length}
                </span>
              </div>

              {/* Cards List */}
              <div className="p-2 space-y-2.5 overflow-y-auto flex-1">
                {colCandidates.length === 0 ? (
                  <div className="p-4 text-center text-slate-400 text-[11px] italic">
                    No candidates
                  </div>
                ) : (
                  colCandidates.map((cand) => {
                    const cId = cand.candidate_id || cand.id;
                    const candidateLabel = isBlindMode
                      ? `Candidate #${cId.slice(-6).toUpperCase()}`
                      : cand.candidate_name || `Candidate #${cId.slice(-6).toUpperCase()}`;

                    const score = cand.fit_score ?? cand.total_score ?? 0;
                    const prevCol = colIdx > 0 ? PIPELINE_COLUMNS[colIdx - 1] : undefined;
                    const nextCol = colIdx < PIPELINE_COLUMNS.length - 1 ? PIPELINE_COLUMNS[colIdx + 1] : undefined;

                    return (
                      <div
                        key={cand.id}
                        onClick={() => onSelectCandidate(cand.id)}
                        className="p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700/80 shadow-xs hover:border-blue-400 dark:hover:border-blue-500 cursor-pointer transition space-y-2"
                      >
                        <div className="flex items-start justify-between gap-1">
                          <div>
                            <div className="font-semibold text-xs text-slate-900 dark:text-slate-100 flex items-center gap-1">
                              {candidateLabel}
                              {isBlindMode && <Shield className="w-3 h-3 text-purple-500" />}
                            </div>
                            <div className="text-[10px] text-slate-400 line-clamp-1">
                              {cand.candidate_title || "Software Professional"}
                            </div>
                          </div>
                          <Badge variant="tier" value={cand.tier} />
                        </div>

                        <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-100 dark:border-slate-700/60">
                          <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                            {cand.tier === "abstain" ? "ABSTAIN" : `${(score * 100).toFixed(0)}%`}
                          </span>
                          <span className="text-slate-400">
                            {cand.years_experience !== null && cand.years_experience !== undefined && cand.years_experience > 0
                              ? `${cand.years_experience.toFixed(1)}y`
                              : "dates missing"}
                          </span>
                        </div>

                        {/* Quick Transition Action Controls */}
                        <div
                          className="flex items-center justify-between pt-1 text-[10px] text-slate-500"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {prevCol ? (
                            <button
                              type="button"
                              onClick={() => handleQuickAdvance(cand, prevCol.id)}
                              className="p-1 hover:text-slate-800 dark:hover:text-slate-200 rounded"
                              title={`Move back to ${prevCol.label}`}
                            >
                              <ChevronLeft className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <div />
                          )}

                          <button
                            type="button"
                            onClick={() => onOpenDecision(cand)}
                            className="text-[10px] font-medium text-blue-600 dark:text-blue-400 hover:underline"
                          >
                            Decide
                          </button>

                          {nextCol ? (
                            <button
                              type="button"
                              onClick={() => handleQuickAdvance(cand, nextCol.id)}
                              className="p-1 hover:text-slate-800 dark:hover:text-slate-200 rounded"
                              title={`Advance to ${nextCol.label}`}
                            >
                              <ChevronRight className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <div />
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
