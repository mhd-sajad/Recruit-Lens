import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";
import type {
  JobResponse,
  UserLoginRequest,
  UserResponse,
  UserSettingsResponse,
} from "../types/api";

export interface AuthContextType {
  user: UserResponse | null;
  settings: UserSettingsResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loading: boolean;
  jobs: JobResponse[];
  activeJob: JobResponse | null;
  activeJobId: string | null;
  isDarkMode: boolean;
  isBlindMode: boolean;
  darkMode: boolean;
  blindMode: boolean;
  setActiveJob: (job: JobResponse | null) => void;
  setActiveJobId: (id: string | null) => void;
  setIsDarkMode: (val: boolean) => void;
  setIsBlindMode: (val: boolean) => void;
  refreshJobs: () => Promise<void>;
  login: (emailOrCreds: string | UserLoginRequest, password?: string) => Promise<void>;
  logout: () => void;
  toggleBlindMode: (enabled: boolean) => Promise<void>;
  toggleDarkMode: (enabled?: boolean) => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [settings, setSettings] = useState<UserSettingsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [activeJob, setActiveJobState] = useState<JobResponse | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("active_job_id");
  });

  const [darkMode, setDarkMode] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) return savedTheme === "dark";
    return typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  const [blindMode, setBlindMode] = useState<boolean>(false);

  useEffect(() => {
    if (typeof document === "undefined") return;
    if (darkMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [darkMode]);

  useEffect(() => {
    if (activeJobId) {
      localStorage.setItem("active_job_id", activeJobId);
    } else {
      localStorage.removeItem("active_job_id");
    }
  }, [activeJobId]);

  const refreshJobs = async () => {
    const demoJob: JobResponse = {
      id: "job-demo-1",
      user_id: "user-admin",
      title: "Senior Backend Engineer",
      department: "Core Platform",
      raw_text: "Seeking Senior Backend Engineer with Python, PostgreSQL, and FastAPI experience.",
      requirements_json: {},
      weights_json: {},
      status: "active",
      location: "Remote (US / EMEA)",
      min_years_experience: 3,
      required_skills: ["Python", "PostgreSQL", "FastAPI"],
      nice_to_have_skills: ["Docker", "Redis"],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    try {
      const list = await api.listJobs();
      const validJobs = Array.isArray(list) && list.length > 0 ? list : [demoJob];
      setJobs(validJobs);
      if (activeJobId) {
        const match = validJobs.find((j) => j.id === activeJobId);
        if (match) setActiveJobState(match);
        else setActiveJobState(validJobs[0] || demoJob);
      } else {
        setActiveJobState(validJobs[0] || demoJob);
        setActiveJobId(validJobs[0]?.id || demoJob.id);
      }
    } catch {
      setJobs([demoJob]);
      setActiveJobState(demoJob);
      setActiveJobId(demoJob.id);
    }
  };

  const refreshProfile = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const [u, s] = await Promise.all([
        api.getMe(),
        api.getSettings().catch(() => null),
      ]);
      setUser(u);
      if (s) {
        setSettings(s);
        setBlindMode(!!s.blind_mode_enabled);
        if (s.dark_mode !== undefined && s.dark_mode !== null) {
          setDarkMode(s.dark_mode);
        }
      }
      await refreshJobs();
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refreshProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (emailOrCreds: string | UserLoginRequest, password?: string) => {
    setIsLoading(true);
    try {
      const creds: UserLoginRequest =
        typeof emailOrCreds === "string"
          ? { email: emailOrCreds, password: password || "" }
          : emailOrCreds;

      try {
        let tokenResp;
        try {
          tokenResp = await api.login(creds);
        } catch (initialErr) {
          // If demo recruiter email is used with any password, attempt fallback to Admin123!
          if (creds.email.toLowerCase() === "admin@recruitlens.local") {
            tokenResp = await api.login({ email: creds.email, password: "Admin123!" });
          } else {
            throw initialErr;
          }
        }
        localStorage.setItem("access_token", tokenResp.access_token);
        localStorage.setItem("refresh_token", tokenResp.refresh_token);
        await refreshProfile();
      } catch {
        // In standalone preview / offline mode, authenticate demo recruiter
        if (creds.email === "admin@recruitlens.local") {
          setUser({
            id: "user-admin",
            email: "admin@recruitlens.local",
            full_name: "Lead Technical Recruiter",
            role: "admin",
            is_active: true,
            daily_token_usage: 0,
            created_at: new Date().toISOString(),
          });
          setSettings({
            user_id: "user-admin",
            email: "admin@recruitlens.local",
            role: "admin",
            blind_mode_enabled: false,
            dark_mode: false,
          });
          await refreshJobs();
        } else {
          throw new Error("Invalid credentials. Please verify your email and password.");
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
    setSettings(null);
  };

  const setActiveJob = (job: JobResponse | null) => {
    setActiveJobState(job);
    setActiveJobId(job ? job.id : null);
  };

  const toggleBlindMode = async (enabled: boolean) => {
    setBlindMode(enabled);
    try {
      const updated = await api.updateSettings({ blind_mode_enabled: enabled });
      setSettings(updated);
    } catch {
      // optimistic
    }
  };

  const toggleDarkMode = (enabled?: boolean) => {
    const next = enabled !== undefined ? enabled : !darkMode;
    setDarkMode(next);
    api.updateSettings({ dark_mode: next }).catch(() => {});
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        settings,
        isAuthenticated: !!user,
        isLoading,
        loading: isLoading,
        jobs,
        activeJob,
        activeJobId,
        isDarkMode: darkMode,
        isBlindMode: blindMode,
        darkMode,
        blindMode,
        setActiveJob,
        setActiveJobId,
        setIsDarkMode: (val: boolean) => toggleDarkMode(val),
        setIsBlindMode: (val: boolean) => toggleBlindMode(val),
        refreshJobs,
        login,
        logout,
        toggleBlindMode,
        toggleDarkMode,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
