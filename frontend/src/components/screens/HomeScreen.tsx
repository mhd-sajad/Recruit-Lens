import React from "react";
import { ArrowRight, CheckCircle2, Shield, Search, FileText, BarChart3, Sliders, Mail, UserCheck, Lock } from "lucide-react";
import { BrandLogo } from "../common/BrandLogo";
import { useAuth } from "../../context/AuthContext";

interface HomeScreenProps {
  onNavigate: (path: string) => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({ onNavigate }) => {
  const { isAuthenticated, user } = useAuth();

  const handleTryItOut = () => {
    if (isAuthenticated) {
      onNavigate("/requisitions");
    } else {
      onNavigate("/login?tab=signup&redirect=%2Frequisitions");
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)] flex flex-col">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 w-full border-b border-[var(--border-default)] bg-[var(--bg-surface)]/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Brand */}
          <button
            onClick={() => onNavigate("/")}
            className="flex items-center text-left group cursor-pointer focus:outline-none"
            aria-label="Recruit Lens Home"
          >
            <BrandLogo size="md" />
          </button>

          {/* Nav Links & Auth CTA */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => onNavigate("/how-it-works")}
              className="text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors px-3 py-1.5 rounded-md hover:bg-[var(--bg-subtle)]"
            >
              How it Works
            </button>

            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-semibold text-[var(--text-primary)]">
                    {user?.email || "admin@recruitlens.local"}
                  </span>
                  <span className="text-[10px] text-indigo-400 font-mono font-medium">
                    Recruiter
                  </span>
                </div>
                <button
                  onClick={() => onNavigate("/requisitions")}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors cursor-pointer"
                >
                  Open workspace
                  <ArrowRight size={14} />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onNavigate("/login?tab=login")}
                  className="text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors px-3 py-1.5 rounded-md hover:bg-[var(--bg-subtle)]"
                >
                  Log in
                </button>
                <button
                  onClick={() => onNavigate("/login?tab=signup")}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors cursor-pointer"
                >
                  Sign up
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {/* HERO SECTION */}
        <section className="relative overflow-hidden pt-12 pb-20 border-b border-[var(--border-default)]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
              {/* Left Column: Copy & Actions */}
              <div className="lg:col-span-7 flex flex-col items-start">
                <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-400 text-[11px] font-mono uppercase tracking-wider mb-5">
                  <Shield size={12} />
                  <span>EXPLAINABLE, PRIVACY-FIRST RECRUITMENT</span>
                </div>

                <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[var(--text-primary)] leading-[1.15] mb-5">
                  Screen resumes with evidence,{" "}
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">
                    not black-box scores.
                  </span>
                </h1>

                <p className="text-base sm:text-lg text-[var(--text-secondary)] leading-relaxed max-w-2xl mb-8">
                  Recruit Lens ranks candidates against your job description and shows the exact resume text behind every score, so every decision can be explained and checked.
                </p>

                <div className="flex flex-wrap items-center gap-4 mb-4">
                  <button
                    onClick={handleTryItOut}
                    className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md hover:shadow-indigo-500/25 transition-all cursor-pointer"
                  >
                    Try it out →
                  </button>

                  <button
                    onClick={() => onNavigate("/how-it-works")}
                    className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg text-sm font-semibold border border-[var(--border-default)] bg-[var(--bg-surface)] hover:bg-[var(--bg-subtle)] text-[var(--text-primary)] transition-colors cursor-pointer"
                  >
                    See how it works
                  </button>
                </div>

                <p className="text-xs text-[var(--text-secondary)]">
                  {isAuthenticated
                    ? `Signed in as ${user?.email || "admin@recruitlens.local"}. This takes you straight to Requisitions.`
                    : "New here? You will sign up or log in first, then land on Requisitions."}
                </p>
              </div>

              {/* Right Column: Sample Candidate Card #6299 */}
              <div className="lg:col-span-5">
                <div className="p-6 rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)] shadow-xl relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />

                  <div className="flex items-center justify-between pb-4 border-b border-[var(--border-default)] mb-4">
                    <div>
                      <span className="font-mono text-xs font-semibold text-indigo-400">
                        Candidate #6299
                      </span>
                      <h2 className="text-base font-bold text-[var(--text-primary)]">
                        Senior Python Developer
                      </h2>
                    </div>
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <CheckCircle2 size={12} />
                      FastTrack
                    </span>
                  </div>

