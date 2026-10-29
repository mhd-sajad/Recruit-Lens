import React from "react";
import {
  Briefcase,
  Users,
  LayoutGrid,
  BarChart3,
  Settings,
  Shield,
  Sun,
  Moon,
  LogOut,
  Upload,
  Plus,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { cn } from "../../lib/utils";

interface NavbarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onOpenCreateJob: () => void;
  onOpenUpload: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onSelectTab,
  onOpenCreateJob,
  onOpenUpload,
}) => {
  const {
    user,
    logout,
    jobs,
    activeJob,
    setActiveJob,
    isDarkMode,
    setIsDarkMode,
    isBlindMode,
    setIsBlindMode,
  } = useAuth();

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutGrid },
    { id: "candidates", label: "Candidates", icon: Users },
    { id: "pipeline", label: "Pipeline", icon: Briefcase },
    { id: "reports", label: "Reports", icon: BarChart3 },
    { id: "settings", label: "Settings & Logs", icon: Settings },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white/90 dark:bg-slate-900/90 backdrop-blur border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Logo & Product Name */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => onSelectTab("dashboard")}>
              <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
                <Briefcase className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-base font-bold text-slate-900 dark:text-slate-100 leading-tight">
                  Recruit Lens
                </h1>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                  Evidence-Grounded AI
                </p>
              </div>
            </div>

            {/* Active Job Requisition Selector */}
            <div className="hidden md:flex items-center gap-2 pl-4 border-l border-slate-200 dark:border-slate-800">
              <label htmlFor="active-job-select" className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                Active Job:
              </label>
              <select
                id="active-job-select"
                aria-label="Active Job Requisition"
                className="text-xs bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5 font-medium text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-blue-500 max-w-[220px] truncate"
                value={activeJob?.id || ""}
                onChange={(e) => {
                  const selected = (jobs || []).find((j) => j.id === e.target.value);
                  if (selected) setActiveJob(selected);
                }}
              >
                {(jobs || []).length === 0 ? (
                  <option value="">No Active Jobs</option>
                ) : (
                  (jobs || []).map((job) => (
                    <option key={job.id} value={job.id}>
                      {job.title} ({job.department || "General"})
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition",
                    isActive
                      ? "bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 font-semibold"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Actions & Toggles */}
          <div className="flex items-center gap-2.5">
            {/* Quick action buttons */}
            <button
              onClick={onOpenCreateJob}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
              title="Create new job requisition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Job</span>
            </button>
            <button
              onClick={onOpenUpload}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition"
              title="Upload resumes in batch"
            >
              <Upload className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Upload</span>
            </button>

            {/* Blind Mode Toggle Button */}
            <button
              onClick={() => setIsBlindMode(!isBlindMode)}
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition",
                isBlindMode
                  ? "bg-purple-50 text-purple-700 border-purple-300 dark:bg-purple-950/70 dark:text-purple-300 dark:border-purple-700 font-semibold"
                  : "bg-slate-50 text-slate-500 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700"
              )}
              title="Toggle Blind Review Mode (redacts candidate name, email, and demographics)"
              aria-label="Toggle Blind Mode"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Blind {isBlindMode ? "ON" : "OFF"}</span>
            </button>

            {/* Dark Mode Toggle */}
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className="p-1.5 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              aria-label="Toggle color theme"
            >
              {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            {/* User profile & logout */}
            <div className="flex items-center gap-2 pl-2 border-l border-slate-200 dark:border-slate-800">
              <span className="hidden xl:inline text-xs font-medium text-slate-700 dark:text-slate-300 max-w-[120px] truncate">
                {user?.full_name || user?.email || "Recruiter"}
              </span>
              <button
                onClick={logout}
                className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/50 transition"
                title="Log out"
                aria-label="Log out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
