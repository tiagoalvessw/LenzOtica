# Fluxo de Dados e Estrutura do Banco de Dados — LenzOtica

## Visão Geral da Arquitetura

```
WhatsApp (cliente)
      │
      ▼
Evolution API  ──webhook──►  FastAPI (main.py)
                                    │
                    ┌───────────────┼───────────────────┐
                    ▼               ▼                   ▼
              ai.py (LLM)    appointments.py       pending.py
              sessions        (agendamentos)      (pendências)
                    │               │                   │
                    └───────────────┴───────────────────┘
                                    │
                                    ▼
                           PostgreSQL + pgvector
                        ┌──────────────────────────┐
                        │  appointments             │
                        │  conversation_history     │
                        │  pending_items            │
                        │  rag_documents            │
                        │  rag_chunks               │
                        │  rag_config               │
                        └──────────────────────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                  Google Calendar         Painel Web
                  (calendar_service)      (panel.py)
```

---

## 1. Fluxo de Dados Detalhado

### 1.1 Recebimento de Mensagem (Webhook)

```
Cliente envia mensagem no WhatsApp
        │
        ▼
Evolution API dispara POST /webhook
        │
        ▼
main.py verifica:
  ├── É mensagem duplicada? → ignora (dedup em memória, TTL 30s)
  ├── É fromMe (enviada pelo bot)? → ignora
  ├── É mídia (áudio, imagem, vídeo)? → resposta padrão
  ├── Tem lembrete pendente? → fluxo de confirmação/cancelamento
  └── É texto normal? → continua
        │
        ▼
mark_response_received(sender)  [atualiza status no banco]
        │
        ▼
get_response(sender, text)  [ai.py]
  ├── Carrega histórico: conversation_history WHERE phone = sender
  ├── Carrega horários livres: appointments WHERE status NOT IN (...)
  ├── Monta system_prompt + contexto dinâmico
  ├── _trim_history() — remove mensagens antigas se exceder token budget
  ├── Chama LLM (Groq ou Ollama)
  │     ├── RAG: busca chunks relevantes via pgvector antes de montar o prompt
  │     │         SELECT ... ORDER BY embedding <=> query_embedding LIMIT k
  │     └── Retorna resposta com possíveis marcadores [AGENDAR:...] [PENDENTE:...]
  └── Salva histórico: INSERT INTO conversation_history
        │
        ▼
main.py processa marcadores:
  ├── [AGENDAR:NOME|DATA|HORA]
  │     ├── Cancela agendamento anterior ativo (se houver)
  │     ├── create_event() → Google Calendar
  │     ├── add_appointment() → INSERT INTO appointments
  │     └── Envia confirmação ao cliente via Evolution API
  ├── [PENDENTE:descrição]
  │     └── INSERT INTO pending_items
  └── [BREAK] → split em múltiplas mensagens com delay de digitação
```

### 1.2 Scheduler (loop a cada 60s)

```
scheduler_loop() — roda em background
        │
        ├── check_day_reminders()
        │     SELECT * FROM appointments
        │     WHERE status = 'scheduled'
        │       AND appointment_datetime BETWEEN now()+23h AND now()+24h
        │     → envia lembrete de 24h → UPDATE status = 'day_reminder_sent'
        │
        ├── check_reminders()
        │     SELECT * FROM appointments
        │     WHERE status IN ('scheduled','day_reminder_sent')
        │       AND appointment_datetime BETWEEN now()+55min AND now()+65min
        │     → envia lembrete de 1h → UPDATE status = 'reminder_sent'
        │
        ├── check_cancellations()
        │     SELECT * FROM appointments
        │     WHERE status = 'reminder_sent'
        │       AND appointment_datetime <= now()
        │     → cancela por falta de confirmação → UPDATE status = 'cancelled'
        │
        └── check_no_shows()
              SELECT * FROM appointments
              WHERE status = 'confirmed'
                AND appointment_datetime <= now() - interval '30 min'
              → marca falta → UPDATE status = 'no_show'
```

### 1.3 Fluxo RAG (Retrieval-Augmented Generation)

```
Pergunta do cliente
        │
        ▼
Gerar embedding da pergunta
  embed(text) → vector[1536]
        │
        ▼
Busca vetorial no PostgreSQL
  SELECT chunk_text, metadata
  FROM rag_chunks
  ORDER BY embedding <=> $query_vector
  LIMIT rag_config.top_k
  WHERE similarity > rag_config.min_similarity
        │
        ▼
Injetar chunks relevantes no system_prompt
  "Contexto adicional:\n{chunk1}\n{chunk2}..."
        │
        ▼
LLM gera resposta com base no contexto recuperado
```

