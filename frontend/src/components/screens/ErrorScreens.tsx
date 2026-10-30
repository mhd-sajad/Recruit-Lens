import React from "react";
import { ArrowLeft, AlertCircle, Clock, Home } from "lucide-react";

interface NotFoundScreenProps {
  path?: string;
  onHome?: () => void;
  onRequisitions?: () => void;
  message?: string;
}

export const NotFoundScreen: React.FC<NotFoundScreenProps> = ({
  onHome = () => { window.location.pathname = "/"; },
  onRequisitions = () => { window.location.pathname = "/requisitions"; },
  message = "The requested URL, requisition, or candidate record does not exist or does not belong to this job.",
}) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] py-16 px-4 text-center">
      <div className="w-14 h-14 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-4 border border-indigo-500/20">
        <AlertCircle size={28} />
      </div>
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">
        404 - Page Not Found
      </h1>
      <p className="text-xs text-[var(--text-secondary)] mt-2 max-w-md leading-relaxed">
        {message}
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={onHome}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-[var(--text-primary)] bg-[var(--bg-subtle)] hover:bg-[var(--border-default)] border border-[var(--border-default)] rounded-lg transition-colors cursor-pointer"
        >
          <Home size={14} />
          <span>Go to Home</span>
        </button>
        <button
          type="button"
          onClick={onRequisitions}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors shadow-xs cursor-pointer"
        >
          <ArrowLeft size={14} />
          <span>Go to Requisitions</span>
        </button>
      </div>
    </div>
  );
};

interface SessionExpiredScreenProps {
  returnTo?: string;
  onLoginAgain?: (returnTo?: string) => void;
}

export const SessionExpiredScreen: React.FC<SessionExpiredScreenProps> = ({
  returnTo,
  onLoginAgain,
}) => {
  const handleLogin = () => {
    if (onLoginAgain) {
      onLoginAgain(returnTo);
    } else {
      const qs = returnTo ? `?redirect=${encodeURIComponent(returnTo)}` : "";
      window.location.href = `/login${qs}`;
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] py-16 px-4 text-center">
      <div className="w-14 h-14 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center mb-4 border border-amber-500/20">
        <Clock size={28} />
      </div>
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">
        Your session has expired
      </h1>
      <p className="text-xs text-[var(--text-secondary)] mt-2 max-w-md leading-relaxed">
        For your security, active recruiter sessions expire after periods of inactivity. Log in again to resume your screening work.
      </p>
      <div className="mt-6">
        <button
          type="button"
          onClick={handleLogin}
          className="inline-flex items-center gap-1.5 px-5 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors shadow-xs cursor-pointer"
        >
          <span>Log in again</span>
        </button>
      </div>
    </div>
  );
};
