"""Notifications API: runtime warnings and errors captured by the backend.

Collects log messages at WARNING level and above into an in-memory ring buffer.
The frontend notification bell polls this endpoint to display alerts.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["notifications"])

# ---------------------------------------------------------------------------
# In-memory notification store (ring buffer, thread-safe)
# ---------------------------------------------------------------------------
_MAX_NOTIFICATIONS = 200


class Notification(BaseModel):
    id: str
    timestamp: float
    level: str  # "warning" | "error" | "critical"
    source: str  # module/component that emitted the message
    message: str
    read: bool = False


_lock = threading.Lock()
_notifications: deque[Notification] = deque(maxlen=_MAX_NOTIFICATIONS)


def push_notification(level: str, source: str, message: str) -> None:
    """Add a notification to the ring buffer (called from the log handler)."""
    n = Notification(
        id=str(uuid4()),
        timestamp=time.time(),
        level=level,
        source=source,
        message=message,
    )
    with _lock:
        _notifications.append(n)


def _get_notifications(
    *, unread_only: bool = False, limit: int = 50
) -> list[Notification]:
    with _lock:
        items = list(_notifications)
    items.reverse()  # newest first
    if unread_only:
        items = [n for n in items if not n.read]
    return items[:limit]


def _mark_all_read() -> int:
    count = 0
    with _lock:
        for n in _notifications:
            if not n.read:
                n.read = True
                count += 1
    return count


def _mark_read(notification_id: str) -> bool:
    with _lock:
        for n in _notifications:
            if n.id == notification_id:
                n.read = True
                return True
    return False


# ---------------------------------------------------------------------------
# Custom logging handler that feeds into the ring buffer
# ---------------------------------------------------------------------------
class NotificationLogHandler(logging.Handler):
    """Captures WARNING+ log records from the backend and pushes them
    into the notification ring buffer for the frontend bell."""

    # Modules to skip (too noisy or internal)
    _SKIP_LOGGERS = frozenset({"uvicorn.access", "uvicorn.error", "watchfiles"})

    def emit(self, record: logging.LogRecord) -> None:
        if record.name in self._SKIP_LOGGERS:
            return
        level_map = {
            logging.WARNING: "warning",
            logging.ERROR: "error",
            logging.CRITICAL: "critical",
        }
        level = level_map.get(record.levelno, "warning")
        source = record.name.replace("payment_analysis.backend.", "")
        try:
            msg = self.format(record)
        except Exception:
            msg = str(record.getMessage())
        push_notification(level, source, msg)


def install_log_handler() -> None:
    """Attach the notification log handler to the root logger."""
    handler = NotificationLogHandler()
    handler.setLevel(logging.WARNING)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger("payment_analysis").addHandler(handler)


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------
class NotificationOut(BaseModel):
    id: str
    timestamp: float
    level: str
    source: str
    message: str
    read: bool


class NotificationListOut(BaseModel):
    notifications: list[NotificationOut]
    unread_count: int
    total_count: int


class MarkReadOut(BaseModel):
    marked: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("", response_model=NotificationListOut, operation_id="listNotifications")
def list_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    limit: int = Query(50, ge=1, le=200, description="Max notifications to return"),
) -> NotificationListOut:
    """List runtime notifications (warnings, errors) captured by the backend."""
    items = _get_notifications(unread_only=unread_only, limit=limit)
    with _lock:
        unread = sum(1 for n in _notifications if not n.read)
        total = len(_notifications)
    return NotificationListOut(
        notifications=[NotificationOut(**n.model_dump()) for n in items],
        unread_count=unread,
        total_count=total,
    )


@router.post("/read-all", response_model=MarkReadOut, operation_id="markAllNotificationsRead")
def mark_all_read() -> MarkReadOut:
    """Mark all notifications as read."""
    count = _mark_all_read()
    return MarkReadOut(marked=count)


@router.post("/{notification_id}/read", response_model=MarkReadOut, operation_id="markNotificationRead")
def mark_read(notification_id: str) -> MarkReadOut:
    """Mark a single notification as read."""
    found = _mark_read(notification_id)
    return MarkReadOut(marked=1 if found else 0)
