import React from "react";
import {
  Briefcase,
  Shield,
  Settings,
  HelpCircle,
  Users,
  UserPlus,
  Award,
  Mail,
  Layers,
  ArrowLeft,
  Sun,
  Moon,
  LogOut,
  LayoutDashboard,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { cn } from "../../lib/utils";
import type { AppRoute } from "../../lib/router";
import type { JobItem, CandidateItem } from "../../lib/mockData";

interface SidebarProps {
  currentRoute: AppRoute;
  jobsList: JobItem[];
  selectedJob: JobItem | null;
  candidatesList: CandidateItem[];
  onNavigate: (path: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentRoute,
  jobsList,
  selectedJob,
  candidatesList,
  onNavigate,
}) => {
  const { user, isDarkMode, setIsDarkMode, logout } = useAuth();

  const isInsideJob =
    currentRoute.name === "job-dashboard" ||
    currentRoute.name === "job-candidates" ||
    currentRoute.name === "job-candidates-add" ||
    currentRoute.name === "job-candidate-dossier" ||
    currentRoute.name === "job-candidate-email" ||
    currentRoute.name === "job-pipeline" ||
    currentRoute.name === "job-audit";

  const currentJobId = isInsideJob && "jobId" in currentRoute ? currentRoute.jobId : selectedJob?.id || "job-backend";
  const activeJob = jobsList.find((j) => j.id === currentJobId) || selectedJob || jobsList[0];

  // Candidates scoped to activeJob
  const jobCandidates = candidatesList.filter(
    (c) => (c.job_id || "job-backend") === (activeJob?.id || "job-backend")
  );
  const topCandidate = jobCandidates[0];

  const emailCandidateId =
    currentRoute.name === "job-candidate-email"
      ? currentRoute.candidateId
      : currentRoute.name === "job-candidate-dossier"
      ? currentRoute.candidateId
      : topCandidate?.id || "cand-6299";

  return (
    <aside
      className="w-60 shrink-0 h-screen sticky top-0 flex flex-col bg-[var(--bg-surface)] border-r border-[var(--border-default)] select-none text-[var(--text-primary)] transition-colors z-20"
      aria-label="Main Navigation"
    >
      {/* Navigation Body */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
        {isInsideJob ? (
          /* INSIDE A JOB SIDEBAR */
          <div className="space-y-3">
            {/* Top link: ← Back to Requisitions */}
            <button
              onClick={() => onNavigate("/requisitions")}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-indigo-400 hover:bg-indigo-500/10 transition-colors cursor-pointer text-left"
            >
              <ArrowLeft size={14} />
              <span>Back to Requisitions</span>
            </button>

            {/* Active Job Heading Card */}
            {activeJob && (
              <div className="px-2.5 py-2 rounded-lg bg-[var(--bg-subtle)] border border-[var(--border-default)]">
                <span className="text-[9px] font-mono uppercase tracking-wider text-[var(--text-secondary)] block mb-0.5">
                  JOB WORKSPACE
                </span>
                <span className="text-[11px] font-mono font-bold text-indigo-300 block">
                  {activeJob.id.toUpperCase().replace("JOB-", "REQ-")}
                </span>
                <span className="text-xs font-semibold text-[var(--text-primary)] line-clamp-2 leading-tight">
                  {activeJob.title}
                </span>
              </div>
            )}

            {/* Job Nav Links */}
            <nav className="space-y-0.5" aria-label="Job Navigation">
              {/* 1. Job Dashboard */}
              <button
                onClick={() => onNavigate(`/jobs/${currentJobId}`)}
                aria-current={currentRoute.name === "job-dashboard" ? "page" : undefined}
                className={cn(
                  "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "job-dashboard"
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <LayoutDashboard size={15} />
                <span>Job Dashboard</span>
              </button>

              {/* 2. Ranked Candidates */}
              <button
                onClick={() => onNavigate(`/jobs/${currentJobId}/candidates`)}
                aria-current={currentRoute.name === "job-candidates" ? "page" : undefined}
                className={cn(
                  "w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "job-candidates"
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Users size={15} />
                  <span>Ranked Candidates</span>
                </div>
                <span
                  className={cn(
                    "px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold",
                    currentRoute.name === "job-candidates"
                      ? "bg-white/20 text-white"
                      : "bg-[var(--bg-subtle)] text-[var(--text-secondary)] border border-[var(--border-default)]"
                  )}
                >
                  {jobCandidates.length || activeJob?.applicants_count || 0}
                </span>
              </button>

              {/* 3. Add Candidates */}
              <button
                onClick={() => onNavigate(`/jobs/${currentJobId}/candidates/add`)}
                aria-current={currentRoute.name === "job-candidates-add" ? "page" : undefined}
                className={cn(
                  "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "job-candidates-add"
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <UserPlus size={15} />
                <span>Add Candidates</span>
              </button>

              {/* 4. Top Candidate */}
              <button
                onClick={() => {
                  if (topCandidate) {
                    onNavigate(`/jobs/${currentJobId}/candidates/${topCandidate.id}`);
                  } else {
                    onNavigate(`/jobs/${currentJobId}/candidates`);
                  }
                }}
                aria-current={
                  currentRoute.name === "job-candidate-dossier" &&
                  topCandidate &&
                  currentRoute.candidateId === topCandidate.id
                    ? "page"
                    : undefined
                }
                className={cn(
                  "w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "job-candidate-dossier" &&
                    topCandidate &&
                    currentRoute.candidateId === topCandidate.id
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Award size={15} />
                  <span>Top Candidate</span>
                </div>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  #1 Top
                </span>
              </button>

              {/* 5. Email Center */}
              <button
                onClick={() => onNavigate(`/jobs/${currentJobId}/candidates/${emailCandidateId}/email`)}
                aria-current={currentRoute.name === "job-candidate-email" ? "page" : undefined}
                className={cn(
                  "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "job-candidate-email"
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <Mail size={15} />
                <span>Email Center</span>
              </button>

              {/* 6. Hiring Pipeline */}
              <button
                onClick={() => onNavigate(`/jobs/${currentJobId}/pipeline`)}
                aria-current={currentRoute.name === "job-pipeline" ? "page" : undefined}
                className={cn(
                  "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "job-pipeline"
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <Layers size={15} />
                <span>Hiring Pipeline</span>
              </button>

              {/* 7. Job Audit Log */}
              <button
                onClick={() => onNavigate(`/jobs/${currentJobId}/audit`)}
                aria-current={currentRoute.name === "job-audit" ? "page" : undefined}
                className={cn(
                  "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "job-audit"
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <Shield size={15} />
                <span>Job Audit Log</span>
              </button>
            </nav>
          </div>
        ) : (
          /* OUTSIDE A JOB SIDEBAR (Requisitions, All-jobs Audit, Settings) */
          <div className="space-y-3">
            <div className="px-2 pt-1">
              <span className="text-[9px] font-mono uppercase tracking-widest text-[var(--text-secondary)]">
                WORKSPACE
              </span>
            </div>

            <nav className="space-y-0.5" aria-label="Workspace Navigation">
              {/* 1. Requisitions */}
              <button
                onClick={() => onNavigate("/requisitions")}
                aria-current={currentRoute.name === "requisitions" ? "page" : undefined}
                className={cn(
                  "w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "requisitions"
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Briefcase size={15} />
                  <span>Requisitions</span>
                </div>
                <span
                  className={cn(
                    "px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold",
                    currentRoute.name === "requisitions"
                      ? "bg-white/20 text-white"
                      : "bg-[var(--bg-subtle)] text-[var(--text-secondary)] border border-[var(--border-default)]"
                  )}
                >
                  {jobsList.length}
                </span>
              </button>

              {/* 2. Audit Log (All Jobs) */}
              <button
                onClick={() => onNavigate("/audit")}
                aria-current={currentRoute.name === "audit" ? "page" : undefined}
                className={cn(
                  "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "audit"
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <Shield size={15} />
                <span>Audit Log</span>
              </button>

              {/* 3. Settings */}
              <button
                onClick={() => onNavigate("/settings")}
                aria-current={currentRoute.name === "settings" ? "page" : undefined}
                className={cn(
                  "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer",
                  currentRoute.name === "settings"
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                )}
              >
                <Settings size={15} />
                <span>Settings</span>
              </button>
            </nav>
          </div>
        )}
      </div>

      {/* Bottom Block */}
      <div className="p-3 border-t border-[var(--border-default)] space-y-2 bg-[var(--bg-surface)]">
        {/* How it Works link */}
        <button
          onClick={() => onNavigate("/how-it-works")}
          className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors cursor-pointer text-left"
        >
          <HelpCircle size={15} />
          <span>How it Works</span>
        </button>

        {/* If inside job, also show Settings in bottom block */}
        {isInsideJob && (
          <button
            onClick={() => onNavigate("/settings")}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors cursor-pointer text-left"
          >
            <Settings size={15} />
            <span>Settings</span>
          </button>
        )}

        {/* Recruiter Profile */}
        <div className="p-2 rounded-lg bg-[var(--bg-subtle)] border border-[var(--border-default)] flex items-center justify-between">
          <div className="flex flex-col min-w-0 pr-1">
            <span className="text-[10px] font-mono text-indigo-400 font-semibold uppercase tracking-wider">
              Recruiter
            </span>
            <span className="text-xs font-medium text-[var(--text-primary)] truncate" title={user?.email || "admin@recruitlens.local"}>
              {user?.email || "admin@recruitlens.local"}
            </span>
          </div>
          <button
            onClick={logout}
            className="p-1 rounded text-[var(--text-secondary)] hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer shrink-0"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={14} />
          </button>
        </div>

        {/* Theme Toggle: Light / Dark */}
        <div className="flex border border-[var(--border-default)] rounded-lg p-0.5 bg-[var(--bg-subtle)]">
          <button
            type="button"
            onClick={() => setIsDarkMode(false)}
            className={cn(
              "flex-1 flex items-center justify-center gap-1.5 py-1 text-[11px] font-medium rounded-md transition-colors cursor-pointer",
              !isDarkMode
                ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs font-semibold"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            )}
            aria-label="Switch to Light Theme"
          >
            <Sun size={12} />
            <span>Light</span>
          </button>
          <button
            type="button"
            onClick={() => setIsDarkMode(true)}
            className={cn(
              "flex-1 flex items-center justify-center gap-1.5 py-1 text-[11px] font-medium rounded-md transition-colors cursor-pointer",
              isDarkMode
                ? "bg-indigo-600 text-white shadow-xs font-semibold"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            )}
            aria-label="Switch to Dark Theme"
          >
            <Moon size={12} />
            <span>Dark</span>
          </button>
        </div>
      </div>
    </aside>
  );
};
