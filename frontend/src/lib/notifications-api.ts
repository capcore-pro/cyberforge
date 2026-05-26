import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface ContactNotificationItem {
  demo_id: string;
  token: string;
  title: string;
  interested_at: string;
  client_name: string | null;
  client_email: string | null;
}

export interface ContactNotificationsResponse {
  unread_count: number;
  items: ContactNotificationItem[];
}

export async function fetchContactNotifications() {
  return apiRequest<ContactNotificationsResponse>({
    method: "GET",
    path: `${API_PREFIX}/notifications/contacts`,
  });
}

export async function fetchContactUnreadCount() {
  return apiRequest<{ unread_count: number }>({
    method: "GET",
    path: `${API_PREFIX}/notifications/contacts/unread-count`,
  });
}

export async function markContactNotificationsSeen() {
  return apiRequest<{ marked: number }>({
    method: "POST",
    path: `${API_PREFIX}/notifications/contacts/mark-seen`,
  });
}
