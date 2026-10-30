import React from "react";
import {
  Users,
  ArrowRight,
  Shield,
  Award,
  Layers,
  UserPlus,
} from "lucide-react";
import type { JobItem, CandidateItem } from "../../lib/mockData";

interface DashboardScreenProps {
  job: JobItem;
  candidates: CandidateItem[];
  onNavigate: (path: string) => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({
  job,
  candidates,
  onNavigate,
}) => {
  const jobCandidates = candidates.filter(
    (c) => (c.job_id || "job-backend") === job.id
  );

  const total = jobCandidates.length || job.applicants_count || 14;
  const fasttrack = jobCandidates.filter((c) => c.tier === "FastTrack").length || job.tier_counts.fasttrack;
  const interview = jobCandidates.filter((c) => c.tier === "Interview").length || job.tier_counts.interview;
  const hold = jobCandidates.filter((c) => c.tier === "Hold").length || job.tier_counts.hold;
  const reject = jobCandidates.filter((c) => c.tier === "Reject").length || job.tier_counts.reject;
  const abstained = 0;

  const topCandidate = jobCandidates[0];

  return (
    <div className="space-y-6">
      {/* Job Command Center Header */}
      <div className="p-6 rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)] flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-indigo-400">
              {job.id.toUpperCase().replace("JOB-", "REQ-")}
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {job.status}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            {job.title} — Command Center
          </h1>
          <p className="text-xs text-[var(--text-secondary)]">
            Candidates automatically ranked in descending order of score with evidence grounding.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate(`/jobs/${job.id}/candidates/add`)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg border border-[var(--border-default)] bg-[var(--bg-subtle)] hover:bg-[var(--border-default)]/60 text-[var(--text-primary)] transition-colors cursor-pointer"
          >
            <UserPlus size={14} />
            Add CVs
          </button>
          <button
            onClick={() => onNavigate(`/jobs/${job.id}/candidates`)}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors cursor-pointer"
          >
            <span>View Ranked Table</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <span className="block text-[10px] font-mono uppercase tracking-wider text-[var(--text-secondary)]">
            TOTAL RESUMES
          </span>
          <span className="text-2xl font-extrabold text-[var(--text-primary)] font-mono mt-1 block">
            {total}
          </span>
          <span className="text-[10px] text-emerald-400 font-mono">100% Parsed</span>
        </div>

        <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
          <span className="block text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold">
            ✓ FASTTRACK
          </span>
          <span className="text-2xl font-extrabold text-emerald-400 font-mono mt-1 block">
            {fasttrack}
          </span>
          <span className="text-[10px] text-[var(--text-secondary)] font-mono">Score ≥ 85</span>
        </div>

        <div className="p-4 rounded-xl border border-blue-500/20 bg-blue-500/5">
          <span className="block text-[10px] font-mono uppercase tracking-wider text-blue-400 font-semibold">
            ● INTERVIEW
          </span>
          <span className="text-2xl font-extrabold text-blue-400 font-mono mt-1 block">
            {interview}
          </span>
          <span className="text-[10px] text-[var(--text-secondary)] font-mono">Score 70–84</span>
        </div>

        <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5">
          <span className="block text-[10px] font-mono uppercase tracking-wider text-amber-400 font-semibold">
            ◔ HOLD
          </span>
          <span className="text-2xl font-extrabold text-amber-400 font-mono mt-1 block">
            {hold}
          </span>
          <span className="text-[10px] text-[var(--text-secondary)] font-mono">Score 50–69</span>
        </div>

        <div className="p-4 rounded-xl border border-rose-500/20 bg-rose-500/5">
          <span className="block text-[10px] font-mono uppercase tracking-wider text-rose-400 font-semibold">
            ✕ REJECT
          </span>
          <span className="text-2xl font-extrabold text-rose-400 font-mono mt-1 block">
            {reject}
          </span>
          <span className="text-[10px] text-[var(--text-secondary)] font-mono">Score &lt; 50</span>
        </div>

        <div className="p-4 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <span className="block text-[10px] font-mono uppercase tracking-wider text-[var(--text-secondary)]">
            ⊘ ABSTAINED
          </span>
          <span className="text-2xl font-extrabold text-[var(--text-secondary)] font-mono mt-1 block">
            {abstained}
          </span>
          <span className="text-[10px] text-[var(--text-secondary)] font-mono">Non-resumes</span>
        </div>
      </div>

      {/* Tier Distribution Bar */}
      <div className="p-5 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] space-y-3">
        <div className="flex items-center justify-between text-xs font-semibold">
          <span className="text-[var(--text-primary)]">
            Tier distribution ({total} ranked)
          </span>
          <span className="text-[var(--text-secondary)] font-mono text-[11px]">
            FastTrack {Math.round((fasttrack / (total || 1)) * 100)}% · Interview {Math.round((interview / (total || 1)) * 100)}%
          </span>
        </div>

        <div className="h-3 w-full bg-[var(--bg-subtle)] rounded-full overflow-hidden flex">
          <div
            style={{ width: `${(fasttrack / (total || 1)) * 100}%` }}
            className="bg-emerald-500 h-full"
            title={`FastTrack: ${fasttrack}`}
          />
          <div
            style={{ width: `${(interview / (total || 1)) * 100}%` }}
            className="bg-blue-500 h-full"
            title={`Interview: ${interview}`}
          />
          <div
            style={{ width: `${(hold / (total || 1)) * 100}%` }}
            className="bg-amber-500 h-full"
            title={`Hold: ${hold}`}
          />
          <div
            style={{ width: `${(reject / (total || 1)) * 100}%` }}
            className="bg-rose-500 h-full"
            title={`Reject: ${reject}`}
          />
        </div>
      </div>

      {/* Quick Action Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Top Candidate */}
        <div
          onClick={() => {
            if (topCandidate) {
              onNavigate(`/jobs/${job.id}/candidates/${topCandidate.id}`);
            } else {
              onNavigate(`/jobs/${job.id}/candidates`);
            }
          }}
          className="p-5 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-indigo-500/50 transition-colors cursor-pointer flex flex-col justify-between"
        >
          <div>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-3">
              <Award size={18} />
            </div>
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              #1 Ranked Candidate
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              {topCandidate ? `Candidate #${topCandidate.code} (${topCandidate.match_score} pts)` : "View top candidate dossier"}
            </p>
          </div>
          <span className="text-xs font-semibold text-indigo-400 inline-flex items-center gap-1 mt-4">
            Open Dossier <ArrowRight size={12} />
          </span>
        </div>

        {/* Ranked Candidates Table */}
        <div
          onClick={() => onNavigate(`/jobs/${job.id}/candidates`)}
          className="p-5 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-indigo-500/50 transition-colors cursor-pointer flex flex-col justify-between"
        >
          <div>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center mb-3">
              <Users size={18} />
            </div>
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              Ranked Candidates
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Table with must-have coverage, filters, and prestige bias suppression.
            </p>
          </div>
          <span className="text-xs font-semibold text-indigo-400 inline-flex items-center gap-1 mt-4">
            View Table ({total}) <ArrowRight size={12} />
          </span>
        </div>

        {/* Hiring Pipeline */}
        <div
          onClick={() => onNavigate(`/jobs/${job.id}/pipeline`)}
          className="p-5 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-indigo-500/50 transition-colors cursor-pointer flex flex-col justify-between"
        >
          <div>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-3">
              <Layers size={18} />
            </div>
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              Hiring Pipeline
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Kanban tracking across Screening, Interview, Assessment, Offer, and Hired.
            </p>
          </div>
          <span className="text-xs font-semibold text-indigo-400 inline-flex items-center gap-1 mt-4">
            Open Pipeline <ArrowRight size={12} />
          </span>
        </div>

        {/* Audit Log */}
        <div
          onClick={() => onNavigate(`/jobs/${job.id}/audit`)}
          className="p-5 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-indigo-500/50 transition-colors cursor-pointer flex flex-col justify-between"
        >
          <div>
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center mb-3">
              <Shield size={18} />
            </div>
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              Job Audit Log
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Cryptographically chained audit trail for every action in this role.
            </p>
          </div>
          <span className="text-xs font-semibold text-indigo-400 inline-flex items-center gap-1 mt-4">
            Inspect Log <ArrowRight size={12} />
          </span>
        </div>
      </div>
    </div>
  );
};
