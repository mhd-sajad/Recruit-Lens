import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Sidebar } from "./components/layout/Sidebar";
import { ToastProvider, useToast } from "./components/common/Toast";

// Screens
import { LoginScreen } from "./components/screens/LoginScreen";
import { RequisitionsScreen } from "./components/screens/RequisitionsScreen";
import { RankedTableScreen } from "./components/screens/RankedTableScreen";
import { CandidateDossierScreen } from "./components/screens/CandidateDossierScreen";
import { PipelineBoardScreen } from "./components/screens/PipelineBoardScreen";
import { EmailCenterScreen } from "./components/screens/EmailCenterScreen";
import { AuditLogScreen } from "./components/screens/AuditLogScreen";
import { AnalyticsScreen } from "./components/screens/AnalyticsScreen";
import { SettingsScreen } from "./components/screens/SettingsScreen";
import { JobCreateModal } from "./components/screens/JobCreateModal";
import { NotFoundScreen } from "./components/screens/ErrorScreens";
import { api } from "./lib/api";
import { jobResponseToJobItem, evaluationSummaryToCandidateItem } from "./lib/transformers";

// Mock & Initial Data
import {
  INITIAL_JOBS,
  INITIAL_CANDIDATES,
  SAMPLE_DOSSIER_6299,
  type JobItem,
  type CandidateItem,
  type CandidateDossier,
} from "./lib/mockData";

