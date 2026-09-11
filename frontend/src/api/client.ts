import type {
  CaseListResponse,
  CaseState,
  EvalCaseComparison,
  EvalReport,
  EvalVariant,
  EvaluationOverview,
  FinalComparison,
  EvalDataset,
  ShowcaseScenario,
  SystemInfo,
  SystemStatus,
  HealthResponse,
  ApprovalDecision,
} from "@/types";

// Prefer Vite proxy (/api → backend) in local dev to avoid CORS.
// Set VITE_API_URL to call the API directly when needed.
const API_BASE =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "/api" : "http://localhost:8000");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(detail, response.status);
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  systemStatus: () => request<SystemStatus>("/system/status"),

  systemInfo: () => request<SystemInfo>("/system/info"),

  listCases: (params?: {
    customer_id?: string;
    stage?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.customer_id) query.set("customer_id", params.customer_id);
    if (params?.stage) query.set("stage", params.stage);
    if (params?.limit != null) query.set("limit", String(params.limit));
    if (params?.offset != null) query.set("offset", String(params.offset));
    const qs = query.toString();
    return request<CaseListResponse>(`/cases${qs ? `?${qs}` : ""}`);
  },

  getCase: (caseId: string) => request<CaseState>(`/cases/${caseId}`),

  decideApproval: (caseId: string, decision: Exclude<ApprovalDecision, "PENDING">) =>
    request<CaseState>(`/cases/${caseId}/approval`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    }),

  executeCase: (caseId: string) =>
    request<CaseState>(`/cases/${caseId}/execute`, { method: "POST" }),

  verifyCase: (caseId: string) =>
    request<CaseState>(`/cases/${caseId}/verify`, { method: "POST" }),

  evaluationsOverview: () => request<EvaluationOverview>("/evaluations"),

  evaluationsComparison: () =>
    request<FinalComparison>("/evaluations/comparison"),

  evaluationVariant: (variant: EvalVariant) =>
    request<EvalReport>(`/evaluations/${variant}`),

  evaluationCase: (evalId: string) =>
    request<EvalCaseComparison>(`/evaluations/cases/${evalId}`),

  evaluationDataset: () => request<EvalDataset>("/evaluations/dataset"),

  showcaseScenarios: () =>
    request<ShowcaseScenario[]>("/evaluations/showcase/scenarios"),
};

export { API_BASE };
