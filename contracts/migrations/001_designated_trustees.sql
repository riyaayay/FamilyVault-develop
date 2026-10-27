-- ==============================================================================
-- Migration 001: designated trustees for PRIVATE_STRICT documents & digital wills
-- ==============================================================================
-- Brings a database created from an older contracts/schema.sql up to date.
-- Fresh installs already get all of this from schema.sql. Safe to re-run.
--
--   Supabase:  SQL editor -> paste -> Run
--   Local:     psql "$DATABASE_URL" -f contracts/migrations/001_designated_trustees.sql
-- ==============================================================================

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS designated_trustee_ids JSONB DEFAULT '[]'::jsonb NOT NULL;

DROP POLICY IF EXISTS "Document access policy" ON documents;

CREATE POLICY "Document access policy"
ON documents FOR SELECT
USING (
    auth.uid() IS NOT NULL
    AND is_member_of_joint_family(joint_family_id)
    AND (
        uploader_id = auth.uid()
        OR
        (
            (capsule_status NOT IN ('LOCKED', 'TRUSTEE_PENDING') OR (time_capsule_unlock_at IS NOT NULL AND time_capsule_unlock_at <= NOW() AND trustee_approvals_required = 0))
            AND (
                visibility_tier = 'JOINT_CLAN'
                OR
                (visibility_tier = 'NUCLEAR_HOUSEHOLD' AND is_member_of_nuclear_family(nuclear_family_id))
                OR
                (visibility_tier = 'PRIVATE_STRICT' AND (
                    (target_unlock_recipient_id = auth.uid() AND capsule_status = 'RELEASED')
                    OR designated_trustee_ids ? auth.uid()::text
                ))
            )
        )
    )
);
