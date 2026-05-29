"""
Newsletter — contacts, séquences et emails (cockpit.db).
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Literal

from cockpit_db import _connect, _lock, _row_to_dict, _rows_to_dicts, _utc_now

SequenceTrigger = Literal["project_delivered", "manual", "web_form"]
SequenceStatus = Literal["pending", "in_progress", "completed", "cancelled"]
EmailType = Literal["welcome_j0", "welcome_j1", "welcome_j3", "newsletter"]
EmailStatus = Literal["draft", "scheduled", "sent", "failed"]

_TRIGGERS = frozenset({"project_delivered", "manual", "web_form"})
_SEQUENCE_STATUSES = frozenset(
    {"pending", "in_progress", "completed", "cancelled"}
)
_EMAIL_TYPES = frozenset({"welcome_j0", "welcome_j1", "welcome_j3", "newsletter"})
_EMAIL_STATUSES = frozenset({"draft", "scheduled", "sent", "failed"})


def _contact_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    data = _row_to_dict(row)
    if data is None:
        return None
    if "subscribed" in data:
        data["subscribed"] = bool(data["subscribed"])
    return data


def _contacts_from_rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item = _contact_from_row(row)
        if item:
            out.append(item)
    return out


def init_newsletter_db() -> None:
    """Crée les tables newsletter_contacts, newsletter_sequences et newsletter_emails."""
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS newsletter_contacts (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    company TEXT,
                    sector TEXT,
                    project_id TEXT,
                    project_type TEXT,
                    personality_notes TEXT,
                    subscribed INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS newsletter_sequences (
                    id TEXT PRIMARY KEY,
                    contact_id TEXT NOT NULL,
                    trigger TEXT NOT NULL CHECK (
                        trigger IN ('project_delivered', 'manual', 'web_form')
                    ),
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (
                        status IN ('pending', 'in_progress', 'completed', 'cancelled')
                    ),
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (contact_id) REFERENCES newsletter_contacts(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS newsletter_emails (
                    id TEXT PRIMARY KEY,
                    sequence_id TEXT,
                    contact_id TEXT,
                    type TEXT NOT NULL CHECK (
                        type IN ('welcome_j0', 'welcome_j1', 'welcome_j3', 'newsletter')
                    ),
                    subject TEXT NOT NULL,
                    html_content TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft' CHECK (
                        status IN ('draft', 'scheduled', 'sent', 'failed')
                    ),
                    scheduled_at TEXT,
                    sent_at TEXT,
                    brevo_message_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (sequence_id) REFERENCES newsletter_sequences(id)
                        ON DELETE SET NULL,
                    FOREIGN KEY (contact_id) REFERENCES newsletter_contacts(id)
                        ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_newsletter_contacts_email
                    ON newsletter_contacts (email COLLATE NOCASE);
                CREATE INDEX IF NOT EXISTS idx_newsletter_contacts_sector
                    ON newsletter_contacts (sector, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_newsletter_sequences_contact
                    ON newsletter_sequences (contact_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_newsletter_sequences_status
                    ON newsletter_sequences (status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_newsletter_emails_status_scheduled
                    ON newsletter_emails (status, scheduled_at ASC);
                CREATE INDEX IF NOT EXISTS idx_newsletter_emails_contact
                    ON newsletter_emails (contact_id, created_at DESC);
                """
            )
            conn.commit()
        finally:
            conn.close()


# --- Contacts ---


def add_contact(
    *,
    email: str,
    name: str,
    company: str | None = None,
    sector: str | None = None,
    project_id: str | None = None,
    project_type: str | None = None,
    personality_notes: str | None = None,
    subscribed: bool = True,
    contact_id: str | None = None,
) -> dict[str, Any]:
    clean_email = email.strip().lower()
    clean_name = name.strip()
    if not clean_email:
        raise ValueError("email est requis.")
    if not clean_name:
        raise ValueError("name est requis.")

    cid = (contact_id or str(uuid.uuid4())).strip()
    now = _utc_now()

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO newsletter_contacts (
                    id, email, name, company, sector, project_id, project_type,
                    personality_notes, subscribed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    clean_email,
                    clean_name,
                    company.strip() if company else None,
                    sector.strip() if sector else None,
                    project_id.strip() if project_id else None,
                    project_type.strip() if project_type else None,
                    personality_notes.strip() if personality_notes else None,
                    1 if subscribed else 0,
                    now,
                ),
            )
            conn.commit()
            return _contact_from_row(
                conn.execute(
                    "SELECT * FROM newsletter_contacts WHERE id = ?",
                    (cid,),
                ).fetchone()
            )  # type: ignore[return-value]
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Email déjà enregistré : {clean_email}") from exc
        finally:
            conn.close()


