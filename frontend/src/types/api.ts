/**
 * Auto-generated Recruit Lens API TypeScript Definitions
 * Generated from FastAPI OpenAPI schema.
 */

export type CandidateTier = "FastTrack" | "Review" | "Hold" | "Reject" | "Abstain";
export type RecruiterDecision = "pending" | "shortlisted" | "interviewed" | "held" | "rejected" | "hired";
export type EvaluationStage = "screened" | "shortlisted" | "interview_scheduled" | "interviewed" | "offer_extended" | "hired" | "rejected" | "held";

/** Audit log event entry. */
export interface AuditLogResponse {
  id: string;
  user_id: string | any;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, any>;
  created_at: string;
}

/** Asynchronous background task progress summary. */
export interface BackgroundTaskResponse {
  id: string;
  task_type: string;
  status: string;
  progress: number;
  total: number;
  error_message: string | any;
  result: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Body_upload_resumes_api_v1_resumes_upload__job_id__post {
  files: string[];
}

/** Echo payload for input validation testing. */
export interface EchoPayload {
  message: string;
}

/** Email record representation. */
export interface EmailDraftResponse {
  id: string;
  evaluation_id: string;
  email_type: string;
  recipient_email: string;
  subject: string;
  body: string;
  status: string;
  sent_at: string | any;
  error_message: string | any;
  created_at: string;
}

/** Result of sending an email. */
export interface EmailSendResponse {
  id: string;
  status: string;
  dry_run: boolean;
  sent_at: string;
  message: string;
}

/** Recruiter edit to an email draft. */
export interface EmailUpdateRequest {
  subject?: string | any;
  body?: string | any;
}

/** Comprehensive candidate dossier with scores, breakdown, explanation, questions, drafts. */
export interface EvaluationDetailResponse {
  id: string;
  user_id: string;
  job_id: string;
  resume_id: string;
  candidate_filename: string;
  total_score: number;
  tier: string;
  confidence: number;
  stage: string;
  breakdown: Record<string, any>;
  explanation: Record<string, any>;
  explanation_type: string;
  interview_questions: Record<string, any>;
  email_drafts: Record<string, any>;
  evidence_hash: string;
  llm_generated: boolean;
  created_at: string;
  updated_at: string;
}

/** Compact candidate evaluation row for ranking table and drag-and-drop board. */
export interface EvaluationSummaryResponse {
  id: string;
  resume_id: string;
  job_id: string;
  candidate_filename: string;
  total_score: number;
  tier: string;
  confidence: number;
  stage: string;
  explanation_type: string;
  llm_generated: boolean;
  created_at: string;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

/** Post-interview structured scorecard submission. */
export interface InterviewFeedbackCreate {
  interviewer_name: string;
  overall_score: number;
  technical_rating?: number;
  communication_rating?: number;
  recommendation: "hire" | "no_hire" | "strong_hire" | "mixed";
  strengths?: string;
  concerns?: string;
  notes?: string;
}

/** Structured interview scorecard response. */
export interface InterviewFeedbackResponse {
  id: string;
  evaluation_id: string;
  interviewer_name: string;
  overall_score: number;
  technical_rating: number;
  communication_rating: number;
  recommendation: string;
  strengths: string;
  concerns: string;
  notes: string;
  created_at: string;
}

/** Job requisition creation payload. */
export interface JobCreateRequest {
  title: string;
  department?: string;
  raw_text: string;
  weights?: Record<string, any> | any;
}

/** Job requisition response representation. */
export interface JobResponse {
  id: string;
  user_id: string;
  title: string;
  department: string;
  raw_text: string;
  requirements_json: Record<string, any>;
  weights_json: Record<string, any>;
  status: string;
  created_at: string;
  updated_at: string;
}

/** Job requisition update payload. */
export interface JobUpdateRequest {
  title?: string | any;
  department?: string | any;
  raw_text?: string | any;
  weights?: Record<string, any> | any;
  status?: string | any;
}

/** Refresh token request payload. */
export interface RefreshTokenRequest {
  refresh_token: string;
}

/** Uploaded candidate resume representation. */
export interface ResumeResponse {
  id: string;
  job_id: string;
  filename: string;
  file_hash: string;
  status: string;
  storage_backend: string;
  signed_url?: string | any;
  created_at: string;
}

/** Candidate stage workflow transition according to state machine. */
export interface StageTransitionRequest {
  to_stage: string;
  notes?: string;
}

/** Stage transition confirmation response. */
export interface StageTransitionResponse {
  id: string;
  evaluation_id: string;
  from_stage: string;
  to_stage: string;
  notes: string;
  audit_log_id: string;
  updated_at: string;
}

/** JWT access and refresh token pair. */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in_seconds: number;
}

/** User login request payload. */
export interface UserLoginRequest {
  email: string;
  password: string;
}

/** Authenticated user profile representation. */
export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  daily_token_usage: number;
  created_at: string;
}

export interface ValidationError {
  loc: string | number[];
  msg: string;
  type: string;
  input?: any;
  ctx?: Record<string, any>;
}

/** What-if sensitivity simulation request. */
export interface WhatIfRequest {
  weights?: Record<string, any> | any;
  min_years_experience?: number | any;
}

/** What-if calculation result without mutating database. */
export interface WhatIfResponse {
  original_score: number;
  new_score: number;
  original_tier: string;
  new_tier: string;
  score_delta: number;
  breakdown: Record<string, any>;
}