---

## 2. Estrutura do Banco de Dados

### Setup Inicial

```sql
-- Extensão vetorial
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- busca textual auxiliar
```

---

### 2.1 Tabela `appointments`

Substitui `appointments.json`. Registro completo do ciclo de vida de cada consulta.

```sql
CREATE TABLE appointments (
    id              SERIAL PRIMARY KEY,
    phone           TEXT        NOT NULL,           -- ex: 5548999990000@s.whatsapp.net
    name            TEXT        NOT NULL,
    date            DATE        NOT NULL,
    time            TIME        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'scheduled',
    event_id        TEXT        NOT NULL DEFAULT '', -- ID no Google Calendar
    notes           TEXT        NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at    TIMESTAMPTZ,
    attended_at     TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    archived_at     TIMESTAMPTZ
);

-- Índices para queries frequentes do scheduler
CREATE INDEX idx_appointments_phone        ON appointments(phone);
CREATE INDEX idx_appointments_status       ON appointments(status);
CREATE INDEX idx_appointments_date_time    ON appointments(date, time);
CREATE INDEX idx_appointments_phone_status ON appointments(phone, status);

-- Status válidos:
-- scheduled | day_reminder_sent | reminder_sent | response_received
-- confirmed | attended | completed | no_show | cancelled | archived
```

---

### 2.2 Tabela `conversation_history`

Substitui `sessions.json`. Histórico de mensagens por número de telefone.

```sql
CREATE TABLE conversation_history (
    id          BIGSERIAL   PRIMARY KEY,
    phone       TEXT        NOT NULL,
    role        TEXT        NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT        NOT NULL,
    token_count INT         NOT NULL DEFAULT 0,  -- cache para _trim_history()
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_history_phone      ON conversation_history(phone);
CREATE INDEX idx_history_phone_time ON conversation_history(phone, created_at DESC);

-- Política de retenção: mensagens com mais de 30 dias podem ser apagadas
-- DELETE FROM conversation_history
-- WHERE created_at < now() - interval '30 days'
--   AND phone NOT IN (SELECT phone FROM appointments WHERE status NOT IN ('archived','completed'));
```

---

### 2.3 Tabela `pending_items`

Substitui `pending.json`. Itens que precisam de atenção humana.

```sql
CREATE TABLE pending_items (
    id          SERIAL      PRIMARY KEY,
    phone       TEXT        NOT NULL,
    description TEXT        NOT NULL,
    dismissed   BOOLEAN     NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    dismissed_at TIMESTAMPTZ
);

CREATE INDEX idx_pending_dismissed ON pending_items(dismissed);
CREATE INDEX idx_pending_phone     ON pending_items(phone);
```

---

### 2.4 Tabela `rag_documents`

Documentos fonte para o RAG (FAQs, políticas, catálogo de produtos, scripts).

```sql
CREATE TABLE rag_documents (
    id          SERIAL      PRIMARY KEY,
    title       TEXT        NOT NULL,
    source_type TEXT        NOT NULL DEFAULT 'manual',
    -- 'manual' | 'faq' | 'product_catalog' | 'policy' | 'script'
    content     TEXT        NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rag_docs_active ON rag_documents(is_active);
CREATE INDEX idx_rag_docs_type   ON rag_documents(source_type);
```

---

### 2.5 Tabela `rag_chunks`

Fragmentos dos documentos com seus embeddings vetoriais.

```sql
CREATE TABLE rag_chunks (
    id           BIGSERIAL   PRIMARY KEY,
    document_id  INT         NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    chunk_index  INT         NOT NULL,            -- posição do chunk no documento
    chunk_text   TEXT        NOT NULL,
    embedding    vector(1536) NOT NULL,           -- OpenAI text-embedding-3-small
    -- Para Ollama local (nomic-embed-text): vector(768)
    token_count  INT         NOT NULL DEFAULT 0,
    metadata     JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índice HNSW para busca aproximada de vizinhos (melhor performance em produção)
CREATE INDEX idx_rag_chunks_embedding ON rag_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Índice IVFFlat alternativo (menor memória, mais lento na construção)
-- CREATE INDEX idx_rag_chunks_embedding ON rag_chunks
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

CREATE INDEX idx_rag_chunks_document ON rag_chunks(document_id);
```

---

### 2.6 Tabela `rag_config`

Configuração do RAG editável sem alterar código. Suporta múltiplos perfis.

