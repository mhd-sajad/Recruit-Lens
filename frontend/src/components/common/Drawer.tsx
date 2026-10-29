import React, { useEffect } from "react";
import { X, CheckCircle, FileText } from "lucide-react";

export interface EvidenceItem {
  id?: string;
  chunk_index?: number;
  section?: string;
  text: string;
  score?: number;
  relevance_score?: number;
  confidence?: number;
  source?: string;
}

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  candidateName?: string;
  evidence: EvidenceItem[];
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title = "Grounding Evidence & Citations",
  candidateName,
  evidence,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) onClose();
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-slate-900/50 backdrop-blur-sm animate-in fade-in"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md bg-white dark:bg-slate-900 h-full shadow-2xl border-l border-slate-200 dark:border-slate-800 flex flex-col slide-in-from-right animate-in">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              {title}
            </h3>
            {candidateName && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Candidate: {candidateName}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Close evidence panel"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {evidence.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <p className="text-sm">No evidence snippets cited for this selection.</p>
            </div>
          ) : (
            evidence.map((chunk, idx) => (
              <div
                key={chunk.id || idx}
                className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-2 text-sm"
              >
                <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span className="font-mono bg-slate-200/80 dark:bg-slate-700 px-1.5 py-0.5 rounded">
                    Chunk #{chunk.chunk_index !== undefined ? chunk.chunk_index : idx + 1}
                  </span>
                  {chunk.section && (
                    <span className="capitalize font-medium text-slate-700 dark:text-slate-300">
                      {chunk.section}
                    </span>
                  )}
                  {chunk.relevance_score !== undefined && (
                    <span className="text-emerald-600 dark:text-emerald-400 font-mono">
                      rel: {(chunk.relevance_score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>

                <blockquote className="text-slate-800 dark:text-slate-200 border-l-2 border-blue-500 pl-3 italic text-xs leading-relaxed whitespace-pre-wrap">
                  "{chunk.text}"
                </blockquote>

                <div className="flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400 pt-1">
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>Grounding verified against resume source</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
