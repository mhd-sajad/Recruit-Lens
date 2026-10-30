import React, { useState, useEffect, useRef } from "react";
import {
  Users,
  Briefcase,
  BarChart3,
  Shield,
  Mail,
  FileCheck,
  Layers,
  Settings,
  LogOut,
  ChevronDown,
  Plus,
  X,
  Menu,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { cn } from "../../lib/utils";

import type { JobItem } from "../../lib/mockData";
import type { JobResponse } from "../../types/api";

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onOpenCreateJob: () => void;
  jobsList?: JobItem[];
  selectedJob?: JobItem;
  onSelectJob?: (job: JobItem) => void;
}

const NAV_ITEMS = [
  { id: "requisitions", label: "Requisitions", icon: Briefcase },
  { id: "candidates", label: "Candidates", icon: Users },
  { id: "dossier", label: "Candidate Dossier", icon: FileCheck },
  { id: "pipeline", label: "Pipeline Board", icon: Layers },
  { id: "emails", label: "Email Center", icon: Mail },
  { id: "audit", label: "Audit Log", icon: Shield },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "settings", label: "Settings", icon: Settings },
] as const;

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  onOpenCreateJob,
  jobsList,
  selectedJob,
  onSelectJob,
}) => {
  const {
    logout,
    jobs,
    activeJob,
    setActiveJob,
    isDarkMode,
    setIsDarkMode,
    isBlindMode,
    setIsBlindMode,
  } = useAuth();

  const [isJobDropdownOpen, setIsJobDropdownOpen] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);

  const activeTitle =
    selectedJob?.title || activeJob?.title || "Select a Job";
  const displayedJobs =
    jobsList && jobsList.length > 0 ? jobsList : jobs || [];

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsJobDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Close mobile sidebar on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsMobileOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const handleNavSelect = (tab: string) => {
    onSelectTab(tab);
    setIsMobileOpen(false);
  };

  const sidebarContent = (
    <nav
      ref={sidebarRef}
      className={cn(
        "flex flex-col h-full",
        "bg-[var(--bg-surface)] border-r border-[var(--border-default)]"
      )}
      aria-label="Main Navigation"
    >
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-[var(--border-default)]">
        <button
          type="button"
          onClick={() => handleNavSelect("requisitions")}
          className="flex items-center gap-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-md"
          aria-label="Recruit Lens Home"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#818CF8"
            strokeWidth="2"
            aria-hidden="true"
            className="shrink-0"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          <span className="font-bold text-[15px] text-[var(--text-primary)]">
            Recruit Lens
          </span>
        </button>

        {/* Mobile close button */}
        <button
          type="button"
          onClick={() => setIsMobileOpen(false)}
          className="ml-auto lg:hidden p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-md"
          aria-label="Close sidebar"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Job Selector */}
      <div className="px-3 py-3 border-b border-[var(--border-default)]" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setIsJobDropdownOpen(!isJobDropdownOpen)}
          aria-haspopup="listbox"
          aria-expanded={isJobDropdownOpen}
          aria-label="Select active job"
          className="w-full flex items-center justify-between gap-2 px-3 py-2 text-xs font-medium text-[var(--text-primary)] bg-[var(--bg-subtle)] hover:bg-[var(--border-default)]/40 border border-[var(--border-default)] rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <span className="truncate text-left">{activeTitle}</span>
          <ChevronDown
            className={cn("w-3.5 h-3.5 shrink-0 text-[var(--text-secondary)] transition-transform", {
              "rotate-180": isJobDropdownOpen,
            })}
            aria-hidden="true"
          />
        </button>

        {isJobDropdownOpen && (
          <div
            role="listbox"
            aria-label="Jobs list"
            className="mt-1 bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg shadow-lg z-50 overflow-hidden"
          >
            {displayedJobs.map((j) => {
              const isSelected =
                selectedJob?.id === j.id || activeJob?.id === j.id;
              return (
                <button
                  key={j.id}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    if (onSelectJob && "top_score" in j) {
                      onSelectJob(j as JobItem);
                    } else if (setActiveJob) {
                      setActiveJob(j as unknown as JobResponse);
                    }
                    setIsJobDropdownOpen(false);
                  }}
                  className={cn(
                    "w-full text-left px-3 py-2 text-xs transition-colors",
                    isSelected
                      ? "text-blue-600 dark:text-blue-400 bg-blue-500/10 font-semibold"
                      : "text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                  )}
                >
                  {j.title}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => {
                setIsJobDropdownOpen(false);
                onOpenCreateJob();
              }}
              className="w-full text-left px-3 py-2 text-xs font-semibold text-blue-600 dark:text-blue-400 border-t border-[var(--border-default)] hover:bg-[var(--bg-subtle)] transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" aria-hidden="true" />
              Create New Job...
            </button>
          </div>
        )}
      </div>

      {/* Nav Items */}
      <div className="flex-1 overflow-y-auto py-2 px-2">
        {NAV_ITEMS.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleNavSelect(item.id)}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all mb-0.5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                isActive
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
              )}
            >
              <item.icon
                className={cn("w-4 h-4 shrink-0", isActive ? "text-white" : "text-[var(--text-secondary)]")}
                aria-hidden="true"
              />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Bottom: status, blind mode, theme, logout */}
      <div className="border-t border-[var(--border-default)] px-3 py-3 space-y-2">
        {/* System status */}
        <div className="flex items-center gap-2 px-2 py-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" aria-hidden="true" />
          <span className="text-[11px] text-[var(--text-secondary)] font-mono truncate">
            Retrieval OK
          </span>
        </div>

        {/* Blind Mode */}
        <button
          type="button"
          role="switch"
          aria-checked={isBlindMode}
          onClick={() => setIsBlindMode(!isBlindMode)}
          className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-[var(--bg-subtle)] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label="Toggle Blind Screening Mode"
        >
          <span className="text-xs text-[var(--text-primary)]">Blind Mode</span>
          <span
            aria-hidden="true"
            className={cn(
              "relative inline-flex h-4 w-7 rounded-full transition-colors",
              isBlindMode ? "bg-blue-600" : "bg-[var(--border-default)]"
            )}
          >
            <span
              className={cn(
                "absolute top-0.5 h-3 w-3 rounded-full bg-white shadow transition-all",
                isBlindMode ? "left-3.5" : "left-0.5"
              )}
            />
          </span>
        </button>

        {/* Theme toggle */}
        <button
          type="button"
          onClick={() => setIsDarkMode(!isDarkMode)}
          aria-label={isDarkMode ? "Switch to light theme" : "Switch to dark theme"}
          className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-[var(--bg-subtle)] transition-colors text-xs text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <span>{isDarkMode ? "Dark Mode" : "Light Mode"}</span>
          <span aria-hidden="true" className="text-base leading-none">
            {isDarkMode ? "🌙" : "☀️"}
          </span>
        </button>

        {/* Logout */}
        <button
          type="button"
          onClick={logout}
          aria-label="Sign out"
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-red-500/10 transition-colors text-xs text-red-500 hover:text-red-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
        >
          <LogOut className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>Sign Out</span>
        </button>
      </div>
    </nav>
  );

  return (
    <>
      {/* Mobile top bar */}
      <div className="lg:hidden fixed top-0 inset-x-0 z-40 h-14 flex items-center gap-3 px-4 bg-[var(--bg-surface)] border-b border-[var(--border-default)]">
        <button
          type="button"
          onClick={() => setIsMobileOpen(true)}
          aria-label="Open navigation menu"
          className="p-2 rounded-md text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Menu className="w-5 h-5" />
        </button>

        <button
          type="button"
          onClick={() => onSelectTab("requisitions")}
          className="flex items-center gap-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-md"
          aria-label="Recruit Lens Home"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#818CF8"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          <span className="font-bold text-sm text-[var(--text-primary)]">
            Recruit Lens
          </span>
        </button>
      </div>

      {/* Mobile drawer overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 z-50 flex"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation sidebar"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setIsMobileOpen(false)}
            aria-hidden="true"
          />
          {/* Drawer */}
          <div className="relative z-10 w-60 h-full">{sidebarContent}</div>
        </div>
      )}

      {/* Desktop sidebar (always visible) */}
      <aside className="hidden lg:flex flex-col w-60 shrink-0 h-screen sticky top-0">
        {sidebarContent}
      </aside>
    </>
  );
};