const MainAppContent: React.FC = () => {
  const { isAuthenticated, isLoading, activeJob, jobs, refreshJobs, setActiveJob } = useAuth();
  const { showToast } = useToast();

  // Navigation state
  const [currentTab, setCurrentTab] = useState<string>("requisitions");

  // Requisitions & Active Job
  const [jobsList, setJobsList] = useState<JobItem[]>(INITIAL_JOBS);
  const [selectedJob, setSelectedJob] = useState<JobItem>(INITIAL_JOBS[0]!);

  // Candidates for Active Job
  const [candidatesList, setCandidatesList] = useState<CandidateItem[]>(INITIAL_CANDIDATES);

  // Active Candidate Dossier
  const [dossier, setDossier] = useState<CandidateDossier>(SAMPLE_DOSSIER_6299);

  // Job Creation Modal
  const [isCreateJobOpen, setIsCreateJobOpen] = useState(false);

  // Sync backend jobs into jobsList
  useEffect(() => {
    if (jobs && jobs.length > 0) {
      const converted = jobs.map((j) => jobResponseToJobItem(j));
      const convertedIds = new Set(converted.map((c) => c.id));
      const remainingInitial = INITIAL_JOBS.filter((j) => !convertedIds.has(j.id));
      const merged = [...converted, ...remainingInitial];
      setJobsList(merged);

      setSelectedJob((current) => {
        if (current) {
          const matchCurrent = merged.find((m) => m.id === current.id);
          if (matchCurrent) return matchCurrent;
        }
        if (activeJob) {
          const matchActive = merged.find((m) => m.id === activeJob.id);
          if (matchActive) return matchActive;
        }
        return merged[0] || current;
      });
    }
  }, [jobs, activeJob]);

  // Fetch real candidate evaluations when selectedJob changes
  useEffect(() => {
    let isCancelled = false;

    const fetchCandidates = async () => {
      try {
        const evals = await api.getCandidates(selectedJob.id);
        if (!isCancelled && Array.isArray(evals) && evals.length > 0) {
          const transformed = evals.map((e, idx) => evaluationSummaryToCandidateItem(e, idx));
          setCandidatesList(transformed);
          return;
        }
      } catch {
        // Fallback to initial candidates if network or not yet evaluated
      }
      if (!isCancelled) {
        setCandidatesList(INITIAL_CANDIDATES);
      }
    };

    fetchCandidates();

    return () => {
      isCancelled = true;
    };
  }, [selectedJob.id]);

  // Handle selecting candidate to view Dossier
  const handleOpenDossier = (candId: string) => {
    // Find candidate item
    const cand = candidatesList.find((c) => c.id === candId);
    if (cand) {
      setDossier({
        ...SAMPLE_DOSSIER_6299,
        candidate: cand,
      });

      api
        .getCandidateDetail(candId)
        .then((detail) => {
          if (detail && detail.id && detail.breakdown) {
            const contributions = Object.entries(detail.breakdown).map(
              ([k, val]) => {
                const v = val as { score?: number; weight?: number } | undefined;
                return {
                  feature: k.charAt(0).toUpperCase() + k.slice(1) + " Assessment",
                  delta: Math.round(((v?.score ?? 0.8) * (v?.weight ?? 0.25)) * 100),
                  description: `Evidence-backed model component (${Math.round((v?.score ?? 0.8) * 100)}% fit score)`,
                };
              }
            );
            if (contributions.length > 0) {
              setDossier((prev) => ({
                ...prev,
                candidate: cand,
                score_contributions: contributions,
              }));
            }
          }
        })
        .catch(() => {});
    }
    setCurrentTab("dossier");
  };

  // Handle opening email center for candidate
  const handleOpenEmailForCandidate = (candId: string) => {
    void candId;
    setCurrentTab("emails");
  };

  // Handle Job Select from Requisitions screen
  const handleSelectJobFromRequisitions = (job: JobItem) => {
    setSelectedJob(job);
    const backendMatch = jobs?.find((j) => j.id === job.id);
    if (backendMatch && setActiveJob) setActiveJob(backendMatch);
    setCurrentTab("candidates");
  };

  // Handle Job Creation Success
  const handleJobCreated = async (newJob: JobItem) => {
    setJobsList((prev) => [newJob, ...prev]);
    setSelectedJob(newJob);
    await refreshJobs().catch(() => {});
    const match = jobs.find((j) => j.id === newJob.id);
    if (match && setActiveJob) {
      setActiveJob(match);
    }
    showToast(`Requisition "${newJob.title}" created successfully!`, "success");
    setCurrentTab("candidates");
  };

  // Handle candidate stage update on Pipeline Kanban
  const handleUpdateCandidateStage = (candId: string, newStage: CandidateItem["stage"]) => {
    setCandidatesList((prev) =>
      prev.map((c) => (c.id === candId ? { ...c, stage: newStage } : c))
    );
    showToast(`Candidate stage moved to ${newStage}`, "info");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-canvas)] text-xs text-[var(--text-secondary)]">
        <span className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-2" />
        Initializing Recruit Lens...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-canvas)] text-[var(--text-primary)] font-sans transition-colors">
      {/* Fixed 240px Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        onOpenCreateJob={() => setIsCreateJobOpen(true)}
        jobsList={jobsList}
        selectedJob={selectedJob}
        onSelectJob={(job) => {
          setSelectedJob(job);
          const backendMatch = jobs?.find((j) => j.id === job.id);
          if (backendMatch && setActiveJob) setActiveJob(backendMatch);
          setCurrentTab("candidates");
        }}
      />

      {/* Scrollable Main Content Area */}
      <div className="flex-1 overflow-y-auto min-w-0 lg:pt-0 pt-14">
        <main className="p-6 max-w-[1280px] mx-auto">
          {currentTab === "requisitions" && (
            <RequisitionsScreen
              jobs={jobsList}
              onSelectJob={handleSelectJobFromRequisitions}
              onCreateJob={() => setIsCreateJobOpen(true)}
            />
          )}

          {currentTab === "candidates" && (
            <RankedTableScreen
              job={selectedJob}
              candidates={candidatesList}
              onSelectCandidate={handleOpenDossier}
              onOpenEmail={handleOpenEmailForCandidate}
              onExportAudit={() => setCurrentTab("audit")}
              onNavigateRequisitions={() => setCurrentTab("requisitions")}
            />
          )}

          {currentTab === "dossier" && (
            <CandidateDossierScreen
              dossier={dossier}
              candidatesList={candidatesList}
              onBack={() => setCurrentTab("candidates")}
              onNextCandidate={(nextId) => handleOpenDossier(nextId)}
              onOpenEmail={(candId) => handleOpenEmailForCandidate(candId)}
            />
          )}

          {currentTab === "pipeline" && (
            <PipelineBoardScreen
              candidates={candidatesList}
              onSelectCandidate={handleOpenDossier}
              onUpdateCandidateStage={handleUpdateCandidateStage}
            />
          )}

          {currentTab === "emails" && (
            <EmailCenterScreen
              initialCandidateCode={dossier.candidate.code}
              onSendSuccess={() => {
                showToast("Email logged and queued with cryptographic audit hash.", "success");
              }}
            />
          )}

          {currentTab === "audit" && <AuditLogScreen />}

          {currentTab === "analytics" && <AnalyticsScreen />}

          {currentTab === "settings" && <SettingsScreen />}

          {![
            "requisitions",
            "candidates",
            "dossier",
            "pipeline",
            "emails",
            "audit",
            "analytics",
            "settings",
          ].includes(currentTab) && (
            <NotFoundScreen onHome={() => setCurrentTab("requisitions")} />
          )}
        </main>
      </div>

      {/* Requisition Creator 3-Step Wizard Modal */}
      <JobCreateModal
        isOpen={isCreateJobOpen}
        onClose={() => setIsCreateJobOpen(false)}
        onCreateSuccess={handleJobCreated}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <ToastProvider>
        <MainAppContent />
      </ToastProvider>
    </AuthProvider>
  );
};

export default App;
