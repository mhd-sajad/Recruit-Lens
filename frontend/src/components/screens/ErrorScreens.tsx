import React from "react";
import { ArrowLeft, AlertCircle, ShieldAlert } from "lucide-react";

export const NotFoundScreen: React.FC<{ onHome: () => void }> = ({ onHome }) => {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
      <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-500 flex items-center justify-center mb-4">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h1 className="text-xl font-bold text-[var(--text-primary)]">404 - Screen Not Found</h1>
      <p className="text-xs text-[var(--text-secondary)] mt-1.5 max-w-sm">
        The requested requisition, candidate dossier, or page could not be located.
      </p>
      <button
        type="button"
        onClick={onHome}
        className="mt-5 inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Return to Requisitions</span>
      </button>
    </div>
  );
};

export const ForbiddenScreen: React.FC<{ onHome: () => void }> = ({ onHome }) => {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
      <div className="w-12 h-12 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mb-4">
        <ShieldAlert className="w-6 h-6" />
      </div>
      <h1 className="text-xl font-bold text-[var(--text-primary)]">403 - Access Restricted</h1>
      <p className="text-xs text-[var(--text-secondary)] mt-1.5 max-w-sm">
        Your current role does not have permission to view this compliance audit block or
        override screening scores.
      </p>
      <button
        type="button"
        onClick={onHome}
        className="mt-5 inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Return to Safe Workspace</span>
      </button>
    </div>
  );
};
