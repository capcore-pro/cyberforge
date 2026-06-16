import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface ClientReviewCreateResult {
  token: string;
  review_url: string;
  expires_at: string;
  id: string;
}

export interface ClientReviewPublic {
  project_id: string;
  client_name: string | null;
  demo_url: string | null;
  project_title: string;
  status: string;
  viewed_at: string | null;
  expires_at: string;
  expired: boolean;
  responded: boolean;
  rating: number | null;
  feedback: string | null;
}

export interface ClientReviewRecord {
  id: string;
  project_id: string;
  token: string;
  client_name: string | null;
  client_email: string | null;
  status: string;
  feedback: string | null;
  rating: number | null;
  viewed_at: string | null;
  responded_at: string | null;
  expires_at: string;
  created_at: string;
}

export interface ClientReviewRespondResult {
  ok: boolean;
  status: string;
  message: string;
}

export async function createReview(
  projectId: string,
  clientName?: string,
  clientEmail?: string,
  expiresDays = 30,
) {
  return apiRequest<ClientReviewCreateResult>({
    method: "POST",
    path: `${API_PREFIX}/client-review/create`,
    body: {
      project_id: projectId,
      client_name: clientName?.trim() || undefined,
      client_email: clientEmail?.trim() || undefined,
      expires_days: expiresDays,
    },
  });
}

export async function getReview(token: string) {
  return apiRequest<ClientReviewPublic>({
    method: "GET",
    path: `${API_PREFIX}/client-review/${encodeURIComponent(token)}`,
  });
}

export async function respondToReview(
  token: string,
  status: "approved" | "revision_requested",
  feedback?: string,
  rating?: number,
) {
  return apiRequest<ClientReviewRespondResult>({
    method: "POST",
    path: `${API_PREFIX}/client-review/${encodeURIComponent(token)}/respond`,
    body: {
      status,
      feedback: feedback?.trim() || undefined,
      rating,
    },
  });
}

export async function getProjectReviews(projectId: string) {
  return apiRequest<{ items: ClientReviewRecord[]; count: number }>({
    method: "GET",
    path: `${API_PREFIX}/client-review/project/${encodeURIComponent(projectId)}`,
  });
}
