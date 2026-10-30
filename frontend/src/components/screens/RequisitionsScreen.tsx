import React, { useState } from "react";
import { Plus, ArrowRight, Loader2 } from "lucide-react";
import { TierBadge } from "../common/TierBadge";
import { Skeleton } from "../common/Skeleton";
import type { JobItem } from "../../lib/mockData";

interface RequisitionsScreenProps {
  jobs: JobItem[];
  isLoading?: boolean;
  onSelectJob: (job: JobItem) => void;
  onCreateJob: () => void;
}

export const RequisitionsScreen: React.FC<RequisitionsScreenProps> = ({
  jobs,
  isLoading = false,
  onSelectJob,
  onCreateJob,
}) => {
  const [statusFilter, setStatusFilter] = useState<"All" | "Active" | "Closed">("Active");

  const filteredJobs = jobs.filter((job) => {
    if (statusFilter === "All") return true;
    if (statusFilter === "Active")
      return job.status === "Active" || job.status === "Draft" || job.status === "Ingesting";
    return job.status === "Closed";
  });

  const totalCandidates = jobs.reduce((sum, j) => sum + j.applicants_count, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--border-default)] pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Requisitions
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            {jobs.length} requisitions · {totalCandidates} candidates screened
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Active / Closed Filter Tabs */}
          <div className="inline-flex rounded-lg border border-[var(--border-default)] bg-[var(--surface)] p-1">
            {(["Active", "Closed", "All"] as const).map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => setStatusFilter(filter)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  statusFilter === filter
                    ? "bg-blue-600 text-white shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                {filter}
              </button>
            ))}
          </div>

          {/* Primary Action: + Create Requisition */}
          <button
            type="button"
            onClick={onCreateJob}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-[var(--surface)] cursor-pointer"
          >
            <Plus className="w-4 h-4 stroke-[2.5]" aria-hidden="true" />
            <span>Create Requisition</span>
          </button>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* First Tile: Dashed-border Create New Job Tile */}
        <button
          type="button"
          onClick={onCreateJob}
          className="group flex flex-col items-center justify-center min-h-[220px] rounded-xl border-2 border-dashed border-[var(--border-default)] hover:border-blue-500 bg-[var(--surface)]/50 hover:bg-blue-500/5 p-6 text-center transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Create New Job Requisition"
        >
          <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-500 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
            <Plus className="w-6 h-6 stroke-[2]" aria-hidden="true" />
          </div>
          <span className="text-sm font-semibold text-[var(--text-primary)] group-hover:text-blue-500 transition-colors">
            + Create New Job Requisition
          </span>
          <span className="text-xs text-[var(--text-secondary)] mt-1.5">
            Paste a JD · bulk-upload CVs
          </span>
        </button>

        {/* Loading Skeleton Cards */}
        {isLoading && (
          <>
            <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 space-y-4">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-9 w-full mt-4" />
            </div>
            <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 space-y-4">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-9 w-full mt-4" />
            </div>
          </>
        )}

        {/* Real Job Cards */}
        {!isLoading &&
          filteredJobs.map((job) => {
            const { tier_counts, applicants_count, top_score, top_tier } = job;
            const totalTiers =
              tier_counts.fasttrack + tier_counts.interview + tier_counts.hold + tier_counts.reject || 1;

            const pctFastTrack = (tier_counts.fasttrack / totalTiers) * 100;
            const pctInterview = (tier_counts.interview / totalTiers) * 100;
            const pctHold = (tier_counts.hold / totalTiers) * 100;
            const pctReject = (tier_counts.reject / totalTiers) * 100;

            return (
              <div
                key={job.id}
                className="flex flex-col justify-between rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-xs hover:border-slate-500 dark:hover:border-slate-600 transition-all"
              >
                <div>
                  {/* Header Row */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h2 className="text-base font-semibold text-[var(--text-primary)] line-clamp-1">
                        {job.title}
                      </h2>
                      <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                        {job.department} · Created {job.created_at}
                      </p>
                    </div>
                    <span
                      className={`px-2 py-0.5 text-[11px] font-medium rounded-full ${
                        job.status === "Active"
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                          : job.status === "Ingesting"
                          ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/30"
                          : job.status === "Draft"
                          ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                          : "bg-slate-500/15 text-slate-500 border border-slate-500/30"
                      }`}
                    >
                      {job.status}
                    </span>
                  </div>

                  {/* Ingesting State Banner if in flight */}
                  {job.is_ingesting ? (
                    <div className="mt-4 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                      <div className="flex items-center justify-between text-xs text-blue-600 dark:text-blue-400 font-medium mb-1.5">
                        <span className="flex items-center gap-1.5">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Parsing & indexing CVs · {job.ingest_progress?.current || 13} of{" "}
                          {job.ingest_progress?.total || 21}
                        </span>
                        <span>
                          {Math.round(
                            ((job.ingest_progress?.current || 13) /
                              (job.ingest_progress?.total || 21)) *
                              100
                          )}
                          %
                        </span>
                      </div>
                      <div className="w-full bg-[var(--subtle)] h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-blue-600 h-full rounded-full transition-all duration-300 animate-pulse"
                          style={{
                            width: `${
                              ((job.ingest_progress?.current || 13) /
                                (job.ingest_progress?.total || 21)) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  ) : (
                    /* Normal Metrics Line */
                    <div className="mt-4">
                      <div className="flex items-center justify-between text-xs mb-2">
                        <span className="text-[var(--text-secondary)]">
                          {applicants_count} applicants
                        </span>
                        {applicants_count > 0 ? (
                          <span className="font-medium text-[var(--text-primary)] inline-flex items-center gap-1.5">
                            Top match <span className="font-bold">{top_score}</span>
                            <TierBadge tier={top_tier} size="sm" />
                          </span>
                        ) : (
                          <span className="text-[var(--text-secondary)] italic">
                            Awaiting CV uploads
                          </span>
                        )}
                      </div>

                      {/* Segmented Mini-bar */}
                      {applicants_count > 0 ? (
                        <>
                          <div
                            className="w-full h-2 rounded-full overflow-hidden flex bg-[var(--subtle)] border border-[var(--border-default)]"
                            role="progressbar"
                            aria-label={`Tier distribution for ${job.title}`}
                          >
                            <div
                              style={{ width: `${pctFastTrack}%` }}
                              className="bg-emerald-500 transition-all"
                              title={`FastTrack: ${tier_counts.fasttrack}`}
                            />
                            <div
                              style={{ width: `${pctInterview}%` }}
                              className="bg-sky-500 transition-all"
                              title={`Interview: ${tier_counts.interview}`}
                            />
                            <div
                              style={{ width: `${pctHold}%` }}
                              className="bg-amber-500 transition-all"
                              title={`Hold: ${tier_counts.hold}`}
                            />
                            <div
                              style={{ width: `${pctReject}%` }}
                              className="bg-red-500 transition-all"
                              title={`Reject: ${tier_counts.reject}`}
                            />
                          </div>

                          {/* Text Legend below the bar */}
                          <p className="text-[11px] text-[var(--text-secondary)] font-mono mt-2">
                            {tier_counts.fasttrack} FastTrack · {tier_counts.interview} Interview ·{" "}
                            {tier_counts.hold} Hold · {tier_counts.reject} Reject
                          </p>
                        </>
                      ) : (
                        <div className="text-xs text-[var(--text-secondary)] py-2">
                          No candidates processed yet.
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Action Row */}
                <div className="mt-5 pt-4 border-t border-[var(--border-default)]">
                  <button
                    type="button"
                    onClick={() => onSelectJob(job)}
                    className="w-full inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 rounded-lg transition-colors group cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <span>View ranked candidates</span>
                    <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
};
