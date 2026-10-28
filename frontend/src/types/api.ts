/**
 * Recruit Lens API TypeScript Definitions
 * Strictly mirrors backend schemas (Pydantic models and SQLAlchemy domain entities).
 */

export type CandidateTier = "FastTrack" | "Review" | "Hold" | "Reject" | "Abstain";

export type RecruiterDecision = "pending" | "shortlisted" | "interviewed" | "held" | "rejected" | "hired";

export type TaskStatus = "pending" | "processing" | "completed" | "failed";

export type UserRole = "admin" | "recruiter" | "viewer";

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
}

export interface JobRequirements {
  title?: string;
  min_years_experience: number;
  min_education_level: number;
  min_education_name?: string;
  required_must_skills: string[];
  required_nice_skills: string[];
  domains: string[];
  raw_text?: string;
}

export interface Job {
  id: string;
  tenant_id: string;
  title: string;
  department: string;
  raw_text: string;
  requirements_json: JobRequirements;
  weights_json: Record<string, number>;
  status: "draft" | "active" | "archived";
  created_at: string;
  updated_at: string;
}

export interface JobCreateRequest {
  title: string;
  department?: string;
  raw_text: string;
  weights?: Record<string, number>;
}

export interface JobUpdateRequest {
  title?: string;
  department?: string;
  raw_text?: string;
  weights?: Record<string, number>;
  status?: "draft" | "active" | "archived";
}

export interface Resume {
  id: string;
  tenant_id: string;
  job_id: string;
  filename: string;
  file_hash: string;
  status: "pending" | "processed" | "error";
  created_at: string;
}

export interface ScoreComponentBreakdown {
  score: number;
  weight: number;
  weighted: number;
  status: "met" | "partial" | "missing" | "unspecified";
  details?: Record<string, unknown>;
}

export interface EvaluationBreakdown {
  skills: ScoreComponentBreakdown & {
    matched_must_skills: string[];
    missing_must_skills: string[];
    matched_nice_skills: string[];
    missing_nice_skills: string[];
  };
  experience: ScoreComponentBreakdown & {
    candidate_years: number;
    required_years: number;
  };
  education: ScoreComponentBreakdown & {
    candidate_degree: string;
    required_degree: string;
  };
  semantic: ScoreComponentBreakdown;
  penalties: {
    applied: string[];
    multiplier: number;
  };
}

export interface CandidateExplanation {
  sentences: string[];
  evidence_citations: string[][];
  overall_summary: string;
  strengths: string[];
  concerns: string[];
  recommendation: string;
}

export interface InterviewQuestionItem {
  question: string;
  target_skill_or_gap: string;
  expected_signal: string;
  evidence_source_chunk: string;
}

export interface InterviewQuestions {
  questions: InterviewQuestionItem[];
}

export interface EmailDrafts {
  interview_invitation: {
    subject: string;
    body: string;
  };
  rejection: {
    subject: string;
    body: string;
  };
  hold_update: {
    subject: string;
    body: string;
  };
}

export interface EvaluationSummary {
  id: string;
  resume_id: string;
  job_id: string;
  candidate_filename: string;
  total_score: number;
  tier: CandidateTier;
  confidence: number;
  decision: RecruiterDecision;
  llm_generated: boolean;
  created_at: string;
}

export interface EvaluationDetail {
  id: string;
  tenant_id: string;
  job_id: string;
  resume_id: string;
  candidate_filename: string;
  total_score: number;
  tier: CandidateTier;
  confidence: number;
  decision: RecruiterDecision;
  decision_notes: string;
  breakdown: EvaluationBreakdown;
  explanation: CandidateExplanation;
  interview_questions: InterviewQuestions;
  email_drafts: EmailDrafts;
  evidence_hash: string;
  llm_generated: boolean;
  created_at: string;
  updated_at: string;
}

export interface CandidateDecisionRequest {
  decision: "shortlisted" | "interviewed" | "held" | "rejected" | "hired";
  decision_notes?: string;
}

export interface CandidateDecisionResponse {
  id: string;
  evaluation_id: string;
  decision: RecruiterDecision;
  decision_notes: string;
  audit_log_id: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  tenant_id: string;
  user_id: string | null;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface BackgroundTask {
  id: string;
  task_type: string;
  status: TaskStatus;
  progress: number;
  total: number;
  error_message: string | null;
  result: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
