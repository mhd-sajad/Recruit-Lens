import React from "react";
import type { EvaluationSummaryResponse } from "../../types/api";
import { Badge } from "../common/Badge";
import { useAuth } from "../../context/AuthContext";
import { ArrowLeft, CheckCircle2, XCircle, Shield } from "lucide-react";

interface CompareScreenProps {
  candidates: EvaluationSummaryResponse[];
  onBack: () => void;
  onSelectCandidate: (id: string) => void;
}

export const CompareScreen: React.FC<CompareScreenProps> = ({
  candidates,
  onBack,
  onSelectCandidate,
}) => {
  const { isBlindMode } = useAuth();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition"
            aria-label="Back to candidate table"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              Candidate Comparison Matrix
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Comparing {candidates.length} candidates side-by-side
            </p>
          </div>
        </div>
      </div>

      {/* Comparison Grid */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-200 dark:divide-slate-800">
          {candidates.map((cand) => {
            const cId = cand.candidate_id || cand.id;
            const candidateLabel = isBlindMode
              ? `Candidate #${cId.slice(-6).toUpperCase()}`
              : cand.candidate_name || `Candidate #${cId.slice(-6).toUpperCase()}`;

            const missingCount = (cand.missing_must_haves || []).length;
            const score = cand.fit_score ?? cand.total_score ?? 0;

            return (
              <div key={cand.id} className="p-6 space-y-6 flex flex-col justify-between">
                <div className="space-y-4">
                  {/* Candidate Header */}
                  <div>
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                        {candidateLabel}
                        {isBlindMode && <Shield className="w-3.5 h-3.5 text-purple-500" />}
                      </h3>
                      <Badge variant="tier" value={cand.tier} />
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      {cand.candidate_title || "Software Professional"}
                    </p>
                  </div>

                  {/* Fit Score */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700/60 text-center">
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">Fit Score</span>
                    <div className="text-2xl font-black font-mono text-slate-900 dark:text-slate-100">
                      {cand.tier === "abstain" ? "ABSTAIN" : `${(score * 100).toFixed(0)}%`}
                    </div>
                  </div>

                  {/* Experience */}
                  <div className="space-y-1 text-xs">
                    <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider text-[10px]">
                      Experience
                    </span>
                    <p className="font-mono text-slate-800 dark:text-slate-200">
                      {cand.years_experience !== null && cand.years_experience !== undefined && cand.years_experience > 0
                        ? `${cand.years_experience.toFixed(1)} years`
                        : "dates missing"}
                    </p>
                  </div>

                  {/* Must Haves */}
                  <div className="space-y-1 text-xs">
                    <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider text-[10px]">
                      Must-Haves
                    </span>
                    {missingCount === 0 ? (
                      <p className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> All requirements met
                      </p>
                    ) : (
                      <p className="text-rose-600 dark:text-rose-400 flex items-start gap-1">
                        <XCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                        <span>Missing: {(cand.missing_must_haves || []).join(", ")}</span>
                      </p>
                    )}
                  </div>

                  {/* Current Stage */}
                  <div className="space-y-1 text-xs">
                    <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider text-[10px]">
                      Current Stage
                    </span>
                    <div>
                      <Badge variant="stage" value={cand.stage} />
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={() => onSelectCandidate(cand.id)}
                    className="w-full py-2 px-3 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
                  >
                    View Full Profile
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