def get_contact(contact_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM newsletter_contacts WHERE id = ?",
                (contact_id.strip(),),
            ).fetchone()
            return _contact_from_row(row)
        finally:
            conn.close()


def get_contact_by_email(email: str) -> dict[str, Any] | None:
    clean = email.strip().lower()
    if not clean:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM newsletter_contacts
                WHERE email = ? COLLATE NOCASE
                """,
                (clean,),
            ).fetchone()
            return _contact_from_row(row)
        finally:
            conn.close()


def list_contacts(*, limit: int = 500, subscribed_only: bool = False) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 2000))
    with _lock:
        conn = _connect()
        try:
            if subscribed_only:
                rows = conn.execute(
                    """
                    SELECT * FROM newsletter_contacts
                    WHERE subscribed = 1
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (safe_limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM newsletter_contacts
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (safe_limit,),
                ).fetchall()
            return _contacts_from_rows(rows)
        finally:
            conn.close()


def update_contact(contact_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {
        "email",
        "name",
        "company",
        "sector",
        "project_id",
        "project_type",
        "personality_notes",
        "subscribed",
    }
    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "email" and isinstance(value, str):
            updates[key] = value.strip().lower()
        elif key == "subscribed":
            updates[key] = 1 if bool(value) else 0
        elif isinstance(value, str):
            updates[key] = value.strip() if value else value
        else:
            updates[key] = value

    if not updates:
        return get_contact(contact_id)

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [contact_id.strip()]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE newsletter_contacts SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM newsletter_contacts WHERE id = ?",
                (contact_id.strip(),),
            ).fetchone()
            return _contact_from_row(row)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Email déjà utilisé par un autre contact.") from exc
        finally:
            conn.close()


