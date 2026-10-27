-- ==============================================================================
-- FamilyVault Authoritative Schema & Security Protocol (contracts/schema.sql)
-- Owner: Runeet (Lead / Backend & Database Architect)
-- Target Engine: Supabase PostgreSQL 15+ / Standard PostgreSQL with pgcrypto
-- ==============================================================================
--
-- ARCHITECTURAL CONTRACTS & UUID CONVENTION (FOR RIYA & AYUSHMAN):
-- 1. SINGLE SOURCE OF TRUTH FOR IDENTITIES:
--    The `users.id` column (UUIDv4) is generated in PostgreSQL upon user signup.
--    This EXACT UUID string must be reused as the primary identifier across services:
--    - Neo4j AuraDB: (:Person {id: users.id, name: users.full_name})
--    - Biometrics Service: `media_contributions.matched_face_ids` contains an array of these UUIDs.
--    - DO NOT generate independent IDs for people in Neo4j. Pass this UUID on creation.
--
-- 2. THREE-TIER VISIBILITY & TENANT ISOLATION (FOR AYUSH & QA AUDITING):
--    - JOINT_CLAN: Visible to all verified members belonging to the parent joint family.
--    - NUCLEAR_HOUSEHOLD: Restricted strictly to members belonging to that nuclear household.
--    - PRIVATE_STRICT: Restricted to creator/owner and designated trustee accounts.
--
-- 3. MILESTONE LOCKS & EMERGENCY PROTOCOLS:
--    - Documents marked with `time_capsule_unlock_at` remain locked until the timestamp
--      passes OR required trustee sign-offs are satisfied.
--    - Health records flagged with `is_emergency_visible = true` can be accessed by any
--      joint-family member via the Emergency Red Alert endpoint.
-- ==============================================================================

-- Enable UUID & Cryptographic Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- CUSTOM ENUMS
-- ==============================================================================

CREATE TYPE user_role AS ENUM (
    'ADMIN',       -- Joint family head / platform administrator
    'MEMBER',      -- Standard adult family member with read/write access
    'CHILD',       -- Supervised junior profile (restricted write/delete)
    'VIEWER'       -- Read-only relative or trusted guest
);

CREATE TYPE family_relation AS ENUM (
    'HEAD',
    'SPOUSE',
    'CHILD',
    'PARENT',
    'SIBLING',
    'EXTENDED'
);

CREATE TYPE visibility_tier AS ENUM (
    'JOINT_CLAN',          -- Shared with all households under the Joint Family umbrella
    'NUCLEAR_HOUSEHOLD',   -- Confidential to the specific nuclear household
    'PRIVATE_STRICT'       -- Locked strictly to creator / named trustees
);

CREATE TYPE document_category AS ENUM (
    'FINANCIAL',
    'PROPERTY',
    'HEALTH',
    'IDENTITY',
    'LEGACY_WILL',
    'MEMORABILIA',
    'LEGAL'
);

CREATE TYPE time_capsule_status AS ENUM (
    'ACTIVE',             -- Standard unlocked document
    'LOCKED',             -- Milestone-locked (future unlock timestamp)
    'TRUSTEE_PENDING',    -- Awaiting multi-trustee confirmation (e.g., digital will)
    'RELEASED'            -- Formally unlocked and made accessible
);

