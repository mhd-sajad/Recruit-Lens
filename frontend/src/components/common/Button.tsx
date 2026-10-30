import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  icon,
  children,
  className = "",
  disabled,
  ...props
}) => {
  const baseClasses =
    "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed rounded-[8px] min-h-[36px] min-w-[36px] sm:min-w-0";

  const sizeClasses = {
    sm: "text-xs px-2.5 py-1.5 h-8 min-h-[32px]",
    md: "text-sm px-3.5 py-2 h-9 min-h-[36px]",
    lg: "text-base px-4 py-2.5 h-11 min-h-[44px]",
  };

  const variantClasses = {
    primary:
      "bg-[#2563eb] text-white hover:bg-[#1d4ed8] active:bg-[#1e40af] shadow-xs",
    secondary:
      "bg-[var(--bg-subtle)] text-[var(--text-primary)] hover:bg-[var(--border-default)] border border-[var(--border-default)]",
    outline:
      "bg-transparent text-[var(--text-primary)] border border-[var(--border-default)] hover:bg-[var(--bg-subtle)]",
    ghost:
      "bg-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]",
    danger:
      "bg-red-600 text-white hover:bg-red-700 active:bg-red-800 shadow-xs",
  };

  return (
    <button
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      disabled={disabled}
      aria-disabled={disabled}
      {...props}
    >
      {icon && <span className="mr-1.5 flex items-center">{icon}</span>}
      {children}
    </button>
  );
};
