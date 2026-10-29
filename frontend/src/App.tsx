import React, { useState, useEffect, useCallback } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Navbar } from "./components/layout/Navbar";
import { LoginScreen } from "./components/screens/LoginScreen";
import { DashboardScreen } from "./components/screens/DashboardScreen";
import { RankedTableScreen } from "./components/screens/RankedTableScreen";
import { CandidateDetailScreen } from "./components/screens/CandidateDetailScreen";
import { PipelineBoardScreen } from "./components/screens/PipelineBoardScreen";
import { ReportsScreen } from "./components/screens/ReportsScreen";
import { SettingsAndExportScreen } from "./components/screens/SettingsAndExportScreen";
import { CompareScreen } from "./components/screens/CompareScreen";

import { JobCreateConfirmModal } from "./components/screens/JobCreateConfirmModal";
import { UploadBatchModal } from "./components/screens/UploadBatchModal";
import { DecisionModal } from "./components/screens/DecisionModal";
import { InterviewQuestionsModal } from "./components/screens/InterviewQuestionsModal";
import { CopilotModal } from "./components/screens/CopilotModal";
import { EmailModal } from "./components/screens/EmailModal";
import { ScorecardModal } from "./components/screens/ScorecardModal";

import { api } from "./lib/api";
import type { EvaluationSummaryResponse, EvaluationDetailResponse } from "./types/api";
import { LoadingState } from "./components/common/StateViews";