                  {/* AI Recruiter Briefing with Citations */}
                  <div className="space-y-3 mb-5">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-secondary)]">
                      AI RECRUITER BRIEFING
                    </span>
                    <p className="text-xs text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-subtle)] p-3 rounded-lg border border-[var(--border-default)]">
                      Built async APIs in FastAPI{" "}
                      <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold cursor-help">
                        c_01
                      </span>{" "}
                      and migrated pipelines to AWS Lambda{" "}
                      <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold cursor-help">
                        c_02
                      </span>
                      . No Kubernetes evidence found.
                    </p>
                  </div>

                  {/* Skills tags */}
                  <div className="flex flex-wrap gap-1.5 pt-2 border-t border-[var(--border-default)]">
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Python
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      AWS
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Docker
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      Kubernetes (Missing)
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* 5 Trust Highlights / Pillars */}
            <div className="mt-16 pt-8 border-t border-[var(--border-default)] grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {[
                { label: "BM25 + EMBEDDINGS", icon: Search },
                { label: "EVERY CLAIM CITED", icon: FileText },
                { label: "EMPLOYER NAMES HIDDEN", icon: Shield },
                { label: "HUMAN-APPROVED EMAILS", icon: Mail },
                { label: "AUDIT TRAIL", icon: Lock },
              ].map((pill, idx) => {
                const Icon = pill.icon;
                return (
                  <div
                    key={idx}
                    className="flex items-center gap-2 p-2.5 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] text-xs font-mono font-semibold text-[var(--text-secondary)]"
                  >
                    <Icon size={14} className="text-indigo-400 shrink-0" />
                    <span className="truncate">{pill.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 6 FEATURE CARDS SECTION */}
        <section className="py-20 border-b border-[var(--border-default)]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <span className="text-xs font-mono uppercase tracking-widest text-indigo-400 font-semibold block mb-2">
                WHAT RECRUIT LENS DOES
              </span>
              <h2 className="text-3xl font-extrabold text-[var(--text-primary)]">
                Built so every recommendation can be explained.
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  title: "Hybrid retrieval",
                  desc: "Keyword search (BM25) and meaning-based embeddings work together, so strong candidates are found even when they use different words.",
                  icon: Search,
                },
                {
                  title: "Evidence for every claim",
                  desc: "Each statement in the AI briefing carries a citation like [c_02]. Click it to see the exact resume text that supports it.",
                  icon: FileText,
                },
                {
                  title: "Explainable scores",
                  desc: "See which skills and experience added points and which gaps took them away. A score only rises when evidence is added.",
                  icon: BarChart3,
                },
                {
                  title: "Skills, matched or inferred",
                  desc: "Skills are grouped as Matched, Inferred through the O*NET taxonomy, or Missing, so gaps are clear.",
                  icon: Sliders,
                },
                {
                  title: "Fair by design",
                  desc: "Employer names are hidden, and Blind Mode masks names, contact details and photos to reduce bias.",
                  icon: Shield,
                },
                {
                  title: "You stay in control",
                  desc: "Emails are drafted by AI but never sent until you approve them. Every decision is written to a tamper-evident audit log.",
                  icon: UserCheck,
                },
              ].map((feat, idx) => {
                const Icon = feat.icon;
                return (
                  <div
                    key={idx}
                    className="p-6 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-indigo-500/40 transition-colors flex flex-col"
                  >
                    <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-4">
                      <Icon size={20} />
                    </div>
                    <h3 className="text-base font-bold text-[var(--text-primary)] mb-2">
                      {feat.title}
                    </h3>
                    <p className="text-xs text-[var(--text-secondary)] leading-relaxed flex-1">
                      {feat.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 4-STEP OVERVIEW SECTION */}
        <section className="py-20 border-b border-[var(--border-default)] bg-[var(--bg-subtle)]/40">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <span className="text-xs font-mono uppercase tracking-widest text-indigo-400 font-semibold block mb-2">
                HOW IT WORKS
              </span>
              <h2 className="text-3xl font-extrabold text-[var(--text-primary)]">
                Four steps from job description to shortlist.
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  step: "01",
                  title: "Create a requisition",
                  desc: "Paste a job description and confirm the must-have skills.",
                },
                {
                  step: "02",
                  title: "Upload CVs",
                  desc: "Drop in PDF resumes. Non-resumes are flagged and skipped.",
                },
                {
                  step: "03",
                  title: "Review ranked candidates",
                  desc: "See tiers and open a dossier to read the evidence.",
                },
                {
                  step: "04",
                  title: "Approve and move forward",
                  desc: "Approve email drafts and move candidates through the pipeline.",
                },
              ].map((st, idx) => (
                <div
                  key={idx}
                  className="p-6 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] flex flex-col"
                >
                  <span className="font-mono text-2xl font-extrabold text-indigo-400 mb-3">
                    {st.step}
                  </span>
                  <h3 className="text-sm font-bold text-[var(--text-primary)] mb-2">
                    {st.title}
                  </h3>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    {st.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* BUILT FOR RECRUITERS SECTION */}
        <section className="py-20 border-b border-[var(--border-default)]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <span className="text-xs font-mono uppercase tracking-widest text-indigo-400 font-semibold block mb-2">
                DESIGN PHILOSOPHY
              </span>
              <h2 className="text-3xl font-extrabold text-[var(--text-primary)]">
                Built for recruiters
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  title: "Screen in minutes",
                  desc: "Upload a batch of CVs and get a ranked shortlist with the reason behind every score.",
                },
                {
                  title: "Trust every score",
                  desc: "Each point links back to the exact resume text it came from.",
                },
                {
                  title: "Stay in control",
                  desc: "Nothing is emailed until you review and approve the draft.",
                },
              ].map((col, idx) => (
                <div
                  key={idx}
                  className="p-6 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)]"
                >
                  <h3 className="text-base font-bold text-[var(--text-primary)] mb-2">
                    {col.title}
                  </h3>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    {col.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FINAL CALL TO ACTION */}
        <section className="py-20 text-center">
          <div className="max-w-3xl mx-auto px-4">
            <h2 className="text-3xl font-extrabold text-[var(--text-primary)] mb-3">
              Ready to see it in action?
            </h2>
            <p className="text-sm text-[var(--text-secondary)] mb-8">
              Sign up with the demo account and screen your first requisition.
            </p>
            <button
              onClick={handleTryItOut}
              className="inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg hover:shadow-indigo-500/25 transition-all cursor-pointer"
            >
              Try it out →
            </button>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border-default)] bg-[var(--bg-surface)] py-6 text-center text-[11px] font-mono text-[var(--text-secondary)]">
        © 2026 RECRUIT LENS · DEMO BUILD
      </footer>
    </div>
  );
};
