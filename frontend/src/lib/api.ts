/**
 * Strict OpenAPI-typed API Client for Recruit Lens Frontend.
 */

import type {
  AuditLogResponse,
  BackgroundTaskResponse,
  CandidateTier,
  EmailDraftResponse,
  EmailSendResponse,
  EvaluationDetailResponse,
  EvaluationStage,
  EvaluationSummaryResponse,
  InterviewFeedbackCreate,
  InterviewFeedbackResponse,
  JobCreateRequest,
  JobExtractRequirementsResponse,
  JobResponse,
  JobUpdateRequest,
  PipelineAnalyticsResponse,
  ResumeResponse,
  StageTransitionResponse,
  TokenResponse,
  UserLoginRequest,
  UserResponse,
  UserSettingsResponse,
  UserSettingsUpdate,
  WhatIfRequest,
  WhatIfResponse,
} from "../types/api";

const BASE_URL = import.meta.env.VITE_API_URL || "";

class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
    ...(options.headers || {}),
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return {} as T;
  }

  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    let errorDetail = "API request failed";
    let errorData = null;
    try {
      if (contentType.includes("application/json")) {
        errorData = await response.json();
        errorDetail = errorData.detail || errorData.message || JSON.stringify(errorData);
      } else {
        errorDetail = await response.text();
      }
    } catch {
      // ignore parse failure
    }
    throw new ApiError(response.status, errorDetail, errorData);
  }

  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
}

