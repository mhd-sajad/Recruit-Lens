import React from "react";

export const Skeleton: React.FC<{ className?: string }> = ({ className = "" }) => {
  return (
    <div
      className={`animate-pulse bg-[var(--border-default)]/40 rounded-[6px] ${className}`}
      aria-hidden="true"
    />
  );
};

export const TableRowSkeleton: React.FC<{ columns?: number }> = ({ columns = 7 }) => {
  return (
    <tr className="border-b border-[var(--border-default)]/40 animate-pulse">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="py-3.5 px-4">
          <Skeleton className="h-4 w-full max-w-[120px]" />
        </td>
      ))}
    </tr>
  );
};

export const CardSkeleton: React.FC = () => {
  return (
    <div
      className="p-5 rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-surface)] space-y-3.5"
      aria-busy="true"
      aria-label="Loading content..."
    >
      <div className="flex justify-between items-start">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="h-3.5 w-1/3" />
      <div className="pt-2">
        <Skeleton className="h-2 w-full rounded-full" />
      </div>
      <div className="flex justify-between items-center pt-2">
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-8 w-20 rounded-[8px]" />
      </div>
    </div>
  );
};
