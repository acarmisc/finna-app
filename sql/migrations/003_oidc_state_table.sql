-- Migration: oidc_state table for multi-replica support
-- Version: 003
-- Created: 2026-05-23
-- Purpose: Replace in-memory state/nonce storage with database-backed storage
--          for multi-replica deployments

BEGIN;

-- oidc_state: stores state and nonce values for OIDC flow
-- Used to validate callback requests and prevent CSRF attacks
CREATE TABLE IF NOT EXISTS oidc_state (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    state           TEXT NOT NULL UNIQUE,  -- The OAuth state parameter
    provider_id     UUID NOT NULL,
    nonce           TEXT NOT NULL,
    code_verifier   TEXT NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL
);

-- Index for cleanup of expired states
CREATE INDEX IF NOT EXISTS idx_oidc_state_expires ON oidc_state (expires_at);

-- Index for quick lookup by state
CREATE INDEX IF NOT EXISTS idx_oidc_state_state ON oidc_state (state);

COMMENT ON TABLE oidc_state IS 'OIDC state storage for multi-replica support. Entries expire after 10 minutes.';
COMMENT ON COLUMN oidc_state.state IS 'The OAuth 2.0 state parameter for CSRF protection';
COMMENT ON COLUMN oidc_state.nonce IS 'The OIDC nonce for ID token binding';
COMMENT ON COLUMN oidc_state.code_verifier IS 'The PKCE code_verifier for S256 challenge';

COMMIT;
