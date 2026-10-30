import React, { useState, useRef } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Lock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Copy,
  RotateCcw,
  Sliders,
  FileText,
  Mail,
} from "lucide-react";
import { TierBadge } from "../common/TierBadge";
import { ScoreGauge } from "../common/ScoreGauge";
import { CitationPill } from "../common/CitationPill";
import { useAuth } from "../../context/AuthContext";
import type { CandidateDossier, CandidateItem } from "../../lib/mockData";

interface CandidateDossierScreenProps {
  dossier: CandidateDossier;
  candidatesList: CandidateItem[];
  onBack: () => void;
  onNextCandidate: (nextId: string) => void;
  onOpenEmail: (candidateId: string) => void;
}

export const CandidateDossierScreen: React.FC<CandidateDossierScreenProps> = ({
  dossier,
  candidatesList = [],
  onBack,
  onNextCandidate,
  onOpenEmail,
}) => {
  const { isBlindMode } = useAuth();
  if (!dossier || !dossier.candidate) {
    return (
      <div className="p-8 text-center text-xs text-[var(--text-secondary)]">
        Candidate dossier not found.
      </div>
    );
  }
  const { candidate } = dossier;
  const score_contributions = dossier.score_contributions || [];
  const skills_grouped = dossier.skills || { matched: [], inferred: [], missing: [] };
  const citations = dossier.citations || [];
  const interview_questions = dossier.interview_questions || { skill_verification: [], gap_probing: [] };

  const briefingList: Array<{ sentence: string; citation_id: string }> =
    dossier.briefing && Array.isArray(dossier.briefing.sentences)
      ? dossier.briefing.sentences.map((s) => ({
          sentence: s.text,
          citation_id: s.citation_ids[0] ?? "c_01",
        }))
      : [];

  // Active citation pill state & scrolling
  const [activeCitationId, setActiveCitationId] = useState<string | null>("c_01");
  const [screenReaderAnnouncement, setScreenReaderAnnouncement] = useState<string>("");
  const evidenceContainerRef = useRef<HTMLDivElement>(null);
  const citationElementsRef = useRef<Map<string, HTMLElement>>(new Map());

  // What-if simulator state
  const [simAddCassandra, setSimAddCassandra] = useState(false);
  const [simAddYearExp, setSimAddYearExp] = useState(false);

  // Responsive tabs for mobile/tablet
  const [activeTab, setActiveTab] = useState<"score" | "evidence" | "prep">("evidence");

  // Candidate rank in list
  const currentIndex = candidatesList.findIndex((c) => c.id === candidate.id);
  const currentRank = currentIndex >= 0 ? currentIndex + 1 : 1;
  const totalCount = candidatesList.length;

  const nextCandidateId =
    currentIndex >= 0 && currentIndex < candidatesList.length - 1
      ? candidatesList[currentIndex + 1]?.id
      : candidatesList[0]?.id;

  // Compute what-if simulation delta
  const baseScore = candidate.match_score;
  const simDelta = (simAddCassandra ? 5 : 0) + (simAddYearExp ? 2 : 0);
  const simulatedScore = Math.min(100, baseScore + simDelta);
  const isSimulating = simDelta !== 0;

  // Citation click handler with auto-scroll and aria-live announcement
  const handleCitationClick = (citationId: string) => {
    setActiveCitationId(citationId);
    const targetEl = citationElementsRef.current.get(citationId);
    if (targetEl && typeof targetEl.scrollIntoView === "function") {
      targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    const foundCitation = citations.find((c) => c.id === citationId);
    if (foundCitation) {
      setScreenReaderAnnouncement(
        `Scrolled to evidence chunk ${foundCitation.id}: ${foundCitation.text_snippet}`
      );
    }
  };

  // Reset simulator
  const handleResetSimulator = () => {
    setSimAddCassandra(false);
    setSimAddYearExp(false);
  };

  return (
    <div className="space-y-5">
      {/* Hidden Live Region for Accessibility */}
      <div
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {screenReaderAnnouncement}
      </div>

      {/* Top Bar Navigation & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--border-default)] pb-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--subtle)] rounded-md border border-[var(--border-default)] transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            aria-label="Back to candidate table"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Candidates</span>
          </button>

          <div className="h-4 w-px bg-[var(--border-default)] hidden sm:block" />

          {/* Candidate Identifier */}
          <div className="flex items-center gap-2">
            {isBlindMode ? (
              <div className="flex items-center gap-1.5 font-mono font-bold text-base text-[var(--text-primary)]">
                <Lock className="w-4 h-4 text-blue-500 shrink-0" aria-label="PII Masked" />
                <span>Candidate #{candidate.code}</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-[var(--text-primary)]">
                  {candidate.name}
                </h1>
                <span className="text-xs font-mono text-[var(--text-secondary)]">
                  (#{candidate.code})
                </span>
              </div>
            )}

            <span className="text-xs font-mono px-2 py-0.5 rounded bg-[var(--subtle)] text-[var(--text-secondary)] border border-[var(--border-default)]">
              #{currentRank} of {totalCount}
            </span>

            <TierBadge tier={candidate.tier} size="sm" />
          </div>
        </div>

        {/* Right Action buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onOpenEmail(candidate.id)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] bg-[var(--surface)] hover:bg-[var(--subtle)] border border-[var(--border-default)] rounded-md transition-colors"
          >
            <Mail className="w-3.5 h-3.5" />
            <span>Draft Email</span>
          </button>

          {nextCandidateId && (
            <button
              type="button"
              onClick={() => onNextCandidate(nextCandidateId)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors shadow-xs"
            >
              <span>Next candidate</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Mobile / Tablet Tab Switcher */}
      <div className="flex lg:hidden rounded-lg border border-[var(--border-default)] bg-[var(--surface)] p-1">
        <button
          type="button"
          onClick={() => setActiveTab("score")}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md text-center transition-colors ${
            activeTab === "score"
              ? "bg-blue-600 text-white font-semibold"
              : "text-[var(--text-secondary)]"
          }`}
        >
          Score & Breakdown
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("evidence")}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md text-center transition-colors ${
            activeTab === "evidence"
              ? "bg-blue-600 text-white font-semibold"
              : "text-[var(--text-secondary)]"
          }`}
        >
          AI Briefing & Evidence
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("prep")}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md text-center transition-colors ${
            activeTab === "prep"
              ? "bg-blue-600 text-white font-semibold"
              : "text-[var(--text-secondary)]"
          }`}
        >
          Simulator & Questions
        </button>
      </div>

      {/* 3-Column Responsive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* COLUMN 1: Score & Breakdown (30% on lg -> 4 cols) */}
        <div
          className={`lg:col-span-4 space-y-4 ${
            activeTab === "score" ? "block" : "hidden lg:block"
          }`}
        >
          {/* Match Score Card */}
          <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 text-center shadow-xs">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-4">
              Match Score
            </h2>

            <div className="flex flex-col items-center">
              <ScoreGauge score={candidate.match_score} size={110} strokeWidth={9} />
              <div className="mt-3">
                <TierBadge tier={candidate.tier} />
              </div>
              <p className="text-xs font-medium text-[var(--text-primary)] mt-3">
                {candidate.most_recent_role}
              </p>
              <p className="text-[11px] text-[var(--text-secondary)] font-mono mt-0.5">
                {candidate.verified_experience} verified experience
              </p>
            </div>
          </div>

          {/* Why This Score Card (Signed Contributions) */}
          <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-xs">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-3">
              Why This Score (Additive Contributions)
            </h2>
            <div className="space-y-2.5">
              {score_contributions.map((contrib, idx) => {
                const isPositive = contrib.delta >= 0;
                return (
                  <div
                    key={idx}
                    className="flex items-start gap-2.5 text-xs p-2 rounded-lg bg-[var(--subtle)]/70 border border-[var(--border-default)]"
                  >
                    <span
                      className={`inline-flex items-center justify-center font-mono font-bold text-[11px] px-1.5 py-0.5 rounded shrink-0 ${
                        isPositive
                          ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                          : "bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                      }`}
                    >
                      {isPositive ? `+${contrib.delta}` : `${contrib.delta}`}
                    </span>
                    <div className="flex-1">
                      <span className="font-semibold text-[var(--text-primary)]">
                        {contrib.feature}
                      </span>
                      <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                        {contrib.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 3-Group Skills Card */}
          <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-xs space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
              Skills Analysis (3 Groups)
            </h2>

            {/* Group 1: Matched must-haves (Green) */}
            <div>
              <div className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 mb-2 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Matched Must-Haves ({skills_grouped.matched.length})</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {skills_grouped.matched.map((sk: string) => (
                  <span
                    key={sk}
                    className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 font-medium"
                  >
                    <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                    {sk}
                  </span>
                ))}
              </div>
            </div>

            {/* Group 2: Inferred skills via O*NET (Blue with Sparkle) */}
            <div className="pt-2 border-t border-[var(--border-default)]">
              <div className="text-[11px] font-semibold text-sky-600 dark:text-sky-400 mb-2 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Inferred Skills (O*NET Taxonomy) ({skills_grouped.inferred.length})</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {skills_grouped.inferred.map((sk: string) => (
                  <span
                    key={sk}
                    className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-sky-500/15 text-sky-700 dark:text-sky-300 border border-sky-500/30 font-medium cursor-help"
                    title="Inferred from distributed systems architecture and Go/Kafka stack"
                  >
                    <Sparkles className="w-3 h-3 text-sky-500" />
                    {sk}
                  </span>
                ))}
              </div>
            </div>

            {/* Group 3: Missing skills (Red with Exclamation) */}
            <div className="pt-2 border-t border-[var(--border-default)]">
              <div className="text-[11px] font-semibold text-red-600 dark:text-red-400 mb-2 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Missing Skills ({skills_grouped.missing.length})</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {skills_grouped.missing.map((sk: string) => (
                  <span
                    key={sk}
                    className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-red-500/15 text-red-700 dark:text-red-300 border border-red-500/30 font-medium"
                  >
                    <AlertCircle className="w-3 h-3 text-red-500" />
                    {sk}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* COLUMN 2: AI Briefing & Resume Evidence (45% on lg -> 5 cols) */}
        <div
          className={`lg:col-span-5 space-y-4 ${
            activeTab === "evidence" ? "block" : "hidden lg:block"
          }`}
        >
          {/* AI Recruiter Briefing Card */}
          <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-xs">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  AI Recruiter Briefing
                </h2>
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30">
                  <Sparkles className="w-2.5 h-2.5" />
                  Evidence-grounded
                </span>
              </div>
              <span className="text-[10px] text-[var(--text-secondary)] italic">
                Click citation pill to highlight resume
              </span>
            </div>

            <ul className="space-y-3 text-xs leading-relaxed text-[var(--text-primary)]">
              {briefingList.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-blue-500 font-bold mt-0.5">•</span>
                  <div className="flex-1">
                    <span>{item.sentence}</span>{" "}
                    <CitationPill
                      id={item.citation_id}
                      isActive={activeCitationId === item.citation_id}
                      onClick={handleCitationClick}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Resume Evidence Viewer Card */}
          <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-xs">
            <div className="flex items-center justify-between mb-3 border-b border-[var(--border-default)] pb-2.5">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-500" />
                <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Resume Evidence Viewer (Verbatim Text)
                </h2>
              </div>
              {activeCitationId && (
                <span className="text-[11px] font-mono text-blue-600 dark:text-blue-400 font-medium">
                  Active: [{activeCitationId}]
                </span>
              )}
            </div>

            {/* Verbatim Resume Content Box */}
            <div
              ref={evidenceContainerRef}
              className="max-h-[500px] overflow-y-auto rounded-lg bg-[var(--canvas)] p-4 font-mono text-[11px] leading-relaxed text-[var(--text-primary)] border border-[var(--border-default)] space-y-4"
              tabIndex={0}
              aria-label="Verbatim Resume Text with Grounded Evidence Chunks"
            >
              {citations.map((cite) => {
                const isActive = activeCitationId === cite.id;
                return (
                  <div
                    key={cite.id}
                    ref={(el) => {
                      if (el) citationElementsRef.current.set(cite.id, el);
                      else citationElementsRef.current.delete(cite.id);
                    }}
                    id={`citation-target-${cite.id}`}
                    className={`p-3 rounded-md border transition-all duration-300 ${
                      isActive
                        ? "bg-blue-500/15 border-blue-500 ring-2 ring-blue-500/30 text-[var(--text-primary)]"
                        : "bg-[var(--surface)]/50 border-l-2 border-l-blue-500/60 border-[var(--border-default)] hover:border-blue-500/40"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5 text-[10px] text-[var(--text-secondary)] font-sans">
                      <span className="font-mono font-bold text-blue-500">
                        [{cite.id}] · {cite.section}
                      </span>
                      <span>
                        Chars: {cite.char_start}–{cite.char_end}
                      </span>
                    </div>
                    <p className="whitespace-pre-wrap font-mono leading-relaxed">
                      {cite.text_snippet}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* COLUMN 3: Decision & Interview Prep (25% on lg -> 3 cols) */}
        <div
          className={`lg:col-span-3 space-y-4 ${
            activeTab === "prep" ? "block" : "hidden lg:block"
          }`}
        >
          {/* What-if Score Simulator Card */}
          <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-xs space-y-3">
            <div>
              <div className="flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-blue-500" />
                <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  What-If Score Simulator
                </h2>
              </div>
              <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                Simulate score changes by adjusting candidate attributes.
              </p>
            </div>

            {/* Simulator Checkboxes */}
            <div className="space-y-2 pt-2 border-t border-[var(--border-default)]">
              <label className="flex items-center gap-2 text-xs text-[var(--text-primary)] cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={simAddCassandra}
                  onChange={(e) => setSimAddCassandra(e.target.checked)}
                  className="rounded border-[var(--border-default)] text-blue-600 focus:ring-blue-500"
                />
                <span>Add Cassandra experience (+5 pts)</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-[var(--text-primary)] cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={simAddYearExp}
                  onChange={(e) => setSimAddYearExp(e.target.checked)}
                  className="rounded border-[var(--border-default)] text-blue-600 focus:ring-blue-500"
                />
                <span>Add +1 yr verified experience (+2 pts)</span>
              </label>
            </div>

            {/* Real-time score delta indicator */}
            <div className="p-3 rounded-lg bg-[var(--subtle)] border border-[var(--border-default)] flex items-center justify-between">
              <div>
                <span className="text-[10px] text-[var(--text-secondary)] block">
                  Simulated Score
                </span>
                <span className="text-base font-bold font-mono text-[var(--text-primary)]">
                  {baseScore} → {simulatedScore}
                </span>
              </div>
              {isSimulating ? (
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 animate-pulse">
                  ▲ +{simDelta}
                </span>
              ) : (
                <span className="text-[11px] text-[var(--text-secondary)]">No delta</span>
              )}
            </div>

            {/* Reset Button */}
            {isSimulating && (
              <button
                type="button"
                onClick={handleResetSimulator}
                className="w-full inline-flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-default)] rounded-md transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset simulation</span>
              </button>
            )}

            {/* Non-negotiable Disclaimer Banner */}
            <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-700 dark:text-amber-400 leading-tight">
              <strong>Hypothetical simulation.</strong> Never saved to candidate record.
            </div>
          </div>

          {/* Interview Questions Card */}
          <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-xs space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
              Interview Questions
            </h2>

            {/* Skill Verification Questions */}
            <div>
              <span className="text-[11px] font-semibold text-blue-600 dark:text-blue-400 block mb-2">
                Skill Verification ({interview_questions.skill_verification.length})
              </span>
              <div className="space-y-3">
                {interview_questions.skill_verification.map((q, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-[var(--subtle)]/70 border border-[var(--border-default)] space-y-1.5 text-xs"
                  >
                    <p className="font-medium text-[var(--text-primary)] leading-snug">
                      "{q.question}"
                    </p>
                    <div className="text-[10px] text-[var(--text-secondary)] font-mono">
                      Target: <span className="text-blue-500 font-semibold">{q.target_skill}</span>
                    </div>
                    <p className="text-[11px] text-[var(--text-secondary)] italic">
                      Criteria: {q.evaluation_criteria}
                    </p>
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(q.question)}
                      className="inline-flex items-center gap-1 text-[10px] text-blue-600 dark:text-blue-400 hover:underline pt-1"
                    >
                      <Copy className="w-3 h-3" />
                      <span>Copy question</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Gap Probing Questions */}
            <div className="pt-2 border-t border-[var(--border-default)]">
              <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 block mb-2">
                Gap Probing ({interview_questions.gap_probing.length})
              </span>
              <div className="space-y-3">
                {interview_questions.gap_probing.map((q, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-[var(--subtle)]/70 border border-[var(--border-default)] space-y-1.5 text-xs"
                  >
                    <p className="font-medium text-[var(--text-primary)] leading-snug">
                      "{q.question}"
                    </p>
                    <div className="text-[10px] text-[var(--text-secondary)] font-mono">
                      Target Gap: <span className="text-amber-500 font-semibold">{q.target_gap}</span>
                    </div>
                    <p className="text-[11px] text-[var(--text-secondary)] italic">
                      Criteria: {q.evaluation_criteria}
                    </p>
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(q.question)}
                      className="inline-flex items-center gap-1 text-[10px] text-blue-600 dark:text-blue-400 hover:underline pt-1"
                    >
                      <Copy className="w-3 h-3" />
                      <span>Copy question</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