def delete_contact(contact_id: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "DELETE FROM newsletter_contacts WHERE id = ?",
                (contact_id.strip(),),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# --- Sequences ---


def create_sequence(
    contact_id: str,
    trigger: SequenceTrigger,
    *,
    status: SequenceStatus = "pending",
    sequence_id: str | None = None,
) -> dict[str, Any]:
    trig = trigger.strip().lower()
    if trig not in _TRIGGERS:
        raise ValueError("trigger invalide.")

    stat = status.strip().lower()
    if stat not in _SEQUENCE_STATUSES:
        raise ValueError("status invalide.")

    cid = contact_id.strip()
    sid = (sequence_id or str(uuid.uuid4())).strip()
    now = _utc_now()

    with _lock:
        conn = _connect()
        try:
            contact = conn.execute(
                "SELECT 1 FROM newsletter_contacts WHERE id = ?",
                (cid,),
            ).fetchone()
            if contact is None:
                raise ValueError(f"Contact inconnu : {cid}")

            conn.execute(
                """
                INSERT INTO newsletter_sequences (id, contact_id, trigger, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, cid, trig, stat, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM newsletter_sequences WHERE id = ?",
                (sid,),
            ).fetchone()
            result = _row_to_dict(row)
            if result is None:
                raise RuntimeError("Séquence non retrouvée après insertion.")
            return result
        finally:
            conn.close()


def get_sequence(sequence_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM newsletter_sequences WHERE id = ?",
                (sequence_id.strip(),),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def list_sequences(
    *,
    status: SequenceStatus | None = None,
    contact_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if status:
        stat = status.strip().lower()
        if stat not in _SEQUENCE_STATUSES:
            raise ValueError("status invalide.")
        clauses.append("status = ?")
        params.append(stat)

    if contact_id:
        clauses.append("contact_id = ?")
        params.append(contact_id.strip())

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    safe_limit = max(1, min(int(limit), 2000))

    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                f"""
                SELECT * FROM newsletter_sequences
                {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (*params, safe_limit),
            ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


# --- Emails ---


def add_email(
    *,
    type: EmailType,
    subject: str,
    html_content: str,
    sequence_id: str | None = None,
    contact_id: str | None = None,
    status: EmailStatus = "draft",
    scheduled_at: str | None = None,
    sent_at: str | None = None,
    brevo_message_id: str | None = None,
    email_id: str | None = None,
) -> dict[str, Any]:
    kind = type.strip().lower()
    if kind not in _EMAIL_TYPES:
        raise ValueError("type email invalide.")

    stat = status.strip().lower()
    if stat not in _EMAIL_STATUSES:
        raise ValueError("status invalide.")

    subj = subject.strip()
    html = html_content.strip()
    if not subj:
        raise ValueError("subject est requis.")
    if not html:
        raise ValueError("html_content est requis.")

    eid = (email_id or str(uuid.uuid4())).strip()
    now = _utc_now()

    with _lock:
        conn = _connect()
        try:
            if sequence_id:
                seq = conn.execute(
                    "SELECT 1 FROM newsletter_sequences WHERE id = ?",
                    (sequence_id.strip(),),
                ).fetchone()
                if seq is None:
                    raise ValueError(f"Séquence inconnue : {sequence_id}")

            if contact_id:
                contact = conn.execute(
                    "SELECT 1 FROM newsletter_contacts WHERE id = ?",
                    (contact_id.strip(),),
                ).fetchone()
                if contact is None:
                    raise ValueError(f"Contact inconnu : {contact_id}")

            conn.execute(
                """
                INSERT INTO newsletter_emails (
                    id, sequence_id, contact_id, type, subject, html_content,
                    status, scheduled_at, sent_at, brevo_message_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid,
                    sequence_id.strip() if sequence_id else None,
                    contact_id.strip() if contact_id else None,
                    kind,
                    subj,
                    html,
                    stat,
                    scheduled_at,
                    sent_at,
                    brevo_message_id.strip() if brevo_message_id else None,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM newsletter_emails WHERE id = ?",
                (eid,),
            ).fetchone()
            result = _row_to_dict(row)
            if result is None:
                raise RuntimeError("Email non retrouvé après insertion.")
            return result
        finally:
            conn.close()


def list_emails(
    *,
    sequence_id: str | None = None,
    contact_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if sequence_id:
        clauses.append("sequence_id = ?")
        params.append(sequence_id.strip())
    if contact_id:
        clauses.append("contact_id = ?")
        params.append(contact_id.strip())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    safe_limit = max(1, min(int(limit), 2000))
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                f"""
                SELECT * FROM newsletter_emails
                {where}
                ORDER BY COALESCE(scheduled_at, created_at) ASC
                LIMIT ?
                """,
                (*params, safe_limit),
            ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


def get_email(email_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM newsletter_emails WHERE id = ?",
                (email_id.strip(),),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def list_pending_emails(*, limit: int = 100) -> list[dict[str, Any]]:
    """Emails planifiés prêts à l'envoi (scheduled_at passé ou absent)."""
    now = _utc_now()
    safe_limit = max(1, min(int(limit), 500))
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM newsletter_emails
                WHERE status = 'scheduled'
                  AND (scheduled_at IS NULL OR scheduled_at <= ?)
                ORDER BY COALESCE(scheduled_at, created_at) ASC
                LIMIT ?
                """,
                (now, safe_limit),
            ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


def update_email(email_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {
        "sequence_id",
        "contact_id",
        "type",
        "subject",
        "html_content",
        "status",
        "scheduled_at",
        "sent_at",
        "brevo_message_id",
    }
    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "type":
            kind = str(value).strip().lower()
            if kind not in _EMAIL_TYPES:
                raise ValueError("type email invalide.")
            updates[key] = kind
        elif key == "status":
            stat = str(value).strip().lower()
            if stat not in _EMAIL_STATUSES:
                raise ValueError("status invalide.")
            updates[key] = stat
        elif isinstance(value, str):
            updates[key] = value.strip() if value else value
        else:
            updates[key] = value

    if not updates:
        return get_email(email_id)

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [email_id.strip()]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE newsletter_emails SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM newsletter_emails WHERE id = ?",
                (email_id.strip(),),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()