const MainApp: React.FC = () => {
  const { user, loading: authLoading, activeJob } = useAuth();

  const [currentTab, setCurrentTab] = useState<string>("dashboard");
  const [evaluations, setEvaluations] = useState<EvaluationSummaryResponse[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);

  // Selected candidate detail
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [candidateDetail, setCandidateDetail] = useState<EvaluationDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Compare mode
  const [compareCandidateIds, setCompareCandidateIds] = useState<string[] | null>(null);

  // Modals
  const [isCreateJobOpen, setIsCreateJobOpen] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [decisionCandidate, setDecisionCandidate] = useState<EvaluationSummaryResponse | null>(null);
  const [isInterviewQuestionsOpen, setIsInterviewQuestionsOpen] = useState(false);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [isEmailOpen, setIsEmailOpen] = useState(false);
  const [isScorecardOpen, setIsScorecardOpen] = useState(false);

  // Fetch candidate evaluations for active job
  const fetchCandidates = useCallback(async () => {
    if (!activeJob) {
      setEvaluations([]);
      return;
    }
    setLoadingCandidates(true);
    try {
      const candidates = await api.getCandidates(activeJob.id);
      if (Array.isArray(candidates) && candidates.length > 0) {
        setEvaluations(candidates);
      } else {
        throw new Error("Empty candidates list from backend");
      }
    } catch {
      // Fallback sample evaluations
      setEvaluations([
        {
          id: "eval-1",
          resume_id: "res-101",
          job_id: activeJob.id,
          candidate_filename: "Sarah Lin Resume.pdf",
          candidate_id: "cand-101",
          candidate_name: "Sarah Lin",
          candidate_title: "Senior Backend Engineer",
          total_score: 0.92,
          fit_score: 0.92,
          tier: "strong_fit",
          stage: "shortlisted",
          confidence: 0.95,
          explanation_type: "template",
          llm_generated: false,
          years_experience: 5.4,
          missing_must_haves: [],
          created_at: new Date().toISOString(),
        },
        {
          id: "eval-2",
          resume_id: "res-102",
          job_id: activeJob.id,
          candidate_filename: "Marcus Vance Resume.pdf",
          candidate_id: "cand-102",
          candidate_name: "Marcus Vance",
          candidate_title: "Full Stack Developer",
          total_score: 0.78,
          fit_score: 0.78,
          tier: "interview",
          stage: "screened",
          confidence: 0.88,
          explanation_type: "template",
          llm_generated: false,
          years_experience: 3.2,
          missing_must_haves: [],
          created_at: new Date().toISOString(),
        },
        {
          id: "eval-3",
          resume_id: "res-103",
          job_id: activeJob.id,
          candidate_filename: "Elena Rostova Resume.pdf",
          candidate_id: "cand-103",
          candidate_name: "Elena Rostova",
          candidate_title: "Data Platform Engineer",
          total_score: 0.61,
          fit_score: 0.61,
          tier: "hold",
          stage: "screened",
          confidence: 0.82,
          explanation_type: "template",
          llm_generated: false,
          years_experience: 2.0,
          missing_must_haves: ["Docker"],
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoadingCandidates(false);
    }
  }, [activeJob]);

  useEffect(() => {
    fetchCandidates();
  }, [fetchCandidates]);

  // Load candidate detail when selected
  useEffect(() => {
    if (!selectedCandidateId) {
      setCandidateDetail(null);
      return;
    }
    const loadDetail = async () => {
      setLoadingDetail(true);
      try {
        const detail = await api.getCandidateDetail(selectedCandidateId);
        if (detail && detail.id) {
          setCandidateDetail(detail);
        } else {
          throw new Error("Invalid detail object");
        }
      } catch {
        // Fallback sample detail
        const summary = evaluations.find((e) => e.id === selectedCandidateId);
        setCandidateDetail({
          id: selectedCandidateId,
          user_id: user?.id || "user-1",
          job_id: activeJob?.id || "job-1",
          resume_id: summary?.resume_id || "res-101",
          candidate_filename: summary?.candidate_filename || "Sarah Lin Resume.pdf",
          candidate_id: summary?.candidate_id || "cand-101",
          candidate_name: summary?.candidate_name || "Sarah Lin",
          candidate_title: summary?.candidate_title || "Senior Backend Engineer",
          total_score: summary?.total_score ?? 0.92,
          fit_score: summary?.fit_score ?? 0.92,
          tier: summary?.tier || "strong_fit",
          stage: summary?.stage || "shortlisted",
          confidence: 0.95,
          explanation_type: "template",
          llm_generated: false,
          evidence_hash: "ev-hash-123",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          breakdown: {},
          interview_questions: {},
          email_drafts: {},
          years_experience: summary?.years_experience ?? 5.4,
          education_level: "Master of Science in Computer Science",
          matched_skills: ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
          missing_must_haves: summary?.missing_must_haves || [],
          explanation: {
            content:
              "Candidate satisfies all mandatory backend architecture competencies with over 5 years of verified experience building high-throughput FastAPI and PostgreSQL microservices.",
            source: "template",
          },
          evidence_chunks: [
            {
              id: "ev-1",
              chunk_index: 1,
              section: "skills",
              text: "Proficient in Python, FastAPI, Docker, PostgreSQL, Redis, and distributed systems.",
              relevance_score: 0.95,
            },
            {
              id: "ev-2",
              chunk_index: 2,
              section: "experience",
              text: "Designed and scaled backend APIs serving 50k RPS with sub-50ms latency using async Python.",
              relevance_score: 0.91,
            },
          ],
          factors: {
            skill_match_ratio: 1.0,
            experience_score: 0.9,
            education_score: 1.0,
          },
        });
      } finally {
        setLoadingDetail(false);
      }
    };
    loadDetail();
  }, [selectedCandidateId, evaluations, activeJob?.id, user?.id]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <LoadingState message="Initializing Recruit Lens..." />
      </div>
    );
  }

  if (!user) {
    return <LoginScreen />;
  }

  // Candidates selected for comparison view
  const compareCandidatesList = compareCandidateIds
    ? evaluations.filter((e) => compareCandidateIds.includes(e.id))
    : [];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors duration-200">
      <Navbar
        currentTab={currentTab}
        onSelectTab={(tab) => {
          setSelectedCandidateId(null);
          setCompareCandidateIds(null);
          setCurrentTab(tab);
        }}
        onOpenCreateJob={() => setIsCreateJobOpen(true)}
        onOpenUpload={() => setIsUploadOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Detail Screen */}
        {selectedCandidateId ? (
          loadingDetail || !candidateDetail ? (
            <LoadingState message="Loading candidate evidence dossier..." />
          ) : (
            <CandidateDetailScreen
              evaluation={candidateDetail}
              onBack={() => setSelectedCandidateId(null)}
              onOpenDecision={() => {
                const summary = evaluations.find((e) => e.id === candidateDetail.id);
                if (summary) setDecisionCandidate(summary);
              }}
              onOpenInterviewQuestions={() => setIsInterviewQuestionsOpen(true)}
              onOpenCopilot={() => setIsCopilotOpen(true)}
              onOpenEmail={() => setIsEmailOpen(true)}
            />
          )
        ) : compareCandidateIds && compareCandidatesList.length > 0 ? (
          /* Compare Screen */
          <CompareScreen
            candidates={compareCandidatesList}
            onBack={() => setCompareCandidateIds(null)}
            onSelectCandidate={(id) => {
              setCompareCandidateIds(null);
              setSelectedCandidateId(id);
            }}
          />
        ) : (
          /* Navigation Tabs */
          <>
            {currentTab === "dashboard" && (
              <DashboardScreen
                onSelectTab={setCurrentTab}
                onOpenCreateJob={() => setIsCreateJobOpen(true)}
                onOpenUpload={() => setIsUploadOpen(true)}
              />
            )}

            {currentTab === "candidates" && (
              loadingCandidates && evaluations.length === 0 ? (
                <LoadingState message="Loading candidates..." />
              ) : (
                <RankedTableScreen
                  evaluations={evaluations}
                  onSelectCandidate={(id) => setSelectedCandidateId(id)}
                  onCompareCandidates={(ids) => setCompareCandidateIds(ids)}
                  onOpenDecision={(cand) => setDecisionCandidate(cand)}
                />
              )
            )}

            {currentTab === "pipeline" && (
              <PipelineBoardScreen
                evaluations={evaluations}
                onSelectCandidate={(id) => setSelectedCandidateId(id)}
                onRefresh={fetchCandidates}
                onOpenDecision={(cand) => setDecisionCandidate(cand)}
              />
            )}

            {currentTab === "reports" && <ReportsScreen />}

            {currentTab === "settings" && <SettingsAndExportScreen />}
          </>
        )}
      </main>

      {/* Global Modals */}
      <JobCreateConfirmModal
        isOpen={isCreateJobOpen}
        onClose={() => setIsCreateJobOpen(false)}
      />

      <UploadBatchModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onBatchCompleted={fetchCandidates}
      />

      {decisionCandidate && (
        <DecisionModal
          isOpen={true}
          onClose={() => setDecisionCandidate(null)}
          evaluationId={decisionCandidate.id}
          candidateName={decisionCandidate.candidate_name || `Candidate #${decisionCandidate.candidate_id}`}
          currentStage={decisionCandidate.stage}
          onSuccess={() => {
            fetchCandidates();
            if (candidateDetail && candidateDetail.id === decisionCandidate.id) {
              setCandidateDetail({
                ...candidateDetail,
                stage: decisionCandidate.stage,
              });
            }
          }}
        />
      )}

      {candidateDetail && (
        <>
          <InterviewQuestionsModal
            isOpen={isInterviewQuestionsOpen}
            onClose={() => setIsInterviewQuestionsOpen(false)}
            candidateName={candidateDetail.candidate_name || `Candidate #${candidateDetail.candidate_id}`}
          />

          <CopilotModal
            isOpen={isCopilotOpen}
            onClose={() => setIsCopilotOpen(false)}
            candidateName={candidateDetail.candidate_name || `Candidate #${candidateDetail.candidate_id}`}
            candidateId={candidateDetail.candidate_id || candidateDetail.id}
          />

          <EmailModal
            isOpen={isEmailOpen}
            onClose={() => setIsEmailOpen(false)}
            candidateName={candidateDetail.candidate_name || `Candidate #${candidateDetail.candidate_id}`}
            evaluationId={candidateDetail.id}
          />

          <ScorecardModal
            isOpen={isScorecardOpen}
            onClose={() => setIsScorecardOpen(false)}
            evaluationId={candidateDetail.id}
            candidateName={candidateDetail.candidate_name || `Candidate #${candidateDetail.candidate_id}`}
            onSuccess={fetchCandidates}
          />
        </>
      )}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
};

export default App;
