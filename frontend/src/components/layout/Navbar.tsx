import React, { useState } from "react";
import {
  Users,
  Briefcase,
  BarChart3,
  Shield,
  Mail,
  FileCheck,
  Layers,
  HelpCircle,
  LogOut,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { cn } from "../../lib/utils";

import type { JobItem } from "../../lib/mockData";

interface NavbarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onOpenCreateJob: () => void;
  jobsList?: JobItem[];
  selectedJob?: JobItem;
  onSelectJob?: (job: JobItem) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
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

  const activeTitle =
    selectedJob?.title || activeJob?.title || "Staff Backend Engineer – Distributed Systems";
  const displayedJobs = (jobsList && jobsList.length > 0) ? jobsList : (jobs || []);

  const navItems = [
    { id: "requisitions", label: "Requisitions", icon: Briefcase },
    { id: "candidates", label: "Candidates", icon: Users },
    { id: "dossier", label: "Dossier", icon: FileCheck },
    { id: "pipeline", label: "Pipeline", icon: Layers },
    { id: "emails", label: "Email Center", icon: Mail },
    { id: "audit", label: "Audit Log", icon: Shield },
    { id: "analytics", label: "Analytics", icon: BarChart3 },
    { id: "settings", label: "Settings", icon: HelpCircle },
  ];

  return (
    <header
      style={{
        height: "56px",
        display: "flex",
        alignItems: "center",
        gap: "16px",
        padding: "0 24px",
        borderBottom: "1px solid #374151",
        background: "#0F1318",
        position: "sticky",
        top: 0,
        zIndex: 40,
      }}
    >
      {/* Brand & Lens Icon from Design */}
      <div
        style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", userSelect: "none" }}
        onClick={() => onSelectTab("requisitions")}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") onSelectTab("requisitions");
        }}
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
        >
          <circle cx="11" cy="11" r="7" />
          <path d="M21 21l-4.3-4.3" />
        </svg>
        <b style={{ color: "#E6EAF0", fontSize: "15px" }}>Recruit Lens</b>
      </div>

      {/* Active Job Selector Dropdown Button */}
      <div style={{ position: "relative" }}>
        <button
          type="button"
          className="btn"
          style={{ marginLeft: "4px" }}
          onClick={() => setIsJobDropdownOpen(!isJobDropdownOpen)}
          aria-haspopup="listbox"
          aria-expanded={isJobDropdownOpen}
        >
          Job: {activeTitle} ▾
        </button>

        {isJobDropdownOpen && (
          <div
            role="listbox"
            style={{
              position: "absolute",
              left: "4px",
              top: "100%",
              marginTop: "4px",
              background: "#1F2937",
              border: "1px solid #374151",
              borderRadius: "8px",
              zIndex: 50,
              minWidth: "280px",
              boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
              overflow: "hidden",
            }}
          >
            {displayedJobs.map((j) => {
              const isSelected = selectedJob?.id === j.id || activeJob?.id === j.id;
              return (
                <button
                  key={j.id}
                  type="button"
                  onClick={() => {
                    if (onSelectJob && "top_score" in j) {
                      onSelectJob(j as JobItem);
                    } else if (setActiveJob) {
                      setActiveJob(j as any);
                    }
                    setIsJobDropdownOpen(false);
                  }}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    padding: "10px 14px",
                    fontSize: "13px",
                    color: isSelected ? "#60A5FA" : "#E6EAF0",
                    background: isSelected ? "rgba(37,99,235,0.15)" : "transparent",
                    border: 0,
                    cursor: "pointer",
                  }}
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
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "10px 14px",
                fontSize: "13px",
                color: "#60A5FA",
                borderTop: "1px solid #374151",
                background: "transparent",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              + Create New Job...
            </button>
          </div>
        )}
      </div>

      {/* Navigation tabs */}
      <nav
        className="hidden xl:flex items-center gap-1.5"
        style={{ marginLeft: "8px" }}
        aria-label="Main Navigation"
      >
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectTab(item.id)}
              className={cn(
                "btn",
                isActive && "p"
              )}
              style={{
                padding: "6px 11px",
                fontSize: "12px",
                minHeight: "32px",
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
              }}
              aria-current={isActive ? "page" : undefined}
            >
              <item.icon style={{ width: "13px", height: "13px" }} aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div style={{ flex: 1 }} />

      {/* Right Side: Status, Blind Mode Switch, Theme, Profile */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {/* System Status Telemetry */}
        <span
          className="m hidden md:inline-flex items-center gap-1.5"
          style={{ fontSize: "12px", fontFamily: "ui-monospace, monospace" }}
        >
          <span style={{ color: "#34D399" }}>●</span> Retrieval OK · BM25 + embeddings · p95 420 ms · Audit chain verified
        </span>

        {/* Blind Mode Switch from Design */}
        <button
          role="switch"
          aria-checked={isBlindMode}
          onClick={() => setIsBlindMode(!isBlindMode)}
          className="btn"
          style={{ display: "flex", gap: "8px", alignItems: "center" }}
          title="Toggle Blind Screening Mode"
        >
          <span>Blind mode</span>
          <span
            style={{
              width: "30px",
              height: "16px",
              borderRadius: "9px",
              background: isBlindMode ? "#2563EB" : "#2E3844",
              display: "inline-block",
              position: "relative",
              transition: "background-color 0.15s ease",
            }}
          >
            <span
              style={{
                position: "absolute",
                top: "2px",
                left: isBlindMode ? "16px" : "2px",
                width: "12px",
                height: "12px",
                borderRadius: "6px",
                background: "#fff",
                transition: "left 0.15s ease",
              }}
            />
          </span>
        </button>

        {/* Theme Toggle from Design */}
        <button
          type="button"
          className="btn"
          aria-label="Toggle theme"
          onClick={() => setIsDarkMode(!isDarkMode)}
          title={isDarkMode ? "Switch to light theme" : "Switch to dark theme"}
          style={{ padding: "8px 12px" }}
        >
          ◐
        </button>

        {/* Recruiter Logout */}
        <button
          type="button"
          onClick={logout}
          className="btn"
          title="Sign out"
          aria-label="Sign out"
          style={{ padding: "8px 10px", color: "#F87171" }}
        >
          <LogOut style={{ width: "14px", height: "14px" }} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
};
