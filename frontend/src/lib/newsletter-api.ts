import { API_PREFIX } from "@shared/constants";
import type { ProjectRecord } from "@shared/types";
import { apiRequest } from "@/lib/api-client";

const NEWSLETTER = `${API_PREFIX}/newsletter`;

export type SequenceTrigger = "project_delivered" | "manual" | "web_form";
export type SequenceStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "cancelled";
export type WelcomeEmailType = "welcome_j0" | "welcome_j1" | "welcome_j3";
export type EmailStatus = "draft" | "scheduled" | "sent" | "failed";

export interface NewsletterContact {
  id: string;
  email: string;
  name: string;
  company: string | null;
  sector: string | null;
  project_id: string | null;
  project_type: string | null;
  personality_notes: string | null;
  subscribed: boolean;
  created_at: string;
}

export interface NewsletterSequence {
  id: string;
  contact_id: string;
  trigger: SequenceTrigger;
  status: SequenceStatus;
  created_at: string;
}

export interface NewsletterEmail {
  id: string;
  sequence_id: string | null;
  contact_id: string | null;
  type: WelcomeEmailType | "newsletter";
  subject: string;
  html_content: string;
  status: EmailStatus;
  scheduled_at: string | null;
  sent_at: string | null;
  brevo_message_id: string | null;
  created_at: string;
}

export interface TriggerSequenceResult {
  contact: NewsletterContact;
  sequence_id: string;
  emails_scheduled: number;
  j0_sent: boolean;
  emails: NewsletterEmail[];
}

export interface SendPendingResult {
  processed: number;
  sent: number;
  failed: number;
  skipped: number;
  results: { email_id?: string; sent?: boolean; skipped?: boolean; error?: string }[];
}

export const TRIGGER_LABELS: Record<SequenceTrigger, string> = {
  project_delivered: "Projet livré",
  manual: "Manuel",
  web_form: "Formulaire web",
};

export const SEQUENCE_STATUS_LABELS: Record<SequenceStatus, string> = {
  pending: "En attente",
  in_progress: "En cours",
  completed: "Terminée",
  cancelled: "Annulée",
};

export async function fetchNewsletterContacts() {
  return apiRequest<NewsletterContact[]>({
    method: "GET",
    path: `${NEWSLETTER}/contacts`,
  });
}

export async function createNewsletterContact(body: {
  email: string;
  name: string;
  company?: string | null;
  sector?: string | null;
  subscribed?: boolean;
}) {
  return apiRequest<NewsletterContact>({
    method: "POST",
    path: `${NEWSLETTER}/contacts`,
    body,
  });
}

export async function updateNewsletterContact(
  id: string,
  body: Partial<{
    email: string;
    name: string;
    company: string | null;
    sector: string | null;
    subscribed: boolean;
  }>,
) {
  return apiRequest<NewsletterContact>({
    method: "PUT",
    path: `${NEWSLETTER}/contacts/${id}`,
    body,
  });
}

export async function deleteNewsletterContact(id: string) {
  return apiRequest<void>({
    method: "DELETE",
    path: `${NEWSLETTER}/contacts/${id}`,
  });
}

export async function fetchNewsletterSequences(status?: SequenceStatus) {
  const q = status ? `?status=${status}` : "";
  return apiRequest<NewsletterSequence[]>({
    method: "GET",
    path: `${NEWSLETTER}/sequences${q}`,
  });
}

export async function fetchSequenceEmails(sequenceId: string) {
  return apiRequest<NewsletterEmail[]>({
    method: "GET",
    path: `${NEWSLETTER}/sequences/${sequenceId}/emails`,
  });
}

export async function triggerWelcomeSequence(
  projectId: string,
  body?: { email?: string; name?: string },
) {
  return apiRequest<TriggerSequenceResult>({
    method: "POST",
    path: `${NEWSLETTER}/sequences/trigger/${projectId}`,
    body: body ?? {},
  });
}

export async function sendPendingNewsletterEmails() {
  return apiRequest<SendPendingResult>({
    method: "POST",
    path: `${NEWSLETTER}/send-pending`,
  });
}

export async function generateNewsletterEmail(body: {
  theme: string;
  context?: string;
}) {
  return apiRequest<NewsletterEmail>({
    method: "POST",
    path: `${NEWSLETTER}/newsletter/generate`,
    body: { theme: body.theme, context: body.context ?? "" },
  });
}

export async function previewNewsletterEmail(emailId: string) {
  return apiRequest<{ preview_sent: boolean; to: string; brevo_message_id?: string }>({
    method: "POST",
    path: `${NEWSLETTER}/newsletter/${emailId}/preview`,
  });
}

export async function sendNewsletterToAll(emailId: string) {
  return apiRequest<{
    email_id: string;
    recipients: number;
    sent: number;
    failed: number;
  }>({
    method: "POST",
    path: `${NEWSLETTER}/newsletter/${emailId}/send-all`,
  });
}

export async function fetchProjectsForNewsletter() {
  return apiRequest<ProjectRecord[]>({
    method: "GET",
    path: `${API_PREFIX}/projects`,
  });
}
