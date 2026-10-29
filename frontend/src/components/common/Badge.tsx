import React from "react";
import { cn } from "../../lib/utils";

export type TierType = "strong_fit" | "interview" | "hold" | "reject" | "abstain" | string;
export type StageType = "new" | "screened" | "shortlisted" | "interview" | "offered" | "hired" | "rejected" | "withdrawn" | string;

interface BadgeProps {
  variant?: "tier" | "stage" | "source" | "status" | "default";
  value: string;
  className?: string;
  label?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = "default",
  value,
  className,
  label,
}) => {
  const normValue = (value || "").toLowerCase().replace(/[\s-]/g, "_");

  let colorClasses = "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700";

  if (variant === "tier") {
    switch (normValue) {
      case "strong_fit":
      case "fasttrack":
        colorClasses = "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-700";
        break;
      case "interview":
      case "review":
        colorClasses = "bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-700";
        break;
      case "hold":
        colorClasses = "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-700";
        break;
      case "reject":
        colorClasses = "bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-700";
        break;
      case "abstain":
      case "insufficient_information":
        colorClasses = "bg-purple-50 text-purple-700 border-purple-300 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-700";
        break;
    }
  } else if (variant === "stage") {
    switch (normValue) {
      case "hired":
        colorClasses = "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-900/60 dark:text-emerald-200 dark:border-emerald-700";
        break;
      case "offered":
      case "interview":
      case "shortlisted":
        colorClasses = "bg-sky-50 text-sky-700 border-sky-300 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-700";
        break;
      case "screened":
      case "new":
        colorClasses = "bg-indigo-50 text-indigo-700 border-indigo-300 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-700";
        break;
      case "rejected":
        colorClasses = "bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-700";
        break;
      default:
        colorClasses = "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
    }
  } else if (variant === "source") {
    if (normValue.includes("template")) {
      colorClasses = "bg-cyan-50 text-cyan-700 border-cyan-300 dark:bg-cyan-950/60 dark:text-cyan-300 dark:border-cyan-700";
    } else {
      colorClasses = "bg-violet-50 text-violet-700 border-violet-300 dark:bg-violet-950/60 dark:text-violet-300 dark:border-violet-700";
    }
  }

  const displayText =
    label ||
    (normValue === "strong_fit"
      ? "Strong Fit"
      : normValue === "abstain"
      ? "Insufficient Info"
      : value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, " "));

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border tracking-wide",
        colorClasses,
        className
      )}
      data-testid={`badge-${normValue}`}
    >
      {displayText}
    </span>
  );
};
