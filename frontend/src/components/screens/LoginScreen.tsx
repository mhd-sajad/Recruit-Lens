import React, { useState } from "react";
import { Briefcase, KeyRound, Mail, AlertCircle, Info } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export const LoginScreen: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState("admin@recruitlens.local");
  const [password, setPassword] = useState("Admin123!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-50 dark:bg-slate-950">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="p-8 text-center bg-gradient-to-b from-blue-50/60 to-transparent dark:from-blue-950/20 border-b border-slate-100 dark:border-slate-800/60">
          <div className="w-12 h-12 rounded-2xl bg-blue-600 flex items-center justify-center text-white mx-auto shadow-lg shadow-blue-500/30 mb-3">
            <Briefcase className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">
            Recruit Lens
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Explainable, Evidence-Grounded AI Recruiter Platform
          </p>
        </div>

        {/* Demo Credentials Banner */}
        <div className="mx-6 mt-6 p-3.5 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/60 rounded-xl flex items-start gap-3">
          <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
          <div className="text-xs text-blue-800 dark:text-blue-200 space-y-1">
            <p className="font-semibold">Demo Evaluation Credentials:</p>
            <div className="font-mono text-[11px] bg-white/70 dark:bg-slate-900/70 p-2 rounded border border-blue-100 dark:border-blue-900/40">
              <div>Email: <strong className="text-blue-900 dark:text-blue-100">admin@recruitlens.local</strong></div>
              <div>Password: <strong className="text-blue-900 dark:text-blue-100">Admin123!</strong></div>
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-4">
          {error && (
            <div
              role="alert"
              aria-live="assertive"
              className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 rounded-lg text-xs flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label
              htmlFor="login-email-input"
              className="text-xs font-medium text-slate-700 dark:text-slate-300"
            >
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                id="login-email-input"
                type="email"
                required
                className="w-full text-xs pl-9 pr-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="recruiter@company.com"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="login-password-input"
              className="text-xs font-medium text-slate-700 dark:text-slate-300"
            >
              Password
            </label>
            <div className="relative">
              <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                id="login-password-input"
                type="password"
                required
                className="w-full text-xs pl-9 pr-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium text-xs rounded-lg shadow-md shadow-blue-500/20 transition flex items-center justify-center gap-2"
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

          <p className="text-[11px] text-center text-slate-400 dark:text-slate-500 mt-4">
            Invite-only access • Strict RBAC & Session Security
          </p>
        </form>
      </div>
    </div>
  );
};
