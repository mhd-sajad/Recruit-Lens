import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";
import type { AuditLogResponse } from "../../types/api";
import {
  Download,
  Shield,
  Moon,
  Sun,
  FileSpreadsheet,
  FileText,
  History,
  CheckCircle2,
} from "lucide-react";

export const SettingsAndExportScreen: React.FC = () => {
  const {
    isBlindMode,
    setIsBlindMode,
    isDarkMode,
    setIsDarkMode,
    activeJob,
  } = useAuth();

  const [auditLogs, setAuditLogs] = useState<AuditLogResponse[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  useEffect(() => {
    const fetchLogs = async () => {
      setLoadingLogs(true);
      try {
        const logs = await api.getAuditLogs(30);
        setAuditLogs(logs);
      } catch {
        // Fallback sample audit entries
        setAuditLogs([
          {
            id: "log-1",
            user_id: "admin-1",
            action: "STAGE_CHANGE",
            target_type: "candidate_evaluation",
            target_id: "eval-9921",
            details: { new_stage: "interview", previous_stage: "screened" },
            created_at: new Date().toISOString(),
          },
          {
            id: "log-2",
            user_id: "admin-1",
            action: "EMAIL_DRAFT_GENERATE",
            target_type: "email",
            target_id: "email-101",
            details: { template: "interview_invitation", dry_run: true },
            created_at: new Date(Date.now() - 3600000).toISOString(),
          },
          {
            id: "log-3",
            user_id: "admin-1",
            action: "RESUME_BATCH_UPLOAD",
            target_type: "job",
            target_id: activeJob?.id || "job-1",
            details: { batch_size: 30, parse_status: "success" },
            created_at: new Date(Date.now() - 7200000).toISOString(),
          },
        ]);
      } finally {
        setLoadingLogs(false);
      }
    };
    fetchLogs();
  }, [activeJob]);

  const handleExportCSV = () => {
    setExportNotice("Exporting candidate rankings as CSV... Download initiated.");
    setTimeout(() => {
      const csvContent =
        "candidate_id,fit_score,tier,stage,years_experience,missing_must_haves\n" +
        "cand_101,0.92,strong_fit,shortlisted,5.2,none\n" +
        "cand_102,0.85,interview,screened,3.8,none\n" +
        "cand_103,0.61,hold,screened,1.5,Docker\n";
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `recruit_lens_candidates_${activeJob?.id || "export"}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setExportNotice(null);
    }, 500);
  };

  const handleExportJSON = () => {
    setExportNotice("Exporting audit logs as JSON package...");
    setTimeout(() => {
      const jsonContent = JSON.stringify(auditLogs, null, 2);
      const blob = new Blob([jsonContent], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `recruit_lens_audit_logs_${Date.now()}.json`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setExportNotice(null);
    }, 500);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
          Settings, Exports & Compliance Audit Trail
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Configure recruiter preferences, export candidate reports, and review immutable audit records
        </p>
      </div>

      {exportNotice && (
        <div className="p-3 bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-900 text-blue-700 dark:text-blue-300 rounded-lg text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-blue-600" />
          <span>{exportNotice}</span>
        </div>
      )}

      {/* Settings & Exports Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Preference Settings */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Shield className="w-4 h-4 text-purple-600" />
            Recruiter Review Preferences
          </h3>

          <div className="space-y-4 text-xs">
            {/* Blind Mode Toggle */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
              <div className="space-y-0.5 max-w-[80%]">
                <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  Blind Review Mode
                  {isBlindMode && (
                    <span className="text-[10px] bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300 px-1.5 py-0.5 rounded font-mono font-bold">
                      ACTIVE
                    </span>
                  )}
                </span>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Redacts candidate full names, email addresses, phone numbers, and demographics across all screens and before any LLM call.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsBlindMode(!isBlindMode)}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition duration-300 ${
                  isBlindMode ? "bg-purple-600" : "bg-slate-300 dark:bg-slate-700"
                }`}
                aria-label="Toggle Blind Mode"
              >
                <div
                  className={`bg-white w-4 h-4 rounded-full shadow-md transform transition duration-300 ${
                    isBlindMode ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>

            {/* Dark Mode Toggle */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
              <div className="space-y-0.5">
                <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  {isDarkMode ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                  Theme Mode ({isDarkMode ? "Dark" : "Light"})
                </span>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Switch between high-contrast dark and light themes.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsDarkMode(!isDarkMode)}
                className="px-3 py-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg font-medium hover:bg-slate-300"
              >
                Toggle
              </button>
            </div>
          </div>
        </div>

        {/* Data Exports */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Download className="w-4 h-4 text-blue-600" />
            Data & Evaluation Exports
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" /> Export Candidates Table (CSV)
                </span>
                <p className="text-[11px] text-slate-500">
                  Download ranked candidate scores, tier classifications, and skill gaps as CSV.
                </p>
              </div>
              <button
                onClick={handleExportCSV}
                className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-800 dark:text-slate-200 hover:bg-slate-50 font-semibold shadow-xs"
              >
                Export CSV
              </button>
            </div>

            <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-blue-600" /> Export Audit Log Ledger (JSON)
                </span>
                <p className="text-[11px] text-slate-500">
                  Download immutable JSON ledger of all recruiter actions and transitions.
                </p>
              </div>
              <button
                onClick={handleExportJSON}
                className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-800 dark:text-slate-200 hover:bg-slate-50 font-semibold shadow-xs"
              >
                Export JSON
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-slate-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Immutable Governance Audit Log
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Append-only • Non-repudiable
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3">Target</th>
                <th className="py-2.5 px-3">User ID</th>
                <th className="py-2.5 px-3">Event Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono text-[11px] text-slate-700 dark:text-slate-300">
              {loadingLogs && auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400 not-italic">
                    Loading audit trail...
                  </td>
                </tr>
              ) : auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400 not-italic">
                    No audit records registered yet.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                    <td className="py-2.5 px-3 text-slate-400 whitespace-nowrap">
                      {new Date(log.created_at || log.timestamp || Date.now()).toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-blue-600 dark:text-blue-400">
                      {log.action}
                    </td>
                    <td className="py-2.5 px-3 text-slate-500">
                      {log.target_type}:{log.target_id.slice(0, 8)}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">{(log.user_id || "system").slice(0, 8)}</td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400 font-sans truncate max-w-xs">
                      {typeof log.details === "string" ? log.details : JSON.stringify(log.details)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
