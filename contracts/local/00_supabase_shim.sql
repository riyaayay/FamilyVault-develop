-- ==============================================================================
-- Local / CI Supabase compatibility shim
-- ==============================================================================
-- contracts/schema.sql targets Supabase, which provides the `auth` schema, the
-- `auth.uid()` helper and the `anon` / `authenticated` / `service_role` roles.
-- A plain PostgreSQL container (docker-compose `db`, GitHub Actions service
-- container) has none of these, so the first RLS policy fails with
-- `schema "auth" does not exist`.
--
-- This file recreates just enough of that surface for the schema, the seed
-- script and the RLS penetration tests to run unchanged. It must run BEFORE
-- schema.sql (docker-entrypoint-initdb.d executes files in name order).
--
-- NEVER apply this file to a real Supabase project: it would shadow the
-- platform's own auth.uid().
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS auth;

-- Mirrors Supabase: the caller's id is the `sub` claim of the request JWT,
-- exposed through the `request.jwt.claim.sub` / `request.jwt.claims` GUCs.
CREATE OR REPLACE FUNCTION auth.uid() RETURNS UUID
LANGUAGE sql STABLE
AS $$
    SELECT NULLIF(
        COALESCE(
            NULLIF(current_setting('request.jwt.claim.sub', true), ''),
            NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'
        ),
        ''
    )::uuid
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN BYPASSRLS;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated, service_role;
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- Tables are created afterwards by schema.sql, so grant through default
-- privileges. RLS policies (not grants) are what isolate tenants.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO anon, authenticated, service_role;
