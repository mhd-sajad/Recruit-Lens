import React from "react";

export interface CitationPillProps {
  id: string; // e.g. "c_01"
  onClick?: (id: string) => void;
  isActive?: boolean;
}

export const CitationPill: React.FC<CitationPillProps> = ({ id, onClick, isActive = false }) => {
  return (
    <button
      type="button"
      onClick={() => onClick && onClick(id)}
      className={`inline-flex items-center justify-center mx-1 px-1.5 py-0.5 rounded-[4px] text-xs font-mono font-medium border transition-colors cursor-pointer select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
        isActive
          ? "bg-blue-600 text-white border-blue-500 shadow-xs"
          : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30 hover:bg-blue-500/20 active:bg-blue-500/30"
      }`}
      aria-label={`View source evidence citation ${id}`}
      title={`Click to jump to evidence citation ${id} in original resume text`}
    >
      [{id}]
    </button>
  );
};
