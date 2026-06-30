-- Migration 049 — Suivi notification email post-build desktop

ALTER TABLE electron_builds
ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ;
