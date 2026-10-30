import React, { useState } from "react";
import { KeyRound, Mail, AlertCircle, Info } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export const LoginScreen: React.FC = () => {
  const { login } = useAuth();
  const isDemoMode = import.meta.env.VITE_DEMO_MODE === "true";
  const defaultDemoEmail = import.meta.env.VITE_DEMO_EMAIL || "";

  const [activeTab, setActiveTab] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState(isDemoMode ? defaultDemoEmail : "");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("Lead Admin");
  const [selectedRole, setSelectedRole] = useState<"admin" | "recruiter" | "auditor" | null>(
    isDemoMode ? "admin" : null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const demoRoles = [
    {
      id: "admin" as const,
      name: "Lead Admin",
      email: defaultDemoEmail || "admin@recruitlens.local",
      desc: "Full requisition, scoring configuration, and pipeline access",
    },
    {
      id: "recruiter" as const,
      name: "Technical Recruiter",
      email: "recruiter@recruitlens.local",
      desc: "Candidate ranking, dossier review, and email drafting",
    },
    {
      id: "auditor" as const,
      name: "Compliance Auditor",
      email: "auditor@recruitlens.local",
      desc: "Read-only access to tamper-proof hash-chain audit logs",
    },
  ];

  const handleSelectRole = (r: (typeof demoRoles)[0]) => {
    setSelectedRole(r.id);
    setEmail(r.email);
    setFullName(r.name);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password.trim()) {
      setError("Please provide both email and password.");
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || "Failed to sign in. Please verify your credentials.");
      } else {
        setError("Failed to sign in. Please verify your credentials.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--bg-canvas)]">
      <div className="w-full max-w-[440px] bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl shadow-lg p-7">
        {/* Brand Header */}
        <div className="flex flex-col items-start gap-1 pb-4">
          <div className="flex items-center gap-2">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#818CF8"
              strokeWidth="2.5"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4.3-4.3" />
            </svg>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              Recruit Lens
            </h1>
          </div>
          <span className="font-mono text-[9px] tracking-[0.24em] text-[var(--text-secondary)] uppercase">
            Explainable Hiring
          </span>
        </div>

        {/* Tab Toggle: Log in / Sign up */}
        <div
          role="tablist"
          className="flex mt-3 border border-[var(--border-default)] rounded-lg overflow-hidden p-0.5 bg-[var(--bg-subtle)]"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "login"}
            onClick={() => setActiveTab("login")}
            className={`flex-1 min-h-[36px] text-xs font-semibold rounded-md transition-colors ${
              activeTab === "login"
                ? "bg-[var(--primary-btn)] text-white shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Log in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "signup"}
            onClick={() => setActiveTab("signup")}
            className={`flex-1 min-h-[36px] text-xs font-semibold rounded-md transition-colors ${
              activeTab === "signup"
                ? "bg-[var(--primary-btn)] text-white shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Sign up
          </button>
        </div>

        <div className="mt-4">
          <h2 className="text-lg font-bold text-[var(--text-primary)]">
            {activeTab === "login" ? "Sign in to your account" : "Create your account"}
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            After this you will land on Requisitions.
          </p>
        </div>

        {/* Role Switcher Chips (Demo Mode Only) */}
        {isDemoMode && (
          <div className="mt-4 p-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-subtle)]/60">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-secondary)] block mb-2 font-mono">
              Demo Preset Credentials:
            </span>
            <div className="grid grid-cols-3 gap-1.5">
              {demoRoles.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => handleSelectRole(r)}
                  className={`p-1.5 rounded-md text-left border transition-all cursor-pointer ${
                    selectedRole === r.id
                      ? "bg-blue-600 text-white border-blue-500 shadow-xs"
                      : "bg-[var(--bg-surface)] text-[var(--text-secondary)] border-[var(--border-default)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  <span className="text-[11px] font-semibold block">{r.name}</span>
                  <span className="text-[9px] opacity-80 font-mono block truncate">
                    {r.id}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Demo Credentials Banner */}
        {isDemoMode && (
          <div className="mt-3 p-2.5 bg-blue-500/10 border border-blue-500/25 rounded-lg flex items-start gap-2 text-xs text-blue-700 dark:text-blue-300">
            <Info className="w-3.5 h-3.5 text-blue-500 shrink-0 mt-0.5" />
            <div className="space-y-0.5 text-[11px]">
              <span className="font-semibold block">Demo Mode Active:</span>
              <div className="font-mono text-[10px]">
                Email: <strong>{email || "admin@recruitlens.local"}</strong>
                <br />
                Password: <strong>(From DEMO_PASSWORD env)</strong>
              </div>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          {error && (
            <div
              role="alert"
              aria-live="assertive"
              className="p-2.5 bg-red-500/15 border border-red-500/30 text-red-700 dark:text-red-300 rounded-lg text-xs flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {activeTab === "signup" && (
            <div className="space-y-1">
              <label
                htmlFor="login-name-input"
                className="text-xs font-medium text-[var(--text-secondary)]"
              >
                Full Name
              </label>
              <input
                id="login-name-input"
                type="text"
                className="w-full text-xs px-3 py-2 bg-[var(--bg-subtle)] border border-[var(--border-default)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Alex Morgan"
              />
            </div>
          )}

          <div className="space-y-1">
            <label
              htmlFor="login-email-input"
              className="text-xs font-medium text-[var(--text-secondary)]"
            >
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-3.5 h-3.5 text-[var(--text-secondary)] absolute left-3 top-2.5" />
              <input
                id="login-email-input"
                type="email"
                required
                className="w-full text-xs pl-8 pr-3 py-2 bg-[var(--bg-subtle)] border border-[var(--border-default)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@recruitlens.local"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label
              htmlFor="login-password-input"
              className="text-xs font-medium text-[var(--text-secondary)]"
            >
              Password
            </label>
            <div className="relative">
              <KeyRound className="w-3.5 h-3.5 text-[var(--text-secondary)] absolute left-3 top-2.5" />
              <input
                id="login-password-input"
                type="password"
                required
                className="w-full text-xs pl-8 pr-3 py-2 bg-[var(--bg-subtle)] border border-[var(--border-default)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 bg-[var(--primary-btn)] hover:bg-[var(--primary-btn-hover)] disabled:opacity-50 text-white font-semibold text-xs rounded-lg shadow-sm transition-colors cursor-pointer flex items-center justify-center gap-2 min-h-[40px]"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Signing in...
              </span>
            ) : activeTab === "login" ? (
              "Sign in to Recruiter Portal"
            ) : (
              "Create account and continue"
            )}
          </button>

          <p className="font-mono text-[11px] text-center text-[var(--text-secondary)] pt-2 border-t border-[var(--border-default)]">
            Grounded AI · Cryptographic Hash-Chain Audit · WCAG 2.2 AA
          </p>
        </form>
      </div>
    </div>
  );
};
