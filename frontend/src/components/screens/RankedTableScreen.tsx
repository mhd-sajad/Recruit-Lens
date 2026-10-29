import React, { useState, useMemo } from "react";
import type { EvaluationSummaryResponse } from "../../types/api";
import { Badge } from "../common/Badge";
import { useAuth } from "../../context/AuthContext";
import {
  Search,
  ArrowUpDown,
  CheckSquare,
  Square,
  Columns,
  AlertTriangle,
  ChevronRight,
  Shield,
} from "lucide-react";

interface RankedTableScreenProps {
  evaluations: EvaluationSummaryResponse[];
  onSelectCandidate: (evaluationId: string) => void;
  onCompareCandidates: (evaluationIds: string[]) => void;
  onOpenDecision: (candidate: EvaluationSummaryResponse) => void;
}

export const RankedTableScreen: React.FC<RankedTableScreenProps> = ({
  evaluations,
  onSelectCandidate,
  onCompareCandidates,
  onOpenDecision,
}) => {
  const { isBlindMode } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTier, setSelectedTier] = useState<string>("all");
  const [selectedStage, setSelectedStage] = useState<string>("all");
  const [sortField, setSortField] = useState<"score" | "years_experience" | "created_at">("score");
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [filterMissingMustHavesOnly, setFilterMissingMustHavesOnly] = useState<boolean>(false);

  // Selected candidates for comparison (max 3)
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);

  const handleToggleSelectCompare = (id: string) => {
    if (selectedForCompare.includes(id)) {
      setSelectedForCompare(selectedForCompare.filter((i) => i !== id));
    } else {
      if (selectedForCompare.length >= 3) {
        alert("You can compare at most 3 candidates simultaneously.");
        return;
      }
      setSelectedForCompare([...selectedForCompare, id]);
    }
  };

  const filteredCandidates = useMemo(() => {
    const list = Array.isArray(evaluations) ? evaluations : [];
    return list.filter((c) => {
      // Search
      const searchLower = searchQuery.toLowerCase();
      const nameMatch = !isBlindMode && (c.candidate_name || c.candidate_filename || "").toLowerCase().includes(searchLower);
      const titleMatch = (c.candidate_title || "").toLowerCase().includes(searchLower);
      const idMatch = (c.candidate_id || c.id || "").toLowerCase().includes(searchLower);
      const matchesSearch = !searchQuery || nameMatch || titleMatch || idMatch;

      // Tier filter
      const matchesTier =
        selectedTier === "all" ||
        (c.tier && c.tier.toLowerCase() === selectedTier.toLowerCase());

      // Stage filter
      const matchesStage =
        selectedStage === "all" ||
        (c.stage && c.stage.toLowerCase() === selectedStage.toLowerCase());

      // Missing must-haves filter
      const missingMustHaves = (c.missing_must_haves || []).length > 0;
      const matchesMissing = !filterMissingMustHavesOnly || missingMustHaves;

      return matchesSearch && matchesTier && matchesStage && matchesMissing;
    });
  }, [
    evaluations,
    searchQuery,
    selectedTier,
    selectedStage,
    filterMissingMustHavesOnly,
    isBlindMode,
  ]);

  const sortedCandidates = useMemo(() => {
    return [...filteredCandidates].sort((a, b) => {
      let valA: number | string = 0;
      let valB: number | string = 0;

      if (sortField === "score") {
        valA = a.fit_score ?? 0;
        valB = b.fit_score ?? 0;
      } else if (sortField === "years_experience") {
        valA = a.years_experience ?? 0;
        valB = b.years_experience ?? 0;
      } else {
        valA = a.created_at || "";
        valB = b.created_at || "";
      }

      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [filteredCandidates, sortField, sortAsc]);

  return (
    <div className="space-y-4">
      {/* Search and Filter Bar */}
      <div className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex-1 flex items-center gap-2">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by title, skills or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-2 text-slate-700 dark:text-slate-300"
              aria-label="Filter by Fit Tier"
            >
              <option value="all">All Tiers</option>
              <option value="strong_fit">Strong Fit (FastTrack)</option>
              <option value="interview">Interview (Review)</option>
              <option value="hold">Hold</option>
              <option value="reject">Reject</option>
              <option value="abstain">Abstain</option>
            </select>

            <select
              value={selectedStage}
              onChange={(e) => setSelectedStage(e.target.value)}
              className="text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-2 text-slate-700 dark:text-slate-300"
              aria-label="Filter by Stage"
            >
              <option value="all">All Stages</option>
              <option value="new">New</option>
              <option value="screened">Screened</option>
              <option value="shortlisted">Shortlisted</option>
              <option value="interview">Interview</option>
              <option value="offered">Offered</option>
              <option value="hired">Hired</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={filterMissingMustHavesOnly}
              onChange={(e) => setFilterMissingMustHavesOnly(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Missing Must-Haves Only</span>
          </label>

          {selectedForCompare.length >= 2 && (
            <button
              onClick={() => onCompareCandidates(selectedForCompare)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition"
            >
              <Columns className="w-3.5 h-3.5" />
              Compare ({selectedForCompare.length})
            </button>
          )}
        </div>
      </div>

      {/* Candidates Ranked Table */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/50 text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4 w-10 text-center">
                  <span className="sr-only">Select</span>
                </th>
                <th className="py-3 px-4">Candidate</th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                  onClick={() => {
                    if (sortField === "score") setSortAsc(!sortAsc);
                    else {
                      setSortField("score");
                      setSortAsc(false);
                    }
                  }}
                >
                  <div className="flex items-center gap-1">
                    <span>Score & Tier</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                  onClick={() => {
                    if (sortField === "years_experience") setSortAsc(!sortAsc);
                    else {
                      setSortField("years_experience");
                      setSortAsc(false);
                    }
                  }}
                >
                  <div className="flex items-center gap-1">
                    <span>Experience</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-4">Must-Have Skills</th>
                <th className="py-3 px-4">Stage</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80 text-xs text-slate-700 dark:text-slate-300">
              {sortedCandidates.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No candidates found matching the selected criteria.
                  </td>
                </tr>
              ) : (
                sortedCandidates.map((cand) => {
                  const isChecked = selectedForCompare.includes(cand.id);
                  const isAbstain = cand.tier === "abstain";
                  const missingCount = (cand.missing_must_haves || []).length;
                  const cId = cand.candidate_id || cand.id;
                  const score = cand.fit_score ?? cand.total_score ?? 0;

                  // Candidate display: title + dates, "dates missing" instead of 0, no company displayed
                  const candidateLabel = isBlindMode
                    ? `Candidate #${cId.slice(-6).toUpperCase()}`
                    : cand.candidate_name || `Candidate #${cId.slice(-6).toUpperCase()}`;

                  return (
                    <tr
                      key={cand.id}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition cursor-pointer"
                      onClick={() => onSelectCandidate(cand.id)}
                    >
                      {/* Compare Checkbox */}
                      <td
                        className="py-3 px-4 text-center"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleSelectCompare(cand.id);
                        }}
                      >
                        <button
                          type="button"
                          className="text-slate-400 hover:text-blue-600 focus:outline-none"
                          aria-label={`Select ${candidateLabel} for comparison`}
                        >
                          {isChecked ? (
                            <CheckSquare className="w-4 h-4 text-blue-600" />
                          ) : (
                            <Square className="w-4 h-4" />
                          )}
                        </button>
                      </td>

                      {/* Candidate Name & Title (NO COMPANY DISPLAYED per SPEC) */}
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                          {candidateLabel}
                          {isBlindMode && (
                            <span title="Blind Mode Redacted">
                              <Shield className="w-3 h-3 text-purple-500" />
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          {cand.candidate_title || "Software Professional"}
                        </div>
                      </td>

                      {/* Score & Tier */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-slate-900 dark:text-slate-100 font-mono">
                            {isAbstain ? "N/A" : `${(score * 100).toFixed(0)}%`}
                          </span>
                          <Badge variant="tier" value={cand.tier} />
                        </div>
                        {isAbstain && (
                          <span className="text-[10px] text-purple-600 dark:text-purple-400">
                            Insufficient parse confidence
                          </span>
                        )}
                      </td>

                      {/* Experience: "dates missing" instead of 0 */}
                      <td className="py-3 px-4">
                        {cand.years_experience !== null && cand.years_experience !== undefined && cand.years_experience > 0 ? (
                          <span className="font-mono">{cand.years_experience.toFixed(1)} yrs</span>
                        ) : (
                          <span className="text-slate-400 italic text-[11px]">dates missing</span>
                        )}
                      </td>

                      {/* Must-have skills status */}
                      <td className="py-3 px-4">
                        {missingCount === 0 ? (
                          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                            All satisfied
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] text-rose-600 dark:text-rose-400 font-medium">
                            <AlertTriangle className="w-3 h-3" />
                            Missing {missingCount}: {(cand.missing_must_haves || []).slice(0, 2).join(", ")}
                          </span>
                        )}
                      </td>

                      {/* Stage */}
                      <td className="py-3 px-4">
                        <Badge variant="stage" value={cand.stage} />
                      </td>

                      {/* Actions */}
                      <td
                        className="py-3 px-4 text-right"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => onOpenDecision(cand)}
                            className="px-2.5 py-1 text-[11px] font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
                          >
                            Decide
                          </button>
                          <button
                            type="button"
                            onClick={() => onSelectCandidate(cand.id)}
                            className="p-1 text-slate-400 hover:text-blue-600 rounded-lg"
                            aria-label={`View details for ${candidateLabel}`}
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
