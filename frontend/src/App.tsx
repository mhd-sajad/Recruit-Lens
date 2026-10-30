import React, { useState, useEffect, useMemo } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ToastProvider, useToast } from "./components/common/Toast";
import { Sidebar } from "./components/layout/Sidebar";
import { TopBar } from "./components/layout/TopBar";

// Screens
import { HomeScreen } from "./components/screens/HomeScreen";
import { HowItWorksScreen } from "./components/screens/HowItWorksScreen";
import { LoginScreen } from "./components/screens/LoginScreen";
import { RequisitionsScreen } from "./components/screens/RequisitionsScreen";
import { CreateRequisitionScreen } from "./components/screens/CreateRequisitionScreen";
import { DashboardScreen } from "./components/screens/DashboardScreen";
import { RankedTableScreen } from "./components/screens/RankedTableScreen";
import { AddCandidatesScreen } from "./components/screens/AddCandidatesScreen";
import { CandidateDossierScreen } from "./components/screens/CandidateDossierScreen";
import { PipelineBoardScreen } from "./components/screens/PipelineBoardScreen";
import { EmailCenterScreen } from "./components/screens/EmailCenterScreen";
import { AuditLogScreen } from "./components/screens/AuditLogScreen";
import { SettingsScreen } from "./components/screens/SettingsScreen";
import { NotFoundScreen, SessionExpiredScreen } from "./components/screens/ErrorScreens";

// Router & Utilities
import {
  useRouter,
  isProtectedRoute,
  hasSidebar,
} from "./lib/router";
import { api } from "./lib/api";
import { jobResponseToJobItem, evaluationSummaryToCandidateItem } from "./lib/transformers";

// Initial & Mock Data
import {
  INITIAL_JOBS,
  ALL_MOCK_CANDIDATES,
  SAMPLE_DOSSIER_6299,
  type JobItem,
  type CandidateItem,
  type CandidateDossier,
} from "./lib/mockData";

interface MainAppContentProps {
  initialPath?: string;
}

