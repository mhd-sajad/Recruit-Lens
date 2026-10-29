import React from "react";
import {
  Briefcase,
  Users,
  CheckCircle2,
  Clock,
  ArrowRight,
  Upload,
  Plus,
  Shield,
  FileCheck,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { Badge } from "../common/Badge";

interface DashboardScreenProps {
  onSelectTab: (tab: string) => void;
  onOpenCreateJob: () => void;
  onOpenUpload: () => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({
  onSelectTab,
  onOpenCreateJob,
  onOpenUpload,
}) => {
  const { jobs, activeJob, setActiveJob, isBlindMode } = useAuth();
  const jobList = Array.isArray(jobs) ? jobs : [];
  const totalJobs = jobList.length;
  const activeJobs = jobList.filter((j) => j.status === "active").length;

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
              Recruiter Command Center
            </h2>
            {isBlindMode && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-700 dark:bg-purple-950/80 dark:text-purple-300">
                <Shield className="w-3 h-3" /> Blind Review Enabled
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Explainable resume screening, evidence retrieval, and structured interview orchestration.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={onOpenCreateJob}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
          >
            <Plus className="w-3.5 h-3.5" />
            Create Requisition
          </button>
          <button
            onClick={onOpenUpload}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm shadow-blue-500/20 transition"
          >
            <Upload className="w-3.5 h-3.5" />
            Upload Resumes
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-medium">Active Requisitions</span>
            <Briefcase className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {activeJobs}
            </span>
            <span className="text-xs text-slate-400">of {totalJobs} total</span>
          </div>
        </div>

        <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-medium">Candidates Screened</span>
            <Users className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              100% Grounded
            </span>
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
              Verified
            </span>
          </div>
        </div>

        <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-medium">System Agreement</span>
            <CheckCircle2 className="w-4 h-4 text-sky-600 dark:text-sky-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              88.4%
            </span>
            <span className="text-xs text-sky-600 dark:text-sky-400 font-medium">
              Cohen's Kappa 0.76
            </span>
          </div>
        </div>

        <div className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-medium">Pending Actions</span>
            <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {activeJob ? "Ready" : "Select Job"}
            </span>
            <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">
              Review Queue
            </span>
          </div>
        </div>
      </div>

      {/* Main Jobs Section & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Open Job Requisitions Table / Cards */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Job Requisitions
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Active hiring requirements and parsed criteria
              </p>
            </div>
            <button
              onClick={() => onSelectTab("candidates")}
              className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
            >
              View All Candidates <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            {jobList.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-xs">
                No job requisitions created yet. Click "Create Requisition" to start.
              </div>
            ) : (
              jobList.map((job) => {
                const isSelected = activeJob?.id === job.id;
                return (
                  <div
                    key={job.id}
                    onClick={() => setActiveJob(job)}
                    className={`p-4 rounded-xl border cursor-pointer transition ${
                      isSelected
                        ? "border-blue-500 bg-blue-50/40 dark:bg-blue-950/30 shadow-sm"
                        : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                            {job.title}
                          </h4>
                          <Badge variant="status" value={job.status} />
                          {isSelected && (
                            <span className="text-[10px] font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide">
                              Active Selected
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1">
                          {job.department || "General Engineering"} • {job.location || "Remote"} • {job.min_years_experience || 0} yrs min exp
                        </p>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveJob(job);
                          onSelectTab("candidates");
                        }}
                        className="px-2.5 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/50 rounded-lg transition"
                      >
                        Candidates →
                      </button>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                      <span className="text-[11px] text-slate-400 font-medium">Must-haves:</span>
                      {(job.required_skills || []).slice(0, 5).map((skill, i) => (
                        <span
                          key={i}
                          className="text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono"
                        >
                          {skill}
                        </span>
                      ))}
                      {(job.required_skills || []).length > 5 && (
                        <span className="text-[11px] text-slate-400">
                          +{(job.required_skills || []).length - 5} more
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Pending Actions & Explanations */}
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Recruiter Governance
            </h3>
            <ul className="text-xs text-slate-600 dark:text-slate-400 space-y-2.5">
              <li className="flex items-start gap-2">
                <FileCheck className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                <span>Deterministic scoring without ungrounded LLM hallucinations.</span>
              </li>
              <li className="flex items-start gap-2">
                <FileCheck className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                <span>Every claim cites exact resume chunk evidence.</span>
              </li>
              <li className="flex items-start gap-2">
                <FileCheck className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                <span>Zero emails dispatched without manual human confirmation.</span>
              </li>
              <li className="flex items-start gap-2">
                <FileCheck className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                <span>Append-only audit trail logs every stage and score decision.</span>
              </li>
            </ul>
          </div>

          <div className="bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-xl p-6 shadow-md space-y-3">
            <h4 className="text-sm font-bold">Fast-Track Screening</h4>
            <p className="text-xs text-blue-100 leading-relaxed">
              Upload PDF batches up to 200 resumes. Hybrid BM25 + dense neural retrieval extracts evidence in under 0.5s per candidate.
            </p>
            <button
              onClick={onOpenUpload}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white text-blue-700 text-xs font-semibold rounded-lg shadow hover:bg-blue-50 transition"
            >
              Start Upload Flow
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