CREATE TYPE media_status AS ENUM (
    'PENDING_INBOX',      -- Uploaded, awaiting family admin / recipient approval
    'AUTO_PUBLISHED',     -- Biometric match >= 0.85 threshold, published automatically
    'REJECTED'            -- Rejected from public feed (retained in uploader's private archive)
);

CREATE TYPE pet_type AS ENUM (
    'DOG',
    'CAT',
    'BIRD',
    'OTHER'
);

-- ==============================================================================
-- 1. TENANT ENTITIES (JOINT & NUCLEAR FAMILIES)
-- ==============================================================================

-- Top-level Joint Family (Clan / Ancestral umbrella)
CREATE TABLE IF NOT EXISTS joint_families (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    ancestral_origin VARCHAR(255),
    motto TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- Nuclear Family (Specific household unit under a Joint Family)
CREATE TABLE IF NOT EXISTS nuclear_families (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    joint_family_id UUID NOT NULL REFERENCES joint_families(id) ON DELETE CASCADE,
    household_name VARCHAR(255) NOT NULL,
    current_city VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

CREATE INDEX idx_nuclear_families_joint ON nuclear_families(joint_family_id);

-- ==============================================================================
-- 2. USERS & MEMBERSHIPS (IDENTITIES)
-- ==============================================================================

-- User identity table. The `id` matches Supabase `auth.users(id)` and Neo4j `Person.id`.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    preferred_name VARCHAR(100),
    avatar_url TEXT,
    phone_number VARCHAR(30),
    date_of_birth DATE,
    gender VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- Association linking users to nuclear and joint families with granular roles
CREATE TABLE IF NOT EXISTS family_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joint_family_id UUID NOT NULL REFERENCES joint_families(id) ON DELETE CASCADE,
    nuclear_family_id UUID NOT NULL REFERENCES nuclear_families(id) ON DELETE CASCADE,
    role user_role DEFAULT 'MEMBER' NOT NULL,
    relation_to_head family_relation DEFAULT 'EXTENDED' NOT NULL,
    is_emergency_contact BOOLEAN DEFAULT FALSE NOT NULL,
    joined_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    CONSTRAINT unique_user_family_pair UNIQUE (user_id, nuclear_family_id)
);

CREATE INDEX idx_memberships_user ON family_memberships(user_id);
CREATE INDEX idx_memberships_joint ON family_memberships(joint_family_id);
CREATE INDEX idx_memberships_nuclear ON family_memberships(nuclear_family_id);

-- ==============================================================================
-- 3. SECURE DOCUMENT VAULT (WITH TIME CAPSULE & DIGITAL WILL ENGINE)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    joint_family_id UUID NOT NULL REFERENCES joint_families(id) ON DELETE CASCADE,
    nuclear_family_id UUID REFERENCES nuclear_families(id) ON DELETE SET NULL,
    uploader_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category document_category NOT NULL,
    visibility_tier visibility_tier DEFAULT 'NUCLEAR_HOUSEHOLD' NOT NULL,
    
    -- Cloudflare R2 Storage Pointer & Encryption Metadata
    r2_storage_key TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    checksum_sha256 VARCHAR(64),
    
    -- Milestone Lock & Time Capsule Properties
    capsule_status time_capsule_status DEFAULT 'ACTIVE' NOT NULL,
    time_capsule_unlock_at TIMESTAMPTZ,
    trustee_approvals_required INT DEFAULT 0 NOT NULL,
    trustee_approvals_received JSONB DEFAULT '[]'::jsonb NOT NULL,
    target_unlock_recipient_id UUID REFERENCES users(id) ON DELETE SET NULL,
    -- users.id strings named by the uploader; only they may sign, and they may
    -- read a PRIVATE_STRICT record once it is no longer sealed.
    designated_trustee_ids JSONB DEFAULT '[]'::jsonb NOT NULL,
    
    -- Vision Ingestion Auto-Extracted Metadata (JSONB)
    extracted_metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

CREATE INDEX idx_documents_joint ON documents(joint_family_id);
CREATE INDEX idx_documents_nuclear ON documents(nuclear_family_id);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_visibility ON documents(visibility_tier);
CREATE INDEX idx_documents_status ON documents(capsule_status);

-- ==============================================================================
-- 4. BIOMETRIC MEDIA & INBOX CONTRIBUTIONS
-- ==============================================================================

CREATE TABLE IF NOT EXISTS media_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    joint_family_id UUID NOT NULL REFERENCES joint_families(id) ON DELETE CASCADE,
    uploader_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    media_title VARCHAR(255),
    media_type VARCHAR(50) DEFAULT 'image/jpeg' NOT NULL,
    r2_storage_key TEXT NOT NULL,
    
    -- Biometric AI Pipeline Results (InsightFace 512D)
    matched_face_ids JSONB DEFAULT '[]'::jsonb NOT NULL, -- Array of users.id UUIDs
    confidence_scores JSONB DEFAULT '{}'::jsonb NOT NULL, -- Map: { "<UUID>": 0.94 }
    
    -- Inbox Workflow Status
    status media_status DEFAULT 'PENDING_INBOX' NOT NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approval_timestamp TIMESTAMPTZ,
    rejection_reason TEXT,
    
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

CREATE INDEX idx_media_joint ON media_contributions(joint_family_id);
CREATE INDEX idx_media_uploader ON media_contributions(uploader_id);
CREATE INDEX idx_media_status ON media_contributions(status);
CREATE INDEX idx_media_matched_faces_gin ON media_contributions USING GIN (matched_face_ids);

-- ==============================================================================
-- 5. HEALTH RECORDS & EMERGENCY "RED ALERT" MEDICAL ENGINE
-- ==============================================================================

CREATE TABLE IF NOT EXISTS health_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nuclear_family_id UUID NOT NULL REFERENCES nuclear_families(id) ON DELETE CASCADE,
    blood_group VARCHAR(10),
    allergies TEXT[] DEFAULT ARRAY[]::TEXT[],
    chronic_conditions TEXT[] DEFAULT ARRAY[]::TEXT[],
    current_medications JSONB DEFAULT '[]'::jsonb, -- Array of { name, dosage, frequency }
    emergency_notes TEXT,
    insurance_policy_number VARCHAR(100),
    primary_physician_contact VARCHAR(255),
    
    -- Red Alert Emergency Access: When true, bypasses nuclear isolation during emergency queries
    is_emergency_visible BOOLEAN DEFAULT TRUE NOT NULL,
    
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    CONSTRAINT unique_user_health_record UNIQUE (user_id)
);

CREATE INDEX idx_health_user ON health_records(user_id);
CREATE INDEX idx_health_emergency ON health_records(is_emergency_visible);

-- ==============================================================================
-- 6. HOUSEHOLD ASSETS (PETS & PROPERTIES)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS pets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nuclear_family_id UUID NOT NULL REFERENCES nuclear_families(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    pet_type pet_type NOT NULL,
    breed VARCHAR(100),
    date_of_birth DATE,
    microchip_number VARCHAR(100),
    vaccination_schedule JSONB DEFAULT '[]'::jsonb, -- Array of { vaccine, administered_on, next_due }
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

CREATE INDEX idx_pets_nuclear ON pets(nuclear_family_id);

CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    joint_family_id UUID NOT NULL REFERENCES joint_families(id) ON DELETE CASCADE,
    nuclear_family_id UUID REFERENCES nuclear_families(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    property_type VARCHAR(100) NOT NULL, -- e.g. "Ancestral Land", "Apartment", "Agricultural Plot"
    survey_number VARCHAR(100),
    address TEXT NOT NULL,
    estimated_valuation NUMERIC(15, 2),
    ownership_breakdown JSONB DEFAULT '[]'::jsonb, -- Array of { user_id, share_percentage }
    deed_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

CREATE INDEX idx_properties_joint ON properties(joint_family_id);

-- ==============================================================================
-- 7. AUDIT & ACCESS LOGS (IMMUTABLE SECURITY TRAIL)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    joint_family_id UUID NOT NULL REFERENCES joint_families(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL, -- e.g. "DOCUMENT_ACCESSED", "EMERGENCY_DOSSIER_ACCESSED", "VAULT_UNLOCKED"
    target_resource VARCHAR(100) NOT NULL,
    target_resource_id UUID,
    ip_address VARCHAR(45),
    user_agent TEXT,
    event_timestamp TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

CREATE INDEX idx_audit_joint ON audit_logs(joint_family_id);
CREATE INDEX idx_audit_actor ON audit_logs(actor_id);
CREATE INDEX idx_audit_event ON audit_logs(event_type);

-- ==============================================================================
-- 8. ROW LEVEL SECURITY (RLS) POLICIES — MULTI-TIER TENANT ISOLATION
-- ==============================================================================

-- Enable and Force RLS on all tables (prevents table owner and test session bypass)
ALTER TABLE joint_families ENABLE ROW LEVEL SECURITY;
ALTER TABLE joint_families FORCE ROW LEVEL SECURITY;
ALTER TABLE nuclear_families ENABLE ROW LEVEL SECURITY;
ALTER TABLE nuclear_families FORCE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE family_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE media_contributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_contributions FORCE ROW LEVEL SECURITY;
ALTER TABLE health_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_records FORCE ROW LEVEL SECURITY;
ALTER TABLE pets ENABLE ROW LEVEL SECURITY;
ALTER TABLE pets FORCE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

-- Helper Function 1: Check if current user is an active member of a joint family
CREATE OR REPLACE FUNCTION is_member_of_joint_family(family_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    IF family_id IS NULL OR auth.uid() IS NULL THEN
        RETURN FALSE;
    END IF;

    RETURN EXISTS (
        SELECT 1 
        FROM public.family_memberships
        WHERE user_id = auth.uid()
          AND joint_family_id = family_id
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public;

-- Helper Function 2: Check if current user is a member of a specific nuclear household
CREATE OR REPLACE FUNCTION is_member_of_nuclear_family(household_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    IF household_id IS NULL OR auth.uid() IS NULL THEN
        RETURN FALSE;
    END IF;

    RETURN EXISTS (
        SELECT 1 
        FROM public.family_memberships
        WHERE user_id = auth.uid()
          AND nuclear_family_id = household_id
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public;

-- Helper Function 3: Check if target user shares any joint family with the current user
CREATE OR REPLACE FUNCTION are_members_of_same_joint_family(target_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    IF target_user_id IS NULL OR auth.uid() IS NULL THEN
        RETURN FALSE;
    END IF;

    RETURN EXISTS (
        SELECT 1 
        FROM public.family_memberships m1
        JOIN public.family_memberships m2 ON m1.joint_family_id = m2.joint_family_id
        WHERE m1.user_id = auth.uid()
          AND m2.user_id = target_user_id
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public;

-- Policies for joint_families
CREATE POLICY "Users can view their own joint family"
ON joint_families FOR SELECT
USING (
    auth.uid() IS NOT NULL 
    AND is_member_of_joint_family(id)
);

-- Policies for nuclear_families
CREATE POLICY "Users can view households within their joint family"
ON nuclear_families FOR SELECT
USING (
    auth.uid() IS NOT NULL 
    AND is_member_of_joint_family(joint_family_id)
);

-- Policies for users
CREATE POLICY "Users can view profiles in their joint family"
ON users FOR SELECT
USING (
    auth.uid() IS NOT NULL
    AND (id = auth.uid() OR are_members_of_same_joint_family(id))
);

CREATE POLICY "Users can update their own profile"
ON users FOR UPDATE
USING (auth.uid() IS NOT NULL AND id = auth.uid());

-- Policies for family_memberships
CREATE POLICY "Users can view their own memberships"
ON family_memberships FOR SELECT
USING (auth.uid() IS NOT NULL AND user_id = auth.uid());

-- Policies for documents (Three-Tier RLS + Time Capsule Lock Enforcement)
CREATE POLICY "Document access policy"
ON documents FOR SELECT
USING (
    -- 1. Caller must be an authenticated member of the joint family
    auth.uid() IS NOT NULL
    AND is_member_of_joint_family(joint_family_id)
    AND (
        -- Uploader always has read access to their own upload
        uploader_id = auth.uid()
        OR
        (
            -- If milestone locked, only unlocked when timestamp has elapsed
            (capsule_status NOT IN ('LOCKED', 'TRUSTEE_PENDING') OR (time_capsule_unlock_at IS NOT NULL AND time_capsule_unlock_at <= NOW() AND trustee_approvals_required = 0))
            AND (
                -- Visibility Tier Check:
                -- JOINT_CLAN: accessible to everyone in the clan
                visibility_tier = 'JOINT_CLAN'
                OR
                -- NUCLEAR_HOUSEHOLD: accessible only to the specific household
                (visibility_tier = 'NUCLEAR_HOUSEHOLD' AND is_member_of_nuclear_family(nuclear_family_id))
                OR
                -- PRIVATE_STRICT: owner (above), designated trustees, and the target recipient once released
                (visibility_tier = 'PRIVATE_STRICT' AND (
                    (target_unlock_recipient_id = auth.uid() AND capsule_status = 'RELEASED')
                    OR designated_trustee_ids ? auth.uid()::text
                ))
            )
        )
    )
);

CREATE POLICY "Users can insert documents into their own nuclear family"
ON documents FOR INSERT
WITH CHECK (
    auth.uid() IS NOT NULL
    AND uploader_id = auth.uid()
    AND is_member_of_joint_family(joint_family_id)
    AND (nuclear_family_id IS NULL OR is_member_of_nuclear_family(nuclear_family_id))
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.joint_family_id = documents.joint_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
);

CREATE POLICY "Users can update their own documents or clan admins"
ON documents FOR UPDATE
USING (
    auth.uid() IS NOT NULL
    AND is_member_of_joint_family(joint_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.joint_family_id = documents.joint_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
    AND (
        uploader_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM family_memberships
            WHERE user_id = auth.uid()
              AND joint_family_id = documents.joint_family_id
              AND role = 'ADMIN'
        )
    )
)
WITH CHECK (
    auth.uid() IS NOT NULL
    AND is_member_of_joint_family(joint_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.joint_family_id = documents.joint_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
    AND (
        uploader_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM family_memberships
            WHERE user_id = auth.uid()
              AND joint_family_id = documents.joint_family_id
              AND role = 'ADMIN'
        )
    )
);

-- Policies for media_contributions
CREATE POLICY "Users can view published media or their own uploads"
ON media_contributions FOR SELECT
USING (
    auth.uid() IS NOT NULL
    AND is_member_of_joint_family(joint_family_id)
    AND (
        status = 'AUTO_PUBLISHED'
        OR uploader_id = auth.uid()
        OR (
            matched_face_ids IS NOT NULL 
            AND jsonb_typeof(matched_face_ids) = 'array' 
            AND matched_face_ids ? auth.uid()::text
        )
    )
);

CREATE POLICY "Users can upload media to their joint family"
ON media_contributions FOR INSERT
WITH CHECK (
    auth.uid() IS NOT NULL
    AND uploader_id = auth.uid()
    AND is_member_of_joint_family(joint_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.joint_family_id = media_contributions.joint_family_id
          AND fm.role IN ('ADMIN', 'MEMBER', 'CHILD')
    )
);

CREATE POLICY "Clan Admins and Members can triage media"
ON media_contributions FOR UPDATE
USING (
    auth.uid() IS NOT NULL
    AND is_member_of_joint_family(joint_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.joint_family_id = media_contributions.joint_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
)
WITH CHECK (
    auth.uid() IS NOT NULL
    AND is_member_of_joint_family(joint_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.joint_family_id = media_contributions.joint_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
);

-- Policies for health_records
CREATE POLICY "Health record visibility policy"
ON health_records FOR SELECT
USING (
    auth.uid() IS NOT NULL
    AND (
        user_id = auth.uid()
        OR is_member_of_nuclear_family(nuclear_family_id)
        OR (is_emergency_visible = TRUE AND are_members_of_same_joint_family(user_id))
    )
);

-- Policies for pets (Nuclear Household Isolation)
CREATE POLICY "Users can view pets in their nuclear family"
ON pets FOR SELECT
USING (
    auth.uid() IS NOT NULL 
    AND is_member_of_nuclear_family(nuclear_family_id)
);

CREATE POLICY "Users can insert pets into their nuclear family"
ON pets FOR INSERT
WITH CHECK (
    auth.uid() IS NOT NULL
    AND is_member_of_nuclear_family(nuclear_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.nuclear_family_id = pets.nuclear_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
);

CREATE POLICY "Users can update pets in their nuclear family"
ON pets FOR UPDATE
USING (
    auth.uid() IS NOT NULL
    AND is_member_of_nuclear_family(nuclear_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.nuclear_family_id = pets.nuclear_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
)
WITH CHECK (
    auth.uid() IS NOT NULL
    AND is_member_of_nuclear_family(nuclear_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.nuclear_family_id = pets.nuclear_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
);

-- Policies for properties (Ancestral Real Estate Isolation)
CREATE POLICY "Users can view properties belonging to their clan"
ON properties FOR SELECT
USING (
    auth.uid() IS NOT NULL 
    AND is_member_of_joint_family(joint_family_id)
);

CREATE POLICY "Clan Admins and Members can manage properties"
ON properties FOR ALL
USING (
    auth.uid() IS NOT NULL
    AND is_member_of_joint_family(joint_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.joint_family_id = properties.joint_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
)
WITH CHECK (
    auth.uid() IS NOT NULL
    AND is_member_of_joint_family(joint_family_id)
    AND EXISTS (
        SELECT 1 FROM family_memberships fm
        WHERE fm.user_id = auth.uid()
          AND fm.joint_family_id = properties.joint_family_id
          AND fm.role IN ('ADMIN', 'MEMBER')
    )
);

-- Policies for audit_logs
CREATE POLICY "Clan Admins can view audit logs"
ON audit_logs FOR SELECT
USING (
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM family_memberships
        WHERE user_id = auth.uid()
          AND joint_family_id = audit_logs.joint_family_id
          AND role = 'ADMIN'
    )
);
