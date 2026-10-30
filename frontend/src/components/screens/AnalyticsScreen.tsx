import React from "react";
import { BarChart3 } from "lucide-react";

export const AnalyticsScreen: React.FC = () => {
  const funnelStages = [
    { name: "Screened CVs", count: 22, pct: "100%", color: "bg-blue-600" },
    { name: "Interview Invited", count: 9, pct: "40.9%", color: "bg-sky-500" },
    { name: "Technical Assessment", count: 5, pct: "22.7%", color: "bg-indigo-500" },
    { name: "Offer Extended", count: 2, pct: "9.1%", color: "bg-emerald-500" },
  ];

  const tierDistribution = [
    { tier: "FastTrack", count: 6, pct: 27, color: "bg-emerald-500" },
    { tier: "Interview", count: 8, pct: 36, color: "bg-sky-500" },
    { tier: "Hold", count: 5, pct: 23, color: "bg-amber-500" },
    { tier: "Reject", count: 3, pct: 14, color: "bg-red-500" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[var(--border-default)] pb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-500" />
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Screening Analytics & System Metrics
          </h1>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          Objective evaluation telemetry, recruiter agreement rates, and latency benchmarks.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-[var(--border-default)] bg-[var(--surface)] space-y-1 shadow-xs">
          <span className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase">
            Recruiter Agreement Rate
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-500">94.2%</span>
            <span className="text-xs text-[var(--text-secondary)]">on tier decisions</span>
          </div>
          <p className="text-[11px] text-[var(--text-secondary)] pt-1">
            Measured against human senior technical recruiter audits.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-[var(--border-default)] bg-[var(--surface)] space-y-1 shadow-xs">
          <span className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase">
            p95 Retrieval Latency
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-[var(--text-primary)]">420 ms</span>
            <span className="text-xs text-emerald-500 font-medium">under 500 ms SLA</span>
          </div>
          <p className="text-[11px] text-[var(--text-secondary)] pt-1">
            BM25 + quantized dense MiniLM embeddings.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-[var(--border-default)] bg-[var(--surface)] space-y-1 shadow-xs">
          <span className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase">
            Evidence Traceability
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-blue-500">100%</span>
            <span className="text-xs text-[var(--text-secondary)]">citations verified</span>
          </div>
          <p className="text-[11px] text-[var(--text-secondary)] pt-1">
            Zero hallucinated claims; every sentence grounded in CV chunks.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-[var(--border-default)] bg-[var(--surface)] space-y-1 shadow-xs">
          <span className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase">
            Audit Chain Health
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-500">Intact</span>
            <span className="text-xs text-emerald-500 font-medium">SHA-256</span>
          </div>
          <p className="text-[11px] text-[var(--text-secondary)] pt-1">
            Genesis block through latest batch fully validated.
          </p>
        </div>
      </div>

      {/* Funnel & Tier Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Recruitment Funnel Card */}
        <div className="p-5 rounded-xl border border-[var(--border-default)] bg-[var(--surface)] shadow-xs space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            Hiring Pipeline Progression
          </h2>
          <div className="space-y-3">
            {funnelStages.map((stage, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-[var(--text-primary)]">{stage.name}</span>
                  <span className="font-mono text-[var(--text-secondary)]">
                    {stage.count} candidates ({stage.pct})
                  </span>
                </div>
                <div className="w-full bg-[var(--subtle)] h-2 rounded-full overflow-hidden">
                  <div
                    className={`${stage.color} h-full rounded-full transition-all`}
                    style={{ width: stage.pct }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Tier Distribution Card */}
        <div className="p-5 rounded-xl border border-[var(--border-default)] bg-[var(--surface)] shadow-xs space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            Candidate Tier Distribution
          </h2>
          <div className="space-y-3">
            {tierDistribution.map((t, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-[var(--text-primary)]">{t.tier}</span>
                  <span className="font-mono text-[var(--text-secondary)]">
                    {t.count} ({t.pct}%)
                  </span>
                </div>
                <div className="w-full bg-[var(--subtle)] h-2 rounded-full overflow-hidden">
                  <div
                    className={`${t.color} h-full rounded-full transition-all`}
                    style={{ width: `${t.pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