```sql
CREATE TABLE rag_config (
    id              SERIAL      PRIMARY KEY,
    profile_name    TEXT        NOT NULL UNIQUE DEFAULT 'default',
    is_active       BOOLEAN     NOT NULL DEFAULT false,
    enabled         BOOLEAN     NOT NULL DEFAULT true,

    -- Modelo de embedding
    embed_model     TEXT        NOT NULL DEFAULT 'text-embedding-3-small',
    embed_dims      INT         NOT NULL DEFAULT 1536,
    -- Para Ollama: 'nomic-embed-text', dims=768

    -- Parâmetros de recuperação
    top_k           INT         NOT NULL DEFAULT 3,       -- nº de chunks retornados
    min_similarity  FLOAT       NOT NULL DEFAULT 0.75,    -- limiar de relevância (cosine)
    max_context_tokens INT      NOT NULL DEFAULT 800,     -- limite de tokens injetados

    -- Parâmetros de chunking (para indexação de novos documentos)
    chunk_size      INT         NOT NULL DEFAULT 400,     -- chars por chunk
    chunk_overlap   INT         NOT NULL DEFAULT 80,      -- sobreposição entre chunks

    -- Filtros
    source_types    TEXT[]      DEFAULT NULL,             -- NULL = todos os tipos
    -- Ex: ARRAY['faq','policy'] para restringir a FAQs e políticas

    -- Metadados
    description     TEXT        NOT NULL DEFAULT '',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Garantir exatamente um perfil ativo
CREATE UNIQUE INDEX idx_rag_config_active ON rag_config(is_active)
    WHERE is_active = true;

-- Perfil padrão
INSERT INTO rag_config (profile_name, is_active, description)
VALUES ('default', true, 'Configuração padrão de produção');
```

---

### 2.7 Tabela `rag_query_log`

Log de buscas RAG para diagnóstico e melhoria contínua.

```sql
CREATE TABLE rag_query_log (
    id              BIGSERIAL   PRIMARY KEY,
    phone           TEXT        NOT NULL,
    query_text      TEXT        NOT NULL,
    chunks_returned INT         NOT NULL,
    top_similarity  FLOAT,
    latency_ms      INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Manter apenas 90 dias de log
CREATE INDEX idx_rag_log_created ON rag_query_log(created_at);
```

---

## 3. Queries Principais

### Busca RAG

```sql
-- Buscar os top_k chunks mais relevantes para uma query
SELECT
    rc.chunk_text,
    rc.metadata,
    rd.title,
    rd.source_type,
    1 - (rc.embedding <=> $1::vector) AS similarity
FROM rag_chunks rc
JOIN rag_documents rd ON rd.id = rc.document_id
WHERE rd.is_active = true
  AND (
    -- respeitar filtro de source_types se configurado
    (SELECT source_types FROM rag_config WHERE is_active = true) IS NULL
    OR rd.source_type = ANY((SELECT source_types FROM rag_config WHERE is_active = true))
  )
  AND 1 - (rc.embedding <=> $1::vector) >= (
    SELECT min_similarity FROM rag_config WHERE is_active = true
  )
ORDER BY rc.embedding <=> $1::vector
LIMIT (SELECT top_k FROM rag_config WHERE is_active = true);
```

### Histórico de conversa com limite de tokens

```sql
-- Carregar as últimas N mensagens que cabem no budget de tokens
WITH ranked AS (
    SELECT
        id, role, content, token_count,
        SUM(token_count) OVER (ORDER BY created_at DESC) AS cumulative_tokens
    FROM conversation_history
    WHERE phone = $1
)
SELECT id, role, content
FROM ranked
WHERE cumulative_tokens <= $2   -- $2 = token budget disponível
ORDER BY id ASC;
```

### Agendamentos do scheduler (lembrete de 1h)

```sql
SELECT phone, name, date, time
FROM appointments
WHERE status IN ('scheduled', 'day_reminder_sent')
  AND (date + time)::timestamptz
      BETWEEN now() + interval '55 minutes'
          AND now() + interval '65 minutes';
```

### Horários ocupados para o contexto da IA

```sql
SELECT date, time
FROM appointments
WHERE status NOT IN ('cancelled', 'no_show', 'completed', 'archived')
  AND date >= CURRENT_DATE
  AND date <= CURRENT_DATE + 5;
```

---

## 4. Configuração de Ambiente

Variáveis adicionais para o PostgreSQL (acrescentar ao `server/.env`):

```env
# PostgreSQL principal (painel + RAG + histórico)
DATABASE_URL=postgresql://lenz:senha_forte@localhost:5432/lenzdb

# Embedding (escolher um)
OPENAI_API_KEY=sk-...           # produção — text-embedding-3-small
# EMBED_MODEL_LOCAL=nomic-embed-text  # desenvolvimento — via Ollama
```

---

## 5. Docker Compose Atualizado

