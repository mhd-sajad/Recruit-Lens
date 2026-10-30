import React from "react";
import { ArrowLeft, ArrowRight, Shield, Lock, Send, CheckCircle2, EyeOff, SlidersHorizontal, FileText, Search } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

interface HowItWorksScreenProps {
  onNavigate: (path: string) => void;
}

export const HowItWorksScreen: React.FC<HowItWorksScreenProps> = ({ onNavigate }) => {
  const { isAuthenticated } = useAuth();

  const handleStart = () => {
    if (isAuthenticated) {
      onNavigate("/requisitions");
    } else {
      onNavigate("/login?tab=signup&redirect=%2Frequisitions");
    }
  };

  const steps = [
    {
      num: "1",
      title: "Create a requisition",
      desc: "Paste the job description. Recruit Lens extracts the must-have skills. You confirm or edit them and set the scoring weights, which must add up to 100%.",
      you: "You paste the JD and check the skills.",
      system: "Extracts skills and validates the weights.",
      badge: "Step 1 of 8",
      icon: SlidersHorizontal,
      visual: (
        <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-default)] font-mono text-[11px] text-[var(--text-secondary)] space-y-1.5">
          <div className="flex items-center justify-between text-indigo-400 font-semibold">
            <span>Job description parsed</span>
            <span>Weights: 100%</span>
          </div>
          <div className="flex flex-wrap gap-1">
            <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">Python</span>
            <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">AWS</span>
            <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">Kubernetes</span>
          </div>
          <div className="text-[10px] text-[var(--text-tertiary)] pt-1">
            Skills 50% · Exp 30% · Seniority 20% = 100%
          </div>
        </div>
      ),
    },
    {
      num: "2",
      title: "Upload candidate CVs",
      desc: "Drag in PDF resumes (up to 15 MB each). Every file passes a resume gate first. Files that are not resumes, such as an invoice, are marked Abstain and are not ranked.",
      you: "You drop the files and retry any failures.",
      system: "Verifies the file type, checks it is a CV, splits it into text chunks.",
      badge: "Resume Gate Active",
      icon: FileText,
      visual: (
        <div className="space-y-1.5 font-mono text-[11px]">
          <div className="flex items-center justify-between p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <span>Resume_6299.pdf</span>
            <span>✓ Indexed</span>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <span>Resume_6310.pdf</span>
            <span>Processing…</span>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400">
            <span>Scanned_Invoice.pdf</span>
            <span>⊘ Abstain</span>
          </div>
        </div>
      ),
    },
    {
      num: "3",
      title: "Hybrid retrieval and scoring",
      desc: "Each resume is matched to the JD with keyword search (BM25) and meaning-based embeddings. The match score only goes up when evidence is added, so results are consistent and explainable.",
      you: "Nothing. This is automatic.",
      system: "Combines both searches and produces a 0–100 score with reasons.",
      badge: "BM25 + Dense Vectors",
      icon: Search,
      visual: (
        <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-default)] space-y-2 text-xs">
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-[var(--text-secondary)]">BM25 Keywords</span>
            <span className="text-indigo-400">Exact token match</span>
          </div>
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-[var(--text-secondary)]">Semantic Embeddings</span>
            <span className="text-cyan-400">Conceptual meaning</span>
          </div>
          <div className="pt-1.5 border-t border-[var(--border-default)] flex items-center justify-between font-mono font-bold">
            <span className="text-[var(--text-primary)]">Composite Match Score</span>
            <span className="text-emerald-400 text-sm">95 / 100</span>
          </div>
        </div>
      ),
    },
    {
      num: "4",
      title: "Triage into tiers",
      desc: "Candidates are ranked from highest score and placed in a tier: FastTrack, Interview, Hold or Reject. Employer names are hidden to prevent prestige bias.",
      you: "You scan the ranked table and filter by tier.",
      system: "Sorts by score and withholds company names.",
      badge: "Prestige Bias Suppression",
      icon: Shield,
      visual: (
        <div className="space-y-1.5 font-mono text-[11px]">
          <div className="flex items-center justify-between p-1.5 rounded bg-[var(--bg-subtle)] border border-[var(--border-default)]">
            <span className="text-emerald-400 font-semibold">✓ FastTrack</span>
            <span className="text-[var(--text-secondary)]">Score ≥ 85</span>
          </div>
          <div className="flex items-center justify-between p-1.5 rounded bg-[var(--bg-subtle)] border border-[var(--border-default)]">
            <span className="text-blue-400 font-semibold">● Interview</span>
            <span className="text-[var(--text-secondary)]">Score 70–84</span>
          </div>
          <div className="flex items-center justify-between p-1.5 rounded bg-[var(--bg-subtle)] border border-[var(--border-default)]">
            <span className="text-amber-400 font-semibold">◔ Hold</span>
            <span className="text-[var(--text-secondary)]">Score 50–69</span>
          </div>
          <div className="text-[10px] text-indigo-400 pt-0.5">
            Employer names are never shown.
          </div>
        </div>
      ),
    },
    {
      num: "5",
      title: "Read the candidate dossier",
      desc: "Open a candidate to see why they scored as they did, their skills as Matched, Inferred (via O*NET) or Missing, and an AI briefing. Every claim has a citation pill like [c_02].",
      you: "You click a citation to see the exact resume text.",
      system: "Highlights the supporting passage in the resume.",
      badge: "100% Cited Claims",
      icon: CheckCircle2,
      visual: (
        <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-default)] space-y-2 text-xs">
          <p className="text-[var(--text-secondary)] leading-relaxed">
            Led migration to AWS Lambda{" "}
            <span className="px-1 py-0.2 rounded bg-indigo-500/20 text-indigo-300 font-mono text-[10px] font-bold">
              c_02
            </span>
          </p>
          <div className="p-2 rounded bg-[var(--bg-canvas)] border border-indigo-500/30 text-[11px] font-mono text-indigo-300">
            [c_02] &ldquo;Migrated batch pipelines to AWS Lambda and ECS.&rdquo;
          </div>
        </div>
      ),
    },
    {
      num: "6",
      title: "Test with the what-if simulator",
      desc: "Tick a missing skill or add a year of experience to see how the score would change. This is hypothetical only and is never saved to the candidate.",
      you: "You toggle skills and read the score change.",
      system: "Recalculates the score instantly.",
      badge: "Hypothetical Simulation",
      icon: SlidersHorizontal,
      visual: (
        <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-default)] font-mono text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-emerald-400">☑ Kubernetes</span>
            <span className="text-emerald-400">▲ +5 pts</span>
          </div>
          <div className="flex items-center justify-between text-[var(--text-secondary)]">
            <span>☐ Terraform</span>
            <span>+0 pts</span>
          </div>
          <div className="text-[10px] text-amber-400/90 pt-1 border-t border-[var(--border-default)]">
            Simulated: 95 → 100 · Never saved
          </div>
        </div>
      ),
    },
    {
      num: "7",
      title: "Draft, approve, then send emails",
      desc: "You: You edit, approve, choose dry-run or live, then send. System: Blocks sending until approved and scans rejections for scores.",
      you: "You edit, approve, choose dry-run or live, then send.",
      system: "Blocks sending until approved and scans rejections for scores.",
      badge: "Two-Step Human Gate",
      icon: Send,
      visual: (
        <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-default)] space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-2 py-1 rounded bg-indigo-600 text-white text-[10px] font-semibold">
              1. Approve Draft
            </span>
            <span className="px-2 py-1 rounded bg-[var(--bg-canvas)] border border-[var(--border-default)] text-[var(--text-secondary)] text-[10px] font-semibold">
              2. Send Email (Locked)
            </span>
          </div>
          <div className="text-[10px] font-mono text-emerald-400">
            ✓ Adverse-action rejection policy verified: Zero scores
          </div>
        </div>
      ),
    },
    {
      num: "8",
      title: "Move through the pipeline and audit",
      desc: "Drag or move candidates through stages. A candidate cannot reach Offer before the technical assessment is complete. Every override, approval and send is written to a tamper-evident audit log.",
      you: "You move candidates and give a reason for overrides.",
      system: "Enforces stage rules and chains each log entry by hash.",
      badge: "Cryptographic Audit Log",
      icon: Lock,
      visual: (
        <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-default)] font-mono text-[11px] space-y-1.5">
          <div className="flex items-center justify-between text-[var(--text-secondary)]">
            <span>Screened → Interview → Assessment</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
            <CheckCircle2 size={12} />
            <span>✓ Hash chain verified</span>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)] flex flex-col">
      {/* Top Header */}
      <header className="sticky top-0 z-40 w-full border-b border-[var(--border-default)] bg-[var(--bg-surface)]/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => onNavigate("/")}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
            >
              <ArrowLeft size={16} />
              Home
            </button>
            <div className="h-4 w-px bg-[var(--border-default)]" />
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-[var(--text-primary)]">
                Recruit <span className="text-indigo-400 font-extrabold">Lens</span>
              </span>
              <span className="text-[9px] font-mono tracking-widest uppercase text-[var(--text-secondary)]">
                EXPLAINABLE HIRING
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <button
                onClick={() => onNavigate("/requisitions")}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors cursor-pointer"
              >
                Open workspace
                <ArrowRight size={14} />
              </button>
            ) : (
              <button
                onClick={() => onNavigate("/login?tab=signup")}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors cursor-pointer"
              >
                Sign up
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Guide Content */}
      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Title & Overview */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <span className="text-xs font-mono uppercase tracking-widest text-indigo-400 font-semibold block mb-2">
            HOW IT WORKS
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[var(--text-primary)] mb-4">
            From job description to hired, in 8 steps
          </h1>
          <p className="text-sm sm:text-base text-[var(--text-secondary)] leading-relaxed">
            Recruit Lens ranks candidates and explains every score with evidence from the resume. You stay in control: nothing is sent or decided without your approval.
          </p>

          {/* 3 Callout Cards */}
          <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
            <div className="p-3.5 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
              <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold mb-1">
                <EyeOff size={14} />
                <span>Blind Mode</span>
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                Turn it on in Settings to hide names and contact details everywhere.
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
              <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold mb-1">
                <Lock size={14} />
                <span>Audit trail</span>
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                Cryptographically records every evaluation, approval, and send action.
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)]">
              <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold mb-1">
                <Send size={14} />
                <span>Dry-run</span>
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                Lets you safely test email templates without dispatching SMTP traffic.
              </p>
            </div>
          </div>
        </div>

        {/* 8 Step Cards */}
        <div className="space-y-6">
          {steps.map((st) => {
            const Icon = st.icon;
            return (
              <div
                key={st.num}
                className="p-6 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] shadow-xs hover:border-indigo-500/40 transition-colors"
              >
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
                  <div className="md:col-span-7">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 font-mono font-bold text-sm flex items-center justify-center shrink-0">
                        {st.num}
                      </span>
                      <Icon size={16} className="text-indigo-400 shrink-0" />
                      <h2 className="text-lg font-bold text-[var(--text-primary)]">
                        {st.title}
                      </h2>
                      <span className="ml-auto md:hidden text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--bg-subtle)] text-[var(--text-secondary)] border border-[var(--border-default)]">
                        {st.badge}
                      </span>
                    </div>

                    <p className="text-xs text-[var(--text-secondary)] leading-relaxed mb-4">
                      {st.desc}
                    </p>

                    <div className="space-y-1 text-xs">
                      <div className="flex items-baseline gap-2">
                        <span className="font-semibold text-indigo-400 font-mono text-[11px] shrink-0">You:</span>
                        <span className="text-[var(--text-primary)]">{st.you}</span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="font-semibold text-cyan-400 font-mono text-[11px] shrink-0">System:</span>
                        <span className="text-[var(--text-secondary)]">{st.system}</span>
                      </div>
                    </div>
                  </div>

                  <div className="md:col-span-5">
                    {st.visual}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom CTA */}
        <div className="mt-16 text-center p-8 rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">
            Ready to screen your first candidate pool?
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mb-6">
            Jump directly into the workspace to create a requisition or review active candidate rankings.
          </p>
          <button
            onClick={handleStart}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md transition-colors cursor-pointer"
          >
            Start with a requisition
            <ArrowRight size={16} />
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border-default)] bg-[var(--bg-surface)] py-6 text-center text-[11px] font-mono text-[var(--text-secondary)]">
        © 2026 RECRUIT LENS · DEMO BUILD
      </footer>
    </div>
  );
};
