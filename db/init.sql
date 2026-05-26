-- =============================================================================
-- LenzOtica — Schema inicial
-- PostgreSQL 16 + pgvector
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================================================
-- appointments
-- =============================================================================

CREATE TABLE appointments (
    id           SERIAL       PRIMARY KEY,
    phone        TEXT         NOT NULL,
    name         TEXT         NOT NULL,
    date         DATE         NOT NULL,
    time         TIME         NOT NULL,
    status       TEXT         NOT NULL DEFAULT 'scheduled',
    event_id     TEXT         NOT NULL DEFAULT '',
    notes        TEXT         NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    confirmed_at TIMESTAMPTZ,
    attended_at  TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    archived_at  TIMESTAMPTZ,

    CONSTRAINT appointments_status_check CHECK (status IN (
        'scheduled', 'day_reminder_sent', 'reminder_sent', 'response_received',
        'confirmed', 'attended', 'completed', 'no_show', 'cancelled', 'archived'
    ))
);

CREATE INDEX idx_appointments_phone        ON appointments (phone);
CREATE INDEX idx_appointments_status       ON appointments (status);
CREATE INDEX idx_appointments_date_time    ON appointments (date, time);
CREATE INDEX idx_appointments_phone_status ON appointments (phone, status);

-- =============================================================================
-- conversation_history
-- =============================================================================

CREATE TABLE conversation_history (
    id          BIGSERIAL    PRIMARY KEY,
    phone       TEXT         NOT NULL,
    role        TEXT         NOT NULL,
    content     TEXT         NOT NULL,
    token_count INT          NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT history_role_check CHECK (role IN ('user', 'assistant'))
);

CREATE INDEX idx_history_phone      ON conversation_history (phone);
CREATE INDEX idx_history_phone_time ON conversation_history (phone, created_at DESC);

-- =============================================================================
-- pending_items
-- =============================================================================

CREATE TABLE pending_items (
    id           SERIAL       PRIMARY KEY,
    phone        TEXT         NOT NULL,
    description  TEXT         NOT NULL,
    dismissed    BOOLEAN      NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    dismissed_at TIMESTAMPTZ
);

CREATE INDEX idx_pending_dismissed ON pending_items (dismissed);
CREATE INDEX idx_pending_phone     ON pending_items (phone);

-- =============================================================================
-- rag_documents
-- =============================================================================

CREATE TABLE rag_documents (
    id          SERIAL       PRIMARY KEY,
    title       TEXT         NOT NULL,
    source_type TEXT         NOT NULL DEFAULT 'manual',
    content     TEXT         NOT NULL,
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT rag_documents_source_check CHECK (source_type IN (
        'manual', 'faq', 'product_catalog', 'policy', 'script'
    ))
);

CREATE INDEX idx_rag_docs_active ON rag_documents (is_active);
CREATE INDEX idx_rag_docs_type   ON rag_documents (source_type);

-- =============================================================================
-- rag_chunks
-- =============================================================================

CREATE TABLE rag_chunks (
    id          BIGSERIAL    PRIMARY KEY,
    document_id INT          NOT NULL REFERENCES rag_documents (id) ON DELETE CASCADE,
    chunk_index INT          NOT NULL,
    chunk_text  TEXT         NOT NULL,
    embedding   vector(1536) NOT NULL,
    token_count INT          NOT NULL DEFAULT 0,
    metadata    JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- HNSW para busca aproximada por similaridade de cosseno
CREATE INDEX idx_rag_chunks_embedding ON rag_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_rag_chunks_document ON rag_chunks (document_id);

-- =============================================================================
-- rag_config
-- =============================================================================

CREATE TABLE rag_config (
    id                  SERIAL       PRIMARY KEY,
    profile_name        TEXT         NOT NULL UNIQUE,
    is_active           BOOLEAN      NOT NULL DEFAULT false,
    enabled             BOOLEAN      NOT NULL DEFAULT true,

    embed_model         TEXT         NOT NULL DEFAULT 'text-embedding-3-small',
    embed_dims          INT          NOT NULL DEFAULT 1536,

    top_k               INT          NOT NULL DEFAULT 3,
    min_similarity      FLOAT        NOT NULL DEFAULT 0.75,
    max_context_tokens  INT          NOT NULL DEFAULT 800,

    chunk_size          INT          NOT NULL DEFAULT 400,
    chunk_overlap       INT          NOT NULL DEFAULT 80,

    source_types        TEXT[]                DEFAULT NULL,

    description         TEXT         NOT NULL DEFAULT '',
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT rag_config_top_k_check        CHECK (top_k BETWEEN 1 AND 20),
    CONSTRAINT rag_config_similarity_check   CHECK (min_similarity BETWEEN 0.0 AND 1.0),
    CONSTRAINT rag_config_chunk_size_check   CHECK (chunk_size > 0),
    CONSTRAINT rag_config_chunk_overlap_check CHECK (chunk_overlap >= 0 AND chunk_overlap < chunk_size)
);

-- Garante que apenas um perfil esteja ativo por vez
CREATE UNIQUE INDEX idx_rag_config_active ON rag_config (is_active)
    WHERE is_active = true;

INSERT INTO rag_config (profile_name, is_active, description)
VALUES ('default', true, 'Configuração padrão de produção');

-- =============================================================================
-- rag_query_log
-- =============================================================================

CREATE TABLE rag_query_log (
    id              BIGSERIAL    PRIMARY KEY,
    phone           TEXT         NOT NULL,
    query_text      TEXT         NOT NULL,
    chunks_returned INT          NOT NULL DEFAULT 0,
    top_similarity  FLOAT,
    latency_ms      INT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_rag_log_created ON rag_query_log (created_at);