```yaml
services:
  postgres-lenz:
    image: pgvector/pgvector:pg16   # imagem oficial com pgvector pré-instalado
    container_name: lenz-postgres
    restart: always
    environment:
      POSTGRES_DB: lenzdb
      POSTGRES_USER: lenz
      POSTGRES_PASSWORD: senha_forte
    volumes:
      - lenz_pg_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql  # executa na 1ª subida
    ports:
      - "5433:5432"   # 5433 para não conflitar com o postgres da Evolution API

  postgres-evolution:
    image: postgres:15
    container_name: evolution-postgres
    restart: always
    environment:
      POSTGRES_DB: evolution
      POSTGRES_USER: evolution
      POSTGRES_PASSWORD: evolution123
    volumes:
      - evolution_pg_data:/var/lib/postgresql/data

  evolution-api:
    image: evolution-api:local
    container_name: evolution-api
    restart: always
    ports:
      - "8080:8080"
    environment:
      - AUTHENTICATION_API_KEY=lenz-otica-key-2024
      - DATABASE_ENABLED=true
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://evolution:evolution123@postgres-evolution:5432/evolution
      - CACHE_LOCAL_ENABLED=true
      - NODE_OPTIONS=--require /tmp/patch-os.js
    volumes:
      - evolution_data:/evolution/instances
      - ./patch-os.js:/tmp/patch-os.js
    depends_on:
      - postgres-evolution

volumes:
  lenz_pg_data:
  evolution_pg_data:
  evolution_data:
```

---

## 6. Ciclo de Vida de um Agendamento

```
[scheduled]
    │
    ├─ (24h antes) ──► [day_reminder_sent]
    │                       │
    │                       ▼
    └───────────────► [reminder_sent]  ◄── (1h antes)
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
         [confirmed]    [cancelled]    (sem resposta
              │          (auto após      → também
              │           horário)        cancelled)
              │
    ┌─────────┴──────────┐
    ▼                    ▼
[attended]           [no_show]
    │                    │
    ▼                    ▼
[completed]         (admin pode
    │                reagendar)
    ▼
[archived]
```

---

## 7. Estrutura de Pastas com o Banco

```
lenz-otica/
├── docker-compose.yml          # dois postgres: lenz + evolution
├── db/
│   └── init.sql                # CREATE EXTENSION + CREATE TABLE (todo o schema)
├── server/
│   ├── .env                    # inclui DATABASE_URL
│   ├── db.py                   # pool de conexões (asyncpg ou psycopg3)
│   ├── ai.py                   # get_response() — lê histórico do banco
│   ├── appointments.py         # CRUD → banco (substituindo JSON)
│   ├── pending.py              # CRUD → banco
│   ├── rag.py                  # embed() + search_chunks() + index_document()
│   ├── main.py                 # FastAPI + scheduler
│   ├── panel.py                # render_panel()
│   └── calendar_service.py     # Google Calendar
└── DATABASE.md                 # este arquivo
```

---

## 8. Indexação de Documentos RAG

Fluxo para adicionar um novo documento ao RAG:

```python
# rag.py — pseudocódigo do pipeline de indexação

async def index_document(title: str, content: str, source_type: str):
    cfg = await get_active_config()          # lê rag_config WHERE is_active=true

    # 1. Salvar documento
    doc_id = await db.fetchval(
        "INSERT INTO rag_documents(title, content, source_type) VALUES($1,$2,$3) RETURNING id",
        title, content, source_type
    )

    # 2. Chunking
    chunks = split_text(content, cfg.chunk_size, cfg.chunk_overlap)

    # 3. Embeddings em batch
    embeddings = await embed_batch([c.text for c in chunks], model=cfg.embed_model)

    # 4. Inserir chunks
    await db.executemany(
        """INSERT INTO rag_chunks(document_id, chunk_index, chunk_text, embedding, token_count)
           VALUES($1, $2, $3, $4, $5)""",
        [(doc_id, i, c.text, emb, c.tokens) for i, (c, emb) in enumerate(zip(chunks, embeddings))]
    )
```

---

## 9. Considerações de Performance

| Cenário | Índice usado | Latência esperada |
|---|---|---|
| Busca RAG (top_k=3) | HNSW cosine | < 20ms |
| Histórico por telefone | `idx_history_phone_time` | < 5ms |
| Scheduler (agendamentos) | `idx_appointments_status` | < 10ms |
| Painel (listar ativos) | `idx_appointments_date_time` | < 10ms |

> Com até ~10.000 chunks no RAG, o índice HNSW com `m=16` oferece recall >95% e é recomendado sobre IVFFlat para este volume.
