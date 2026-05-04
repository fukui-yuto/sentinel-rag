-- =============================================================================
-- Sentinel RAG Platform - Database Initialization
-- =============================================================================
-- Executed on first container start via docker-entrypoint-initdb.d

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- Tenants
-- =============================================================================
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    max_storage_bytes BIGINT NOT NULL DEFAULT 53687091200, -- 50GB
    max_documents INT NOT NULL DEFAULT 10000,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);

-- =============================================================================
-- Users
-- =============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(255),  -- SSO subject ID
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user'
        CHECK (role IN ('system_admin', 'tenant_admin', 'content_manager', 'user', 'auditor', 'read_only')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_external_id ON users(external_id);

-- =============================================================================
-- Documents
-- =============================================================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    filename VARCHAR(500) NOT NULL,
    original_path VARCHAR(1000),
    mime_type VARCHAR(255),
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    file_hash VARCHAR(128) NOT NULL,     -- SHA-256
    minio_bucket VARCHAR(255) NOT NULL,
    minio_key VARCHAR(1000) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'indexed', 'failed', 'deleted')),
    sensitivity VARCHAR(50) NOT NULL DEFAULT 'internal'
        CHECK (sensitivity IN ('public', 'internal', 'confidential', 'restricted')),
    chunk_count INT NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}',
    error_message TEXT,
    deleted_at TIMESTAMPTZ,              -- soft delete
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_sensitivity ON documents(sensitivity);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);
CREATE INDEX idx_documents_deleted_at ON documents(deleted_at) WHERE deleted_at IS NOT NULL;

-- =============================================================================
-- Document Chunks (metadata only; vectors in Qdrant)
-- =============================================================================
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    token_count INT NOT NULL DEFAULT 0,
    qdrant_point_id UUID NOT NULL,       -- reference to Qdrant vector
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_tenant_id ON document_chunks(tenant_id);
CREATE INDEX idx_chunks_qdrant_point_id ON document_chunks(qdrant_point_id);

-- =============================================================================
-- QA History
-- =============================================================================
CREATE TABLE qa_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    answer TEXT,
    sources JSONB NOT NULL DEFAULT '[]',
    llm_provider VARCHAR(50),
    llm_model VARCHAR(100),
    token_usage JSONB NOT NULL DEFAULT '{}',
    duration_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_qa_history_tenant_id ON qa_history(tenant_id);
CREATE INDEX idx_qa_history_user_id ON qa_history(user_id);
CREATE INDEX idx_qa_history_created_at ON qa_history(created_at);

-- =============================================================================
-- Audit Log (with hash chain for tamper detection)
-- =============================================================================
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    category VARCHAR(50) NOT NULL
        CHECK (category IN ('auth', 'authz', 'data_access', 'data_change', 'system', 'security')),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB NOT NULL DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    result VARCHAR(20) NOT NULL DEFAULT 'success'
        CHECK (result IN ('success', 'failure', 'denied')),
    previous_hash VARCHAR(64),           -- SHA-256 of previous record
    record_hash VARCHAR(64) NOT NULL,    -- SHA-256 of this record
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_category ON audit_logs(category);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- =============================================================================
-- LLM Provider Configuration
-- =============================================================================
CREATE TABLE llm_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    provider_type VARCHAR(50) NOT NULL
        CHECK (provider_type IN ('anthropic', 'openai', 'google', 'ollama')),
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    -- API key encrypted with pgcrypto (stored as bytea)
    api_key_encrypted BYTEA,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- Sync Configuration (per tenant)
-- =============================================================================
CREATE TABLE sync_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    watch_path VARCHAR(1000) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    auto_sensitivity VARCHAR(50) NOT NULL DEFAULT 'internal',
    file_patterns JSONB NOT NULL DEFAULT '["*"]',
    exclude_patterns JSONB NOT NULL DEFAULT '[]',
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, watch_path)
);

-- =============================================================================
-- Row Level Security (RLS)
-- =============================================================================

-- Enable RLS on tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE qa_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_configs ENABLE ROW LEVEL SECURITY;

-- Application role for API connections
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN;
    END IF;
END $$;

-- Grant permissions to app_user
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;

-- RLS Policies: tenant isolation via session variable 'app.current_tenant_id'
-- The application sets this at the start of each request.

-- Users
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
CREATE POLICY tenant_isolation_users_insert ON users
    FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Documents
CREATE POLICY tenant_isolation_documents ON documents
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
CREATE POLICY tenant_isolation_documents_insert ON documents
    FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Document Chunks
CREATE POLICY tenant_isolation_chunks ON document_chunks
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
CREATE POLICY tenant_isolation_chunks_insert ON document_chunks
    FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- QA History
CREATE POLICY tenant_isolation_qa ON qa_history
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
CREATE POLICY tenant_isolation_qa_insert ON qa_history
    FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Sync Configs
CREATE POLICY tenant_isolation_sync ON sync_configs
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
CREATE POLICY tenant_isolation_sync_insert ON sync_configs
    FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Audit logs: no RLS for app_user (system_admin / auditor access via API-level filtering)
-- Tenants table: no RLS (managed by system_admin via API)

-- =============================================================================
-- Updated_at trigger
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_llm_providers_updated_at BEFORE UPDATE ON llm_providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_sync_configs_updated_at BEFORE UPDATE ON sync_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- Seed: default tenant and system admin (change password on first login)
-- =============================================================================
INSERT INTO tenants (id, name, slug) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Default', 'default');

INSERT INTO users (tenant_id, email, display_name, role) VALUES
    ('00000000-0000-0000-0000-000000000001', 'admin@sentinel.local', 'System Administrator', 'system_admin');

-- Seed LLM providers (disabled by default)
INSERT INTO llm_providers (name, display_name, provider_type, is_enabled) VALUES
    ('anthropic', 'Anthropic (Claude)', 'anthropic', false),
    ('openai', 'OpenAI', 'openai', false),
    ('google', 'Google (Gemini)', 'google', false),
    ('ollama', 'Ollama (Local)', 'ollama', true);
