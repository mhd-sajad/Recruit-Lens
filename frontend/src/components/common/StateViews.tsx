import React from "react";
import { Loader2, AlertCircle, Inbox, RefreshCw } from "lucide-react";
import { cn } from "../../lib/utils";

interface LoadingProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingProps> = ({
  message = "Loading...",
  className,
}) => {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex flex-col items-center justify-center p-12 text-slate-500 dark:text-slate-400 space-y-3",
        className
      )}
    >
      <Loader2 className="w-8 h-8 animate-spin text-blue-600 dark:text-blue-400" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
};

interface EmptyProps {
  title?: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyProps> = ({
  title = "No data found",
  description = "Get started by taking an action or selecting an item.",
  action,
  className,
  icon,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-12 text-center border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl space-y-3",
        className
      )}
      data-testid="empty-state"
    >
      <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-full text-slate-400 dark:text-slate-500">
        {icon || <Inbox className="w-8 h-8" />}
      </div>
      <div className="max-w-sm space-y-1">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
          {title}
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          {description}
        </p>
      </div>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

interface ErrorProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorProps> = ({
  title = "An error occurred",
  message,
  onRetry,
  className,
}) => {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className={cn(
        "flex flex-col items-center justify-center p-8 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/60 rounded-xl text-center space-y-3",
        className
      )}
      data-testid="error-state"
    >
      <div className="p-2.5 bg-rose-100 dark:bg-rose-900/60 rounded-full text-rose-600 dark:text-rose-400">
        <AlertCircle className="w-6 h-6" />
      </div>
      <div className="max-w-md space-y-1">
        <h3 className="text-sm font-semibold text-rose-900 dark:text-rose-200">
          {title}
        </h3>
        <p className="text-xs text-rose-700 dark:text-rose-300 whitespace-pre-wrap">
          {message}
        </p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-rose-700 dark:text-rose-200 bg-white dark:bg-slate-900 border border-rose-300 dark:border-rose-800 rounded-lg shadow-sm hover:bg-rose-50 dark:hover:bg-slate-800 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Try Again
        </button>
      )}
    </div>
  );
};
