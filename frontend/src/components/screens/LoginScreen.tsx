import React, { useState } from "react";
import { Search, KeyRound, Mail, AlertCircle, Info } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export const LoginScreen: React.FC = () => {
  const { login } = useAuth();
  const isDemoMode = import.meta.env.VITE_DEMO_MODE === "true";
  const defaultDemoEmail = import.meta.env.VITE_DEMO_EMAIL || "";

  const [email, setEmail] = useState(isDemoMode ? defaultDemoEmail : "");
  const [password, setPassword] = useState("");
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
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--canvas)]">
      <div className="w-full max-w-md bg-[var(--surface)] border border-[var(--border-default)] rounded-xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="p-7 text-center border-b border-[var(--border-default)]">
          <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white mx-auto shadow-sm mb-3">
            <Search className="w-5 h-5 stroke-[2.5]" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            Recruit Lens
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Explainable, Evidence-Grounded AI Screening Platform
          </p>
        </div>

        {/* Role Switcher Chips (Demo Mode Only) */}
        {isDemoMode && (
          <div className="p-5 border-b border-[var(--border-default)] bg-[var(--subtle)]/50">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)] block mb-2">
              Switch Demo Role:
            </span>
            <div className="grid grid-cols-3 gap-2">
              {demoRoles.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => handleSelectRole(r)}
                  className={`p-2 rounded-lg text-left border transition-all cursor-pointer ${
                    selectedRole === r.id
                      ? "bg-blue-600 text-white border-blue-500 shadow-xs"
                      : "bg-[var(--surface)] text-[var(--text-secondary)] border-[var(--border-default)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  <span className="text-xs font-semibold block">{r.name}</span>
                  <span className="text-[10px] opacity-80 font-mono block truncate">
                    {r.id}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Demo Credentials Banner (Demo Mode Only) */}
        {isDemoMode && (
          <div className="mx-5 mt-4 p-3 bg-blue-500/10 border border-blue-500/25 rounded-lg flex items-start gap-2.5 text-xs text-blue-700 dark:text-blue-300">
            <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold block">Demo Mode Active:</span>
              <div className="font-mono text-[11px]">
                Email: <strong>{email || "demo@recruitlens.local"}</strong>
                <br />
                Password: <strong>(Configured via DEMO_PASSWORD)</strong>
              </div>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div
              role="alert"
              aria-live="assertive"
              className="p-3 bg-red-500/15 border border-red-500/30 text-red-700 dark:text-red-300 rounded-lg text-xs flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
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
              <Mail className="w-4 h-4 text-[var(--text-secondary)] absolute left-3 top-2.5" />
              <input
                id="login-email-input"
                type="email"
                required
                className="w-full text-xs pl-9 pr-3 py-2 bg-[var(--canvas)] border border-[var(--border-default)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="recruiter@company.com"
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
              <KeyRound className="w-4 h-4 text-[var(--text-secondary)] absolute left-3 top-2.5" />
              <input
                id="login-password-input"
                type="password"
                required
                className="w-full text-xs pl-9 pr-3 py-2 bg-[var(--canvas)] border border-[var(--border-default)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold text-xs rounded-lg shadow-sm transition-colors cursor-pointer flex items-center justify-center gap-2"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Signing in...
              </span>
            ) : (
              "Sign In to Recruiter Portal"
            )}
          </button>

          <p className="text-[11px] text-center text-[var(--text-secondary)] pt-2 font-mono">
            Role-Based Access Control · WCAG 2.2 AA Compliant
          </p>
        </form>
      </div>
    </div>
  );
};