const MainAppContent: React.FC<MainAppContentProps> = ({ initialPath }) => {
  const { currentRoute, navigate } = useRouter();
  const { isAuthenticated, isLoading, jobs, activeJob, setActiveJob } = useAuth();
  const { showToast } = useToast();

  // If initialPath prop was provided, navigate there once
  useEffect(() => {
    if (initialPath && typeof window !== "undefined" && window.location.pathname !== initialPath) {
      navigate(initialPath, true);
    }
  }, [initialPath, navigate]);

  // Jobs state
  const [jobsList, setJobsList] = useState<JobItem[]>(INITIAL_JOBS);
  // Candidates state
  const [candidatesList, setCandidatesList] = useState<CandidateItem[]>(ALL_MOCK_CANDIDATES);
  // Active Dossier
  const [dossier, setDossier] = useState<CandidateDossier>(SAMPLE_DOSSIER_6299);

  // Sync backend jobs into jobsList
  useEffect(() => {
    if (jobs && jobs.length > 0) {
      const converted = jobs.map((j) => jobResponseToJobItem(j));
      const convertedIds = new Set(converted.map((c) => c.id));
      const remainingInitial = INITIAL_JOBS.filter((j) => !convertedIds.has(j.id));
      setJobsList([...converted, ...remainingInitial]);
    }
  }, [jobs]);

  // Determine active job from route or default
  const activeJobIdFromRoute =
    "jobId" in currentRoute ? (currentRoute as { jobId: string }).jobId : null;

  const currentActiveJob = useMemo(() => {
    if (activeJobIdFromRoute) {
      return jobsList.find((j) => j.id === activeJobIdFromRoute) || null;
    }
    if (activeJob) {
      return jobsList.find((j) => j.id === activeJob.id) || jobsList[0] || null;
    }
    return jobsList[0] || null;
  }, [activeJobIdFromRoute, activeJob, jobsList]);

  // Keep backend activeJob in sync when currentActiveJob changes
  useEffect(() => {
    if (currentActiveJob && jobs && jobs.length > 0 && setActiveJob) {
      const match = jobs.find((j) => j.id === currentActiveJob.id);
      if (match && activeJob?.id !== match.id) {
        setActiveJob(match);
      }
    }
  }, [currentActiveJob, jobs, activeJob, setActiveJob]);

  // Fetch real evaluations when active job changes, polling every 3s to reflect background ingestion
  useEffect(() => {
    if (!currentActiveJob) return;
    let isCancelled = false;

    const fetchCandidates = () => {
      api
        .getCandidates(currentActiveJob.id)
        .then((evals) => {
          if (!isCancelled && Array.isArray(evals) && evals.length > 0) {
            const transformed = evals.map((e, idx) => {
              const item = evaluationSummaryToCandidateItem(e, idx);
              return { ...item, job_id: currentActiveJob.id };
            });
            setCandidatesList((prev) => {
              const other = prev.filter((c) => (c.job_id || "job-backend") !== currentActiveJob.id);
              return [...transformed, ...other];
            });
          }
        })
        .catch(() => {});
    };

    fetchCandidates();
    const pollTimer = setInterval(fetchCandidates, 3000);

    return () => {
      isCancelled = true;
      clearInterval(pollTimer);
    };
  }, [currentActiveJob]);

  // Handle protected route access while not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated && isProtectedRoute(currentRoute)) {
      const currentPath = typeof window !== "undefined" ? window.location.pathname : "/requisitions";
      navigate(`/login?redirect=${encodeURIComponent(currentPath)}`, true);
    }
  }, [isLoading, isAuthenticated, currentRoute, navigate]);

  // Handle authenticated user accessing /login -> redirect to /requisitions
  useEffect(() => {
    if (!isLoading && isAuthenticated && currentRoute.name === "login") {
      const target = currentRoute.redirectAfter || "/requisitions";
      navigate(target, true);
    }
  }, [isLoading, isAuthenticated, currentRoute, navigate]);

  // Dossier opener helper
  const handleOpenDossier = (candId: string, jobId: string) => {
    const cand = candidatesList.find(
      (c) => (c.id === candId || c.code === candId) && (c.job_id || "job-backend") === jobId
    );
    if (cand) {
      setDossier({
        ...SAMPLE_DOSSIER_6299,
        candidate: cand,
      });

      api
        .getCandidateDetail(candId)
        .then((detail) => {
          if (detail && detail.id && detail.breakdown) {
            const contributions = Object.entries(detail.breakdown).map(([k, val]) => {
              const v = val as { score?: number; weight?: number } | undefined;
              return {
                feature: k.charAt(0).toUpperCase() + k.slice(1) + " Assessment",
                delta: Math.round((v?.score ?? 0.8) * (v?.weight ?? 0.25) * 100),
                description: `Evidence-backed model component (${Math.round((v?.score ?? 0.8) * 100)}% fit score)`,
              };
            });
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
    navigate(`/jobs/${jobId}/candidates/${candId}`);
  };

  // Pipeline stage update helper
  const handleUpdateCandidateStage = (candId: string, newStage: CandidateItem["stage"]) => {
    setCandidatesList((prev) =>
      prev.map((c) => (c.id === candId ? { ...c, stage: newStage } : c))
    );
    showToast(`Candidate stage moved to ${newStage}`, "info");
  };

  // Loading Screen
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-canvas)] text-xs text-[var(--text-secondary)] font-mono">
        <span className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mr-2" />
        Initializing Recruit Lens...
      </div>
    );
  }

  // PUBLIC SCREEN 1: Home Page ("/")
  if (currentRoute.name === "home") {
    return <HomeScreen onNavigate={navigate} />;
  }

  // PUBLIC SCREEN 2: How It Works ("/how-it-works")
  if (currentRoute.name === "how-it-works") {
    return <HowItWorksScreen onNavigate={navigate} />;
  }

  // PUBLIC SCREEN 3: Login & Sign Up ("/login")
  if (currentRoute.name === "login") {
    return (
      <LoginScreen
        initialTab={currentRoute.initialTab}
        redirectAfter={currentRoute.redirectAfter}
        onNavigateHome={() => navigate("/")}
        onLoginSuccess={(target) => navigate(target)}
      />
    );
  }

  // ERROR SCREEN: Session Expired ("/session-expired")
  if (currentRoute.name === "session-expired") {
    return (
      <SessionExpiredScreen
        returnTo={currentRoute.returnTo}
        onLoginAgain={(ret) => {
          const qs = ret ? `?redirect=${encodeURIComponent(ret)}` : "";
          navigate(`/login${qs}`);
        }}
      />
    );
  }

  // If user is not authenticated and trying to view protected content,
  // the redirect effect will handle it, but render login as fallback
  if (!isAuthenticated) {
    return (
      <LoginScreen
        initialTab="login"
        redirectAfter={typeof window !== "undefined" ? window.location.pathname : undefined}
        onNavigateHome={() => navigate("/")}
        onLoginSuccess={(target) => navigate(target)}
      />
    );
  }

  // For job-scoped routes, verify that the job exists
  if (activeJobIdFromRoute && !currentActiveJob) {
    return (
      <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)]">
        <Sidebar
          currentRoute={currentRoute}
          jobsList={jobsList}
          selectedJob={null}
          candidatesList={candidatesList}
          onNavigate={navigate}
        />
        <div className="flex-1 overflow-y-auto">
          <TopBar
            currentRoute={currentRoute}
            activeJob={null}
            onNavigate={navigate}
          />
          <main className="p-6 max-w-6xl mx-auto">
            <NotFoundScreen
              message={`Requisition "${activeJobIdFromRoute}" could not be found.`}
              onHome={() => navigate("/")}
              onRequisitions={() => navigate("/requisitions")}
            />
          </main>
        </div>
      </div>
    );
  }

  // Candidate validation for dossier and email routes:
  // Must exist AND belong to the specified jobId
  if (
    currentRoute.name === "job-candidate-dossier" ||
    currentRoute.name === "job-candidate-email"
  ) {
    const candidateId = currentRoute.candidateId;
    const cand = candidatesList.find(
      (c) =>
        (c.id === candidateId || c.code === candidateId) &&
        (c.job_id || "job-backend") === currentRoute.jobId
    );

    if (!cand) {
      return (
        <div className="flex h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)]">
          <Sidebar
            currentRoute={currentRoute}
            jobsList={jobsList}
            selectedJob={currentActiveJob}
            candidatesList={candidatesList}
            onNavigate={navigate}
          />
          <div className="flex-1 overflow-y-auto">
            <TopBar
              currentRoute={currentRoute}
              activeJob={currentActiveJob}
              onNavigate={navigate}
            />
            <main className="p-6 max-w-6xl mx-auto">
              <NotFoundScreen
                message={`Candidate "${candidateId}" does not exist in requisition "${currentActiveJob?.title || currentRoute.jobId}". Candidates from other requisitions cannot be accessed here.`}
                onHome={() => navigate("/")}
                onRequisitions={() => navigate("/requisitions")}
              />
            </main>
          </div>
        </div>
      );
    }
  }

  // Render Protected Application Layout with Sidebar & TopBar
  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-canvas)] text-[var(--text-primary)] font-sans transition-colors">
      {/* Contextual Left Sidebar */}
      {hasSidebar(currentRoute, isAuthenticated) && (
        <Sidebar
          currentRoute={currentRoute}
          jobsList={jobsList}
          selectedJob={currentActiveJob}
          candidatesList={candidatesList}
          onNavigate={navigate}
        />
      )}

      {/* Main Content Area with TopBar */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar
          currentRoute={currentRoute}
          activeJob={currentActiveJob}
          onNavigate={navigate}
        />

        <main className="flex-1 overflow-y-auto p-6 max-w-7xl w-full mx-auto">
          {/* /requisitions */}
          {currentRoute.name === "requisitions" && (
            <RequisitionsScreen
              jobs={jobsList}
              onSelectJob={(job) => navigate(`/jobs/${job.id}`)}
              onCreateJob={() => navigate("/requisitions/new")}
            />
          )}

          {/* /requisitions/new */}
          {currentRoute.name === "requisitions-new" && (
            <CreateRequisitionScreen
              initialStep={currentRoute.step}
              onNavigate={navigate}
              onJobCreated={(newJob) => {
                setJobsList((prev) => [newJob, ...prev]);
                showToast(`Requisition "${newJob.title}" created successfully!`, "success");
              }}
            />
          )}

          {/* /jobs/:jobId */}
          {currentRoute.name === "job-dashboard" && currentActiveJob && (
            <DashboardScreen
              job={currentActiveJob}
              candidates={candidatesList}
              onNavigate={navigate}
            />
          )}

          {/* /jobs/:jobId/candidates */}
          {currentRoute.name === "job-candidates" && currentActiveJob && (
            <RankedTableScreen
              job={currentActiveJob}
              candidates={candidatesList.filter(
                (c) => (c.job_id || "job-backend") === currentActiveJob.id
              )}
              onSelectCandidate={(candId) => handleOpenDossier(candId, currentActiveJob.id)}
              onOpenEmail={(candId) => navigate(`/jobs/${currentActiveJob.id}/candidates/${candId}/email`)}
              onExportAudit={() => navigate(`/jobs/${currentActiveJob.id}/audit`)}
              onNavigateRequisitions={() => navigate("/requisitions")}
            />
          )}

          {/* /jobs/:jobId/candidates/add */}
          {currentRoute.name === "job-candidates-add" && currentActiveJob && (
            <AddCandidatesScreen
              job={currentActiveJob}
              onNavigate={navigate}
              onUploadSuccess={() => {
                showToast("Candidate resumes successfully indexed.", "success");
              }}
            />
          )}

          {/* /jobs/:jobId/candidates/:candidateId */}
          {currentRoute.name === "job-candidate-dossier" && currentActiveJob && (
            <CandidateDossierScreen
              dossier={dossier}
              candidatesList={candidatesList.filter(
                (c) => (c.job_id || "job-backend") === currentActiveJob.id
              )}
              onBack={() => navigate(`/jobs/${currentActiveJob.id}/candidates`)}
              onNextCandidate={(nextId) => handleOpenDossier(nextId, currentActiveJob.id)}
              onOpenEmail={(candId) =>
                navigate(`/jobs/${currentActiveJob.id}/candidates/${candId}/email`)
              }
            />
          )}

          {/* /jobs/:jobId/candidates/:candidateId/email */}
          {currentRoute.name === "job-candidate-email" && (
            <EmailCenterScreen
              initialCandidateCode={currentRoute.candidateId}
              onSendSuccess={() => {
                showToast("Email dispatched and logged with cryptographic hash.", "success");
              }}
            />
          )}

          {/* /jobs/:jobId/pipeline */}
          {currentRoute.name === "job-pipeline" && currentActiveJob && (
            <PipelineBoardScreen
              candidates={candidatesList.filter(
                (c) => (c.job_id || "job-backend") === currentActiveJob.id
              )}
              onSelectCandidate={(candId) => handleOpenDossier(candId, currentActiveJob.id)}
              onUpdateCandidateStage={handleUpdateCandidateStage}
            />
          )}

          {/* /jobs/:jobId/audit */}
          {currentRoute.name === "job-audit" && currentActiveJob && (
            <AuditLogScreen jobId={currentActiveJob.id} jobTitle={currentActiveJob.title} />
          )}

          {/* /audit (Global across all jobs) */}
          {currentRoute.name === "audit" && <AuditLogScreen />}

          {/* /settings */}
          {currentRoute.name === "settings" && <SettingsScreen />}

          {/* 404 Not Found for unknown routes */}
          {currentRoute.name === "not-found" && (
            <NotFoundScreen
              path={currentRoute.path}
              onHome={() => navigate("/")}
              onRequisitions={() => navigate("/requisitions")}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export const App: React.FC<{ initialPath?: string }> = ({ initialPath }) => {
  return (
    <AuthProvider>
      <ToastProvider>
        <MainAppContent initialPath={initialPath} />
      </ToastProvider>
    </AuthProvider>
  );
};

export default App;
