-- Add acknowledgement columns to alerts table
-- These columns were present in init.sql but missing from deployments
-- created before the acknowledge feature was added.

ALTER TABLE alerts ADD COLUMN IF NOT EXISTS acknowledged_at   TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS acknowledged_by   TEXT        DEFAULT NULL;
