/**
 * Types notifications contacts — routes /api/notifications/contacts retirées.
 */

export interface ContactNotificationItem {
  id: string;
  title: string;
  message?: string | null;
  created_at: string;
  read?: boolean;
  project_id?: string | null;
}

export interface ContactNotificationsResponse {
  unread_count: number;
  items: ContactNotificationItem[];
}
