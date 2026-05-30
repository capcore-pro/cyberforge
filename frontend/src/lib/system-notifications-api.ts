import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface SystemNotification {
  id: string;
  type: string;
  level: string;
  title: string;
  message: string | null;
  project_id: string | null;
  project_name: string | null;
  read: boolean;
  telegram_sent: boolean;
  created_at: string;
}

export interface SystemNotificationListResponse {
  items: SystemNotification[];
}

export async function fetchSystemNotifications(unreadOnly = false) {
  const query = unreadOnly ? "?unread_only=true" : "";
  return apiRequest<SystemNotificationListResponse>({
    method: "GET",
    path: `${API_PREFIX}/notifications/${query}`,
  });
}

export async function fetchSystemUnreadCount() {
  return apiRequest<{ count: number }>({
    method: "GET",
    path: `${API_PREFIX}/notifications/unread-count`,
  });
}

export async function markSystemNotificationRead(notificationId: string) {
  return apiRequest<SystemNotification>({
    method: "PATCH",
    path: `${API_PREFIX}/notifications/${notificationId}/read`,
  });
}

export async function markAllSystemNotificationsRead() {
  return apiRequest<{ marked: number }>({
    method: "PATCH",
    path: `${API_PREFIX}/notifications/read-all`,
  });
}

export async function clearSystemNotifications() {
  return apiRequest<{ deleted: number }>({
    method: "DELETE",
    path: `${API_PREFIX}/notifications/clear`,
  });
}
