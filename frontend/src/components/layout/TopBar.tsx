import React from "react";
import { ArrowLeft } from "lucide-react";
import { BrandLogo } from "../common/BrandLogo";
import type { AppRoute } from "../../lib/router";
import type { JobItem } from "../../lib/mockData";

interface TopBarProps {
  currentRoute: AppRoute;
  activeJob: JobItem | null;
  onNavigate: (path: string) => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  currentRoute,
  activeJob,
  onNavigate,
}) => {
  // Determine parent info
  let hasParent = true;
  let parentLabel = "Requisitions";
  let parentPath = "/requisitions";

  switch (currentRoute.name) {
    case "requisitions":
      hasParent = false;
      parentLabel = "";
      parentPath = "/";
      break;
    case "requisitions-new":
      parentLabel = "Requisitions";
      parentPath = "/requisitions";
      break;
    case "audit":
    case "settings":
      parentLabel = "Requisitions";
      parentPath = "/requisitions";
      break;
    case "job-dashboard":
      parentLabel = "Requisitions";
      parentPath = "/requisitions";
      break;
    case "job-candidates":
    case "job-pipeline":
    case "job-audit":
      parentLabel = "Job Dashboard";
      parentPath = `/jobs/${currentRoute.jobId}`;
      break;
    case "job-candidates-add":
      parentLabel = "Ranked Candidates";
      parentPath = `/jobs/${currentRoute.jobId}/candidates`;
      break;
    case "job-candidate-dossier":
      parentLabel = "Ranked Candidates";
      parentPath = `/jobs/${currentRoute.jobId}/candidates`;
      break;
    case "job-candidate-email":
      parentLabel = "Candidate Dossier";
      parentPath = `/jobs/${currentRoute.jobId}/candidates/${currentRoute.candidateId}`;
      break;
    default:
      hasParent = false;
      parentLabel = "";
      parentPath = "/";
  }

  const isInsideJob =
    currentRoute.name === "job-dashboard" ||
    currentRoute.name === "job-candidates" ||
    currentRoute.name === "job-candidates-add" ||
    currentRoute.name === "job-candidate-dossier" ||
    currentRoute.name === "job-candidate-email" ||
    currentRoute.name === "job-pipeline" ||
    currentRoute.name === "job-audit";

  return (
    <header className="h-[68px] border-b border-[var(--border-default)] bg-[var(--bg-surface)] px-6 flex items-center justify-between sticky top-0 z-30 select-none">
      {/* Left: Back Arrow with Parent Page Label + Brand Logo */}
      <div className="flex items-center gap-3.5">
        {hasParent && (
          <>
            <button
              onClick={() => onNavigate(parentPath)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer py-1.5 px-2.5 rounded-lg hover:bg-[var(--bg-subtle)]"
              aria-label={`Back to ${parentLabel}`}
            >
              <ArrowLeft size={16} />
              <span>{parentLabel}</span>
            </button>
            <div className="h-5 w-px bg-[var(--border-default)] hidden sm:block" />
          </>
        )}

        {/* Recruit Lens Wordmark (always links Home "/") */}
        <button
          onClick={() => onNavigate("/")}
          className="flex items-center text-left group cursor-pointer focus:outline-none"
          aria-label="Recruit Lens Home"
        >
          <BrandLogo size="md" />
        </button>
      </div>

      {/* Right: Active Job Pill (when inside a job) */}
      <div className="flex items-center gap-3">
        {isInsideJob && activeJob && (
          <div
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-xs font-mono max-w-[280px] sm:max-w-md truncate"
            title={`${activeJob.id.toUpperCase()} · ${activeJob.title}`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
            <span className="font-semibold text-indigo-200 shrink-0">
              Active job:
            </span>
            <span className="truncate">
              {activeJob.id.toUpperCase().replace("JOB-", "REQ-")} · {activeJob.title}
            </span>
          </div>
        )}
      </div>
    </header>
  );
};
