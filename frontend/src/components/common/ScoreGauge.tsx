import React from "react";

export interface ScoreGaugeProps {
  score: number; // 0 to 100
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  score,
  size = 96,
  strokeWidth = 8,
  showLabel = true,
}) => {
  const normalizedScore = Math.max(0, Math.min(100, Math.round(score)));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference;

  let colorClass = "text-red-500 stroke-red-500";
  if (normalizedScore >= 85) {
    colorClass = "text-emerald-500 stroke-emerald-500";
  } else if (normalizedScore >= 70) {
    colorClass = "text-sky-500 stroke-sky-500";
  } else if (normalizedScore >= 55) {
    colorClass = "text-amber-500 stroke-amber-500";
  }

  return (
    <div
      className="relative inline-flex items-center justify-center"
      role="meter"
      aria-valuenow={normalizedScore}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Match score: ${normalizedScore} out of 100`}
    >
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          className="stroke-[var(--border-default)]"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          className={`${colorClass} transition-all duration-500 ease-out`}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
        />
      </svg>
      {showLabel && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            {normalizedScore}
          </span>
          <span className="text-[10px] uppercase font-semibold text-[var(--text-secondary)]">
            / 100
          </span>
        </div>
      )}
    </div>
  );
};
