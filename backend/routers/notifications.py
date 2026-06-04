"""
Compatibilité — notifications système (stockage mémoire API v2).

Les routes HTTP sont exposées par ``api.routes.notifications`` :
  GET    /api/notifications
  POST   /api/notifications/mark-read/{id}
  POST   /api/notifications/mark-all-read
  PATCH  /api/notifications/{id}/read
  PATCH  /api/notifications/read-all
  DELETE /api/notifications/clear
"""

from api.notifications_memory import (
    NotificationCreate,
    NotificationListResponse,
    NotificationRow,
    notify,
    schedule_notify,
)

__all__ = [
    "NotificationCreate",
    "NotificationListResponse",
    "NotificationRow",
    "notify",
    "schedule_notify",
]
