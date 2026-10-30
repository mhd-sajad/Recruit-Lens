import React, { useState } from "react";
import { Mail, Lock, User, AlertCircle, ArrowLeft } from "lucide-react";
import { BrandLogo } from "../common/BrandLogo";
import { useAuth } from "../../context/AuthContext";

interface LoginScreenProps {
  initialTab?: "login" | "signup";
  redirectAfter?: string;
  onNavigateHome?: () => void;
  onLoginSuccess?: (path: string) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({
  initialTab = "login",
  redirectAfter,
  onNavigateHome,
  onLoginSuccess,
}) => {
  const { login } = useAuth();
  const [activeTab, setActiveTab] = useState<"login" | "signup">(initialTab);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("admin@recruitlens.local");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password.trim()) {
      setError("Please provide both email and password.");
      return;
    }

    if (activeTab === "signup" && !fullName.trim()) {
      setError("Please provide your name.");
      return;
    }

    setLoading(true);
    try {
      await login(email.trim(), password);
      const target = redirectAfter || "/requisitions";
      if (onLoginSuccess) {
        onLoginSuccess(target);
      }
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
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-[var(--bg-canvas)] text-[var(--text-primary)]">
      {/* Back to Home Link */}
      <div className="w-full max-w-[420px] mb-4 flex items-center justify-between">
        <button
          onClick={onNavigateHome || (() => { window.location.pathname = "/"; })}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          <ArrowLeft size={14} />
          Back to Home
        </button>
        <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase tracking-wider">
          Recruiter Portal
        </span>
      </div>

      <div className="w-full max-w-[420px] bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl shadow-lg p-7">
        {/* Brand Header */}
        <div className="flex flex-col items-start pb-4">
          <button
            onClick={onNavigateHome || (() => { window.location.pathname = "/"; })}
            className="flex items-center text-left group cursor-pointer focus:outline-none"
            aria-label="Recruit Lens Home"
          >
            <BrandLogo size="lg" asHeading={true} />
          </button>
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
            onClick={() => {
              setActiveTab("login");
              setError(null);
            }}
            className={`flex-1 min-h-[36px] text-xs font-semibold rounded-md transition-colors cursor-pointer ${
              activeTab === "login"
                ? "bg-indigo-600 text-white shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Log in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "signup"}
            onClick={() => {
              setActiveTab("signup");
              setError(null);
            }}
            className={`flex-1 min-h-[36px] text-xs font-semibold rounded-md transition-colors cursor-pointer ${
              activeTab === "signup"
                ? "bg-indigo-600 text-white shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Sign up
          </button>
        </div>

        <div className="mt-4 mb-4">
          <h2 className="text-base font-bold text-[var(--text-primary)]">
            {activeTab === "login" ? "Sign in to Recruiter Portal" : "Create Recruiter Account"}
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            {activeTab === "login"
              ? "Access your requisitions, candidate dossiers, and pipelines."
              : "Set up your recruiter profile to screen and rank candidate resumes."}
          </p>
        </div>

        {error && (
          <div className="p-3 mb-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start gap-2">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {activeTab === "signup" && (
            <div>
              <label
                htmlFor="fullName"
                className="block text-xs font-semibold text-[var(--text-primary)] mb-1"
              >
                Full Name
              </label>
              <div className="relative">
                <User size={15} className="absolute left-3 top-2.5 text-[var(--text-secondary)]" />
                <input
                  id="fullName"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Jane Doe"
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-default)] bg-[var(--bg-canvas)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          )}

          <div>
            <label
              htmlFor="email"
              className="block text-xs font-semibold text-[var(--text-primary)] mb-1"
            >
              Email Address
            </label>
            <div className="relative">
              <Mail size={15} className="absolute left-3 top-2.5 text-[var(--text-secondary)]" />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="recruiter@company.com"
                required
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-default)] bg-[var(--bg-canvas)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-xs font-semibold text-[var(--text-primary)] mb-1"
            >
              Password
            </label>
            <div className="relative">
              <Lock size={15} className="absolute left-3 top-2.5 text-[var(--text-secondary)]" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-default)] bg-[var(--bg-canvas)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors shadow-sm disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : activeTab === "login" ? (
              "Sign In to Recruiter Portal"
            ) : (
              "Create Recruiter Account"
            )}
          </button>
        </form>

        {/* Demo Account Info */}
        <div className="mt-5 pt-4 border-t border-[var(--border-default)] text-center">
          <p className="text-[11px] text-[var(--text-secondary)] font-mono">
            Demo account: <span className="text-indigo-400 font-semibold">admin@recruitlens.local</span>
          </p>
          <p className="text-[10px] text-[var(--text-tertiary)] mt-0.5 font-mono">
            Password: any password · Role: Recruiter
          </p>
        </div>
      </div>
    </div>
  );
};
