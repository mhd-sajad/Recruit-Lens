import React from "react";
import { Check, Circle, Clock, X } from "lucide-react";

export type TierType = "FastTrack" | "Interview" | "Hold" | "Reject" | "strong_fit" | "interview" | "hold" | "reject";

export interface TierBadgeProps {
  tier: TierType | string;
  size?: "sm" | "md";
  className?: string;
}

export const TierBadge: React.FC<TierBadgeProps> = ({ tier, size = "md", className = "" }) => {
  const normalizedTier = tier.toLowerCase().replace("_", "");

  const sizeClasses = size === "sm" ? "text-xs px-2 py-0.5" : "text-xs px-2.5 py-1 font-medium";
  const iconSize = size === "sm" ? 11 : 13;

  if (normalizedTier.includes("fasttrack") || normalizedTier.includes("strongfit")) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 font-medium ${sizeClasses} ${className}`}
        aria-label="Tier: FastTrack (Strong Fit)"
      >
        <Check size={iconSize} className="stroke-[2.5]" aria-hidden="true" />
        <span>FastTrack</span>
      </span>
    );
  }

  if (normalizedTier.includes("interview")) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-full border border-sky-500/30 bg-sky-500/15 text-sky-700 dark:text-sky-400 font-medium ${sizeClasses} ${className}`}
        aria-label="Tier: Interview (Qualified)"
      >
        <Circle size={iconSize} className="fill-current stroke-[2]" aria-hidden="true" />
        <span>Interview</span>
      </span>
    );
  }

  if (normalizedTier.includes("hold")) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/15 text-amber-700 dark:text-amber-400 font-medium ${sizeClasses} ${className}`}
        aria-label="Tier: Hold (Borderline)"
      >
        <Clock size={iconSize} className="stroke-[2.5]" aria-hidden="true" />
        <span>Hold</span>
      </span>
    );
  }

  // Default to Reject
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border border-red-500/30 bg-red-500/15 text-red-700 dark:text-red-400 font-medium ${sizeClasses} ${className}`}
      aria-label="Tier: Reject (Missing Must-Haves)"
    >
      <X size={iconSize} className="stroke-[2.5]" aria-hidden="true" />
      <span>Reject</span>
    </span>
  );
};
