import React, { useState, useMemo } from "react";
import {
  Lock,
  Download,
  Info,
  X,
  CheckCircle2,
  AlertTriangle,
  Mail,
  RotateCcw,
  Search,
} from "lucide-react";
import { TierBadge } from "../common/TierBadge";
import { useAuth } from "../../context/AuthContext";
import type { CandidateItem, JobItem } from "../../lib/mockData";

interface RankedTableScreenProps {
  job: JobItem;
  candidates: CandidateItem[];
  onSelectCandidate: (candidateId: string) => void;
  onOpenEmail: (candidateId: string) => void;
  onExportAudit: () => void;
  onNavigateRequisitions: () => void;
}

export const RankedTableScreen: React.FC<RankedTableScreenProps> = ({
  job,
  candidates = [],
  onSelectCandidate,
  onOpenEmail,
  onExportAudit,
  onNavigateRequisitions,
}) => {
  const { isBlindMode } = useAuth();
  const safeCandidates = useMemo(() => (Array.isArray(candidates) ? candidates : []), [candidates]);
  const [showInfoBanner, setShowInfoBanner] = useState(true);
  const [tierFilter, setTierFilter] = useState<string>("All");
  const [coverageFilter, setCoverageFilter] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Counts by tier
  const tierCounts = useMemo(() => {
    return {
      all: safeCandidates.length,
      fasttrack: safeCandidates.filter((c) => c.tier === "FastTrack").length,
      interview: safeCandidates.filter((c) => c.tier === "Interview").length,
      hold: safeCandidates.filter((c) => c.tier === "Hold").length,
      reject: safeCandidates.filter((c) => c.tier === "Reject").length,
    };
  }, [safeCandidates]);

  // Filtered and sorted descending by match score
  const filteredCandidates = useMemo(() => {
    return safeCandidates
      .filter((c) => {
        if (tierFilter !== "All" && c.tier !== tierFilter) return false;
        if (coverageFilter === "100%" && !c.must_have_coverage.startsWith("7 / 7") && !c.must_have_coverage.startsWith("6 / 6")) {
          return false;
        }
        if (coverageFilter === "75%+") {
          const parts = c.must_have_coverage.split("/").map((s) => parseFloat(s.trim()));
          const num = parts[0];
          const den = parts[1];
          if (num !== undefined && den !== undefined && den > 0 && num / den < 0.75) return false;
        }
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const target = isBlindMode
            ? `candidate #${c.code}`
            : `${c.name} candidate #${c.code} ${c.email} ${c.most_recent_role}`;
          if (!target.toLowerCase().includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => b.match_score - a.match_score);
  }, [safeCandidates, tierFilter, coverageFilter, searchQuery, isBlindMode]);

  const handleResetFilters = () => {
    setTierFilter("All");
    setCoverageFilter("All");
    setSearchQuery("");
  };

  return (
    <div className="space-y-5">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="text-xs text-[var(--text-secondary)]">
        <ol className="flex items-center gap-1.5 flex-wrap">
          <li>
            <button
              type="button"
              onClick={onNavigateRequisitions}
              className="hover:text-[var(--text-primary)] transition-colors focus:outline-none focus:underline cursor-pointer"
            >
              Requisitions
            </button>
          </li>
          <li aria-hidden="true">/</li>
          <li className="text-[var(--text-primary)] font-medium truncate max-w-[320px]">
            {job.title}
          </li>
          <li aria-hidden="true">/</li>
          <li className="text-blue-500 font-semibold" aria-current="page">
            Candidates
          </li>
        </ol>
      </nav>

      {/* Page Title & Controls Row */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              Ranked candidates
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[var(--subtle)] text-[var(--text-secondary)] border border-[var(--border-default)]">
              {filteredCandidates.length} of {candidates.length} candidates
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Deterministic rule-based pre-screening combined with semantic embedding match.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={onExportAudit}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] bg-[var(--surface)] hover:bg-[var(--subtle)] border border-[var(--border-default)] rounded-md shadow-xs transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            title="Export tamper-evident cryptographic audit chain log (CSV)"
          >
            <Download className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Export audit log</span>
          </button>
        </div>
      </div>

      {/* Info Banner: Non-negotiable employer name suppression notice */}
      {showInfoBanner && (
        <div
          role="region"
          aria-label="Privacy notice"
          className="flex items-start justify-between gap-3 p-3.5 rounded-lg bg-blue-500/10 border border-blue-500/25 text-xs text-blue-800 dark:text-blue-300 transition-colors"
        >
          <div className="flex items-start gap-2.5">
            <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <p className="font-semibold text-[var(--text-primary)]">
                Prestige Bias Suppression Active
              </p>
              <p className="text-[var(--text-secondary)] mt-0.5">
                Employer and company names are suppressed by design to prevent prestige bias.
                Scores are grounded strictly in resume evidence and verifiable skills.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowInfoBanner(false)}
            aria-label="Dismiss privacy notice"
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] p-1 rounded-md transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 p-3 rounded-lg bg-[var(--surface)] border border-[var(--border-default)]">
        {/* Tier Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5">
          <span className="text-xs font-medium text-[var(--text-secondary)] mr-1">Tier:</span>
          {[
            { id: "All", label: `All (${tierCounts.all})` },
            { id: "FastTrack", label: `FastTrack (${tierCounts.fasttrack})` },
            { id: "Interview", label: `Interview (${tierCounts.interview})` },
            { id: "Hold", label: `Hold (${tierCounts.hold})` },
            { id: "Reject", label: `Reject (${tierCounts.reject})` },
          ].map((pill) => (
            <button
              key={pill.id}
              type="button"
              onClick={() => setTierFilter(pill.id)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md whitespace-nowrap transition-colors ${
                tierFilter === pill.id
                  ? "bg-blue-600 text-white font-semibold shadow-xs"
                  : "bg-[var(--subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-default)]"
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>

        {/* Coverage Filter Pills + Search */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-[var(--text-secondary)]">Coverage:</span>
            {(["All", "100%", "75%+"] as const).map((cov) => (
              <button
                key={cov}
                type="button"
                onClick={() => setCoverageFilter(cov)}
                className={`px-2 py-1 text-xs font-medium rounded-md transition-colors ${
                  coverageFilter === cov
                    ? "bg-blue-600 text-white font-semibold"
                    : "bg-[var(--subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-default)]"
                }`}
              >
                {cov}
              </button>
            ))}
          </div>

          {/* Quick filter text */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[var(--text-secondary)] absolute left-2.5 top-2.5 pointer-events-none" />
            <input
              type="text"
              placeholder="Search candidate or title..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 text-xs bg-[var(--subtle)] text-[var(--text-primary)] border border-[var(--border-default)] rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 w-44 lg:w-48"
            />
          </div>
        </div>
      </div>

      {/* Candidates Table (Responsive with Sticky Column) */}
      <div className="overflow-x-auto rounded-xl border border-[var(--border-default)] bg-[var(--surface)] shadow-xs">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-[var(--border-default)] bg-[var(--subtle)]/70 text-[var(--text-secondary)] font-medium">
              <th scope="col" className="py-3 px-3 w-12 text-center">
                Rank
              </th>
              <th scope="col" className="py-3 px-4 min-w-[200px]">
                Candidate
              </th>
              <th scope="col" className="py-3 px-4 min-w-[220px]">
                Most recent role (Title only)
              </th>
              <th scope="col" className="py-3 px-4 min-w-[120px]">
                Match score
              </th>
              <th scope="col" className="py-3 px-4 min-w-[120px]">
                Tier
              </th>
              <th scope="col" className="py-3 px-4 min-w-[130px]">
                Must-have coverage
              </th>
              <th scope="col" className="py-3 px-4 min-w-[120px]">
                Verified experience
              </th>
              <th scope="col" className="py-3 px-4 min-w-[150px] text-right">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-default)]">
            {filteredCandidates.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <p className="text-sm font-medium text-[var(--text-primary)]">
                      No candidates match the filter
                    </p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Try adjusting the tier or must-have coverage criteria.
                    </p>
                    <button
                      type="button"
                      onClick={handleResetFilters}
                      className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 rounded-md transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Reset filters</span>
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              filteredCandidates.map((cand, idx) => {
                const rankNumber = idx + 1;
                const isFullCoverage =
                  cand.must_have_coverage.startsWith("7 / 7") ||
                  cand.must_have_coverage.startsWith("6 / 6");

                return (
                  <tr
                    key={cand.id}
                    className="hover:bg-[var(--subtle)] transition-colors focus-within:bg-[var(--subtle)] cursor-pointer group"
                    onClick={() => onSelectCandidate(cand.id)}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelectCandidate(cand.id);
                      }
                    }}
                    aria-label={`View dossier for ${isBlindMode ? `Candidate #${cand.code}` : cand.name}`}
                  >
                    {/* Rank */}
                    <td className="py-3 px-3 text-center font-mono font-bold text-[var(--text-secondary)]">
                      #{rankNumber}
                    </td>

                    {/* Candidate Identity (Blind Mode Masking Compliant) */}
                    <td className="py-3 px-4">
                      {isBlindMode ? (
                        <div className="flex items-center gap-1.5 font-mono font-semibold text-[var(--text-primary)]">
                          <Lock className="w-3.5 h-3.5 text-blue-500 shrink-0" aria-label="PII Masked" />
                          <span>Candidate #{cand.code}</span>
                        </div>
                      ) : (
                        <div>
                          <div className="font-semibold text-[var(--text-primary)] group-hover:text-blue-500 transition-colors">
                            {cand.name}
                          </div>
                          <div className="text-[11px] text-[var(--text-secondary)] font-mono">
                            {cand.email} · #{cand.code}
                          </div>
                        </div>
                      )}
                    </td>

                    {/* Role: Job title only, ZERO employer/company names */}
                    <td className="py-3 px-4 font-medium text-[var(--text-primary)]">
                      {cand.most_recent_role}
                    </td>

                    {/* Match score + horizontal mini-bar */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-[var(--text-primary)] font-mono w-7">
                          {cand.match_score}
                        </span>
                        <div className="w-16 bg-[var(--subtle)] h-1.5 rounded-full overflow-hidden border border-[var(--border-default)]">
                          <div
                            className={`h-full rounded-full ${
                              cand.match_score >= 85
                                ? "bg-emerald-500"
                                : cand.match_score >= 70
                                ? "bg-sky-500"
                                : cand.match_score >= 55
                                ? "bg-amber-500"
                                : "bg-red-500"
                            }`}
                            style={{ width: `${cand.match_score}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Tier badge with SVG icon */}
                    <td className="py-3 px-4">
                      <TierBadge tier={cand.tier} size="sm" />
                    </td>

                    {/* Must-have coverage */}
                    <td className="py-3 px-4">
                      <div className="inline-flex items-center gap-1 font-mono">
                        {isFullCoverage ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                        ) : (
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                        )}
                        <span
                          className={
                            isFullCoverage
                              ? "text-emerald-600 dark:text-emerald-400 font-semibold"
                              : "text-amber-600 dark:text-amber-400 font-semibold"
                          }
                        >
                          {cand.must_have_coverage}
                        </span>
                      </div>
                    </td>

                    {/* Verified experience */}
                    <td className="py-3 px-4 font-mono">
                      {cand.verified_experience === "Dates missing" ? (
                        <span className="text-red-500 font-semibold italic">Dates missing</span>
                      ) : (
                        <span className="text-[var(--text-primary)]">{cand.verified_experience}</span>
                      )}
                    </td>

                    {/* Actions: Dossier & Email buttons */}
                    <td className="py-3 px-4 text-right">
                      <div
                        className="inline-flex items-center gap-1.5"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          onClick={() => onSelectCandidate(cand.id)}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors shadow-xs"
                          aria-label={`Open Dossier for Candidate #${cand.code}`}
                        >
                          Dossier
                        </button>
                        <button
                          type="button"
                          onClick={() => onOpenEmail(cand.id)}
                          className="p-1 text-[var(--text-secondary)] hover:text-blue-500 hover:bg-[var(--subtle)] rounded transition-colors"
                          aria-label={`Draft Email for Candidate #${cand.code}`}
                          title="Open Email Center"
                        >
                          <Mail className="w-4 h-4" />
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
  );
};