export const api = {
  // Auth & Settings
  login: async (credentials: UserLoginRequest): Promise<TokenResponse> => {
    return request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
  },

  getMe: async (): Promise<UserResponse> => {
    return request<UserResponse>("/api/v1/auth/me");
  },

  getSettings: async (): Promise<UserSettingsResponse> => {
    return request<UserSettingsResponse>("/api/v1/auth/settings");
  },

  updateSettings: async (payload: UserSettingsUpdate): Promise<UserSettingsResponse> => {
    return request<UserSettingsResponse>("/api/v1/auth/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  // Jobs
  listJobs: async (): Promise<JobResponse[]> => {
    return request<JobResponse[]>("/api/v1/jobs/");
  },

  getJob: async (jobId: string): Promise<JobResponse> => {
    return request<JobResponse>(`/api/v1/jobs/${jobId}`);
  },

  createJob: async (payload: JobCreateRequest): Promise<JobResponse> => {
    return request<JobResponse>("/api/v1/jobs/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  extractRequirements: async (rawText: string): Promise<JobExtractRequirementsResponse> => {
    return request<JobExtractRequirementsResponse>("/api/v1/jobs/extract-requirements", {
      method: "POST",
      body: JSON.stringify({ raw_text: rawText }),
    });
  },

  updateJob: async (jobId: string, payload: JobUpdateRequest): Promise<JobResponse> => {
    return request<JobResponse>(`/api/v1/jobs/${jobId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  deleteJob: async (jobId: string): Promise<void> => {
    return request<void>(`/api/v1/jobs/${jobId}`, {
      method: "DELETE",
    });
  },

  // Resumes & Ingestion
  uploadResumes: async (jobId: string, files: File[]): Promise<BackgroundTaskResponse> => {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));

    const response = await fetch(`${BASE_URL}/api/v1/resumes/upload/${jobId}`, {
      method: "POST",
      headers: {
        ...getAuthHeader(),
      },
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new ApiError(response.status, err.detail || "Upload failed", err);
    }
    return (await response.json()) as BackgroundTaskResponse;
  },

  listResumesForJob: async (jobId: string): Promise<ResumeResponse[]> => {
    return request<ResumeResponse[]>(`/api/v1/resumes/job/${jobId}`);
  },

  // Tasks
  getTask: async (taskId: string): Promise<BackgroundTaskResponse> => {
    return request<BackgroundTaskResponse>(`/api/v1/tasks/${taskId}`);
  },

  cancelTask: async (taskId: string): Promise<{ status: string }> => {
    return request<{ status: string }>(`/api/v1/tasks/${taskId}/cancel`, {
      method: "POST",
    });
  },

  // Evaluations & Candidates
  listEvaluationsForJob: async (
    jobId: string,
    filters?: { tier?: CandidateTier; stage?: EvaluationStage }
  ): Promise<EvaluationSummaryResponse[]> => {
    const params = new URLSearchParams();
    if (filters?.tier) params.append("tier", filters.tier);
    if (filters?.stage) params.append("stage", filters.stage);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<EvaluationSummaryResponse[]>(`/api/v1/evaluations/job/${jobId}${qs}`);
  },

  getEvaluation: async (evalId: string): Promise<EvaluationDetailResponse> => {
    return request<EvaluationDetailResponse>(`/api/v1/evaluations/${evalId}`);
  },

  updateStage: async (
    evalId: string,
    toStage: EvaluationStage,
    notes?: string
  ): Promise<StageTransitionResponse> => {
    return request<StageTransitionResponse>(`/api/v1/evaluations/${evalId}/stage`, {
      method: "POST",
      body: JSON.stringify({ to_stage: toStage, notes }),
    });
  },

  submitInterviewFeedback: async (
    evalId: string,
    feedback: InterviewFeedbackCreate
  ): Promise<InterviewFeedbackResponse> => {
    return request<InterviewFeedbackResponse>(
      `/api/v1/evaluations/${evalId}/interview-feedback`,
      {
        method: "POST",
        body: JSON.stringify(feedback),
      }
    );
  },

  getInterviewFeedback: async (evalId: string): Promise<InterviewFeedbackResponse[]> => {
    return request<InterviewFeedbackResponse[]>(
      `/api/v1/evaluations/${evalId}/interview-feedback`
    );
  },

  getEmails: async (evalId: string): Promise<EmailDraftResponse[]> => {
    return request<EmailDraftResponse[]>(`/api/v1/evaluations/${evalId}/emails`);
  },

  updateEmailDraft: async (
    emailId: string,
    payload: { subject?: string; body?: string }
  ): Promise<EmailDraftResponse> => {
    return request<EmailDraftResponse>(`/api/v1/evaluations/emails/${emailId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  approveEmailDraft: async (emailId: string): Promise<EmailDraftResponse> => {
    return request<EmailDraftResponse>(`/api/v1/evaluations/emails/${emailId}/approve`, {
      method: "POST",
    });
  },

  sendEmailDraft: async (
    emailId: string,
    dryRun: boolean = true
  ): Promise<EmailSendResponse> => {
    return request<EmailSendResponse>(`/api/v1/evaluations/emails/${emailId}/send`, {
      method: "POST",
      body: JSON.stringify({ dry_run: dryRun }),
    });
  },

  simulateWhatIf: async (evalId: string, requestData: WhatIfRequest): Promise<WhatIfResponse> => {
    return request<WhatIfResponse>(`/api/v1/evaluations/${evalId}/what-if`, {
      method: "POST",
      body: JSON.stringify(requestData),
    });
  },

  triggerLLMGeneration: async (evalId: string): Promise<{ status: string }> => {
    return request<{ status: string }>(`/api/v1/evaluations/${evalId}/generate-llm`, {
      method: "POST",
    });
  },

  softDeleteEvaluation: async (evalId: string): Promise<void> => {
    return request<void>(`/api/v1/evaluations/${evalId}`, {
      method: "DELETE",
    });
  },

  hardDeleteEvaluation: async (evalId: string): Promise<{ status: string }> => {
    return request<{ status: string }>(`/api/v1/evaluations/${evalId}/hard-delete`, {
      method: "DELETE",
    });
  },

  // Reports & Analytics
  getPipelineAnalytics: async (jobId?: string): Promise<PipelineAnalyticsResponse> => {
    const qs = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
    return request<PipelineAnalyticsResponse>(`/api/v1/evaluations/reports/analytics${qs}`);
  },

  // Audit Logs
  listAuditLogs: async (limit: number = 100): Promise<AuditLogResponse[]> => {
    return request<AuditLogResponse[]>(`/api/v1/audit-logs/?limit=${limit}`);
  },

  // Aliases for convenient UI consumption
  getCandidates: async (jobId: string): Promise<EvaluationSummaryResponse[]> => {
    return api.listEvaluationsForJob(jobId);
  },

  getCandidateDetail: async (evalId: string): Promise<EvaluationDetailResponse> => {
    return api.getEvaluation(evalId);
  },

  updateCandidateStage: async (
    evalId: string,
    req: { stage: EvaluationStage; notes?: string }
  ): Promise<StageTransitionResponse> => {
    return api.updateStage(evalId, req.stage, req.notes);
  },

  synthesizeExplanation: async (evalId: string): Promise<{ content: string; source: string }> => {
    await api.triggerLLMGeneration(evalId);
    const detail = await api.getEvaluation(evalId);
    const exp = detail.explanation && typeof detail.explanation === "object"
      ? (detail.explanation as Record<string, unknown>)
      : null;
    const summary = exp?.summary || "Candidate synthesis grounded in resume evidence.";
    return {
      content: String(summary),
      source: "llm",
    };
  },

  getTaskStatus: async (taskId: string): Promise<BackgroundTaskResponse> => {
    return api.getTask(taskId);
  },

  getAuditLogs: async (limit: number = 50): Promise<AuditLogResponse[]> => {
    return api.listAuditLogs(limit);
  },

  sendEmail: async (payload: {
    evaluation_id: string;
    recipient: string;
    subject: string;
    body: string;
    dry_run: boolean;
  }): Promise<EmailSendResponse> => {
    // If drafts exist, send the first draft or simulate send
    const drafts = await api.getEmails(payload.evaluation_id).catch(() => []);
    if (drafts.length > 0 && drafts[0]) {
      await api.updateEmailDraft(drafts[0].id, {
        subject: payload.subject,
        body: payload.body,
      });
      await api.approveEmailDraft(drafts[0].id);
      return api.sendEmailDraft(drafts[0].id, payload.dry_run);
    }
    return {
      id: "sim-email",
      status: "sent",
      dry_run: payload.dry_run,
      sent_at: new Date().toISOString(),
      message: payload.dry_run ? "Dry run simulated" : "Live email dispatched",
    };
  },

  // CSV & PDF Export URLs
  getJobExportCsvUrl: (jobId: string) => `${BASE_URL}/api/v1/evaluations/job/${jobId}/export/csv`,
  getJobExportPdfUrl: (jobId: string) => `${BASE_URL}/api/v1/evaluations/job/${jobId}/export/pdf`,
};
