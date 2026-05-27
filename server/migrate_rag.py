import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import db


def run():
    print("[MIGRATE RAG] Iniciando...")

    # 1. system_prompt na rag_config
    try:
        db.execute("ALTER TABLE rag_config ADD COLUMN system_prompt TEXT NOT NULL DEFAULT ''")
        print("[MIGRATE RAG] Coluna system_prompt adicionada")
    except Exception:
        print("[MIGRATE RAG] system_prompt ja existe, pulando")

    # 2. Tabela business_hours
    db.execute("""
        CREATE TABLE IF NOT EXISTS business_hours (
            day_of_week  INT     PRIMARY KEY,
            is_open      BOOLEAN NOT NULL DEFAULT false,
            is_flexible  BOOLEAN NOT NULL DEFAULT false,
            open_time    TIME,
            close_time   TIME
        )
    """)
    count = db.fetchval("SELECT COUNT(*) FROM business_hours")
    if not count:
        # 0=Seg 1=Ter 2=Qua 3=Qui 4=Sex 5=Sab 6=Dom
        defaults = [
            (0, True,  False, "09:00", "18:00"),
            (1, False, True,  None,    None),
            (2, True,  False, "09:00", "12:00"),
            (3, True,  False, "09:00", "12:00"),
            (4, True,  False, "09:00", "18:00"),
            (5, False, True,  None,    None),
            (6, False, False, None,    None),
        ]
        for row in defaults:
            db.execute(
                "INSERT INTO business_hours VALUES (%s,%s,%s,%s,%s)",
                row
            )
        print("[MIGRATE RAG] Horarios padrao inseridos")
    else:
        print("[MIGRATE RAG] business_hours ja preenchida, pulando")

    # 3. rag_chunks: vector(1536) -> vector(384) para sentence-transformers
    current = db.fetchval("""
        SELECT a.atttypmod FROM pg_attribute a
        JOIN pg_type t ON a.atttypid = t.oid
        WHERE a.attrelid = 'rag_chunks'::regclass
        AND a.attname = 'embedding'
    """)
    # pgvector armazena dims diretamente em atttypmod
    if current == 1536:
        db.execute("DROP INDEX IF EXISTS idx_rag_chunks_embedding")
        db.execute("DELETE FROM rag_chunks")
        db.execute("ALTER TABLE rag_chunks ALTER COLUMN embedding TYPE vector(384)")
        db.execute("""
            CREATE INDEX idx_rag_chunks_embedding ON rag_chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        print("[MIGRATE RAG] rag_chunks migrado vector(1536) -> vector(384)")
    else:
        print(f"[MIGRATE RAG] rag_chunks ja em vector(384) (atttypmod={current})")

    # 4. Atualiza modelo padrao no rag_config
    db.execute("""
        UPDATE rag_config
        SET embed_model = 'paraphrase-multilingual-MiniLM-L12-v2', embed_dims = 384
        WHERE embed_model = 'text-embedding-3-small'
    """)

    print("[MIGRATE RAG] Concluido!")


if __name__ == "__main__":
    run()
