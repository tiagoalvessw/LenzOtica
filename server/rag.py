import time
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import db

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"[RAG] Carregando modelo '{_MODEL_NAME}'...")
        _model = SentenceTransformer(_MODEL_NAME)
        print("[RAG] Modelo carregado")
    return _model


def embed(text: str) -> list:
    vec = _get_model().encode(text, convert_to_numpy=True)
    return vec.tolist()


def _vec_str(vec: list) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def split_chunks(text: str, chunk_size: int = 400, overlap: int = 80) -> list:
    words = text.split()
    chunks = []
    i = 0
    step = max(1, chunk_size - overlap)
    while i < len(words):
        chunk = " ".join(words[i: i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += step
    return chunks


def get_config() -> dict:
    row = db.fetchone("SELECT * FROM rag_config WHERE is_active = true")
    if not row:
        return {
            "enabled": False,
            "top_k": 3,
            "min_similarity": 0.75,
            "max_context_tokens": 800,
            "chunk_size": 400,
            "chunk_overlap": 80,
        }
    return dict(row)


def index_document(doc_id: int) -> int:
    """Divide e embeda o documento, salva chunks. Retorna quantidade de chunks."""
    doc = db.fetchone(
        "SELECT id, content FROM rag_documents WHERE id = %s", (doc_id,)
    )
    if not doc:
        raise ValueError(f"Documento {doc_id} nao encontrado")

    cfg = get_config()
    chunk_size = cfg.get("chunk_size", 400)
    chunk_overlap = cfg.get("chunk_overlap", 80)

    db.execute("DELETE FROM rag_chunks WHERE document_id = %s", (doc_id,))

    chunks = split_chunks(doc["content"], chunk_size, chunk_overlap)
    for i, chunk_text in enumerate(chunks):
        vec = embed(chunk_text)
        token_count = max(1, len(chunk_text) // 4)
        db.execute(
            """
            INSERT INTO rag_chunks (document_id, chunk_index, chunk_text, embedding, token_count)
            VALUES (%s, %s, %s, %s::vector, %s)
            """,
            (doc_id, i, chunk_text, _vec_str(vec), token_count),
        )

    return len(chunks)


def retrieve(query_text: str, phone: str) -> list:
    """Busca chunks relevantes para a query. Retorna lista de textos."""
    cfg = get_config()
    if not cfg.get("enabled", False):
        return []

    # Evita carregar o modelo se não há documentos ativos
    has_docs = db.fetchval(
        "SELECT EXISTS(SELECT 1 FROM rag_documents WHERE is_active = true)"
    )
    if not has_docs:
        return []

    t0 = time.time()
    query_vec = embed(query_text)
    vec_s = _vec_str(query_vec)

    top_k = cfg.get("top_k", 3)
    min_sim = cfg.get("min_similarity", 0.75)

    rows = db.fetchall(
        """
        SELECT c.chunk_text,
               1 - (c.embedding <=> %s::vector) AS similarity
        FROM rag_chunks c
        JOIN rag_documents d ON c.document_id = d.id
        WHERE d.is_active = true
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
        """,
        (vec_s, vec_s, top_k),
    )

    chunks = [r["chunk_text"] for r in rows if (r["similarity"] or 0) >= min_sim]
    top_sim = rows[0]["similarity"] if rows else None
    latency = int((time.time() - t0) * 1000)

    try:
        db.execute(
            """
            INSERT INTO rag_query_log (phone, query_text, chunks_returned, top_similarity, latency_ms)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (phone, query_text[:500], len(chunks), top_sim, latency),
        )
    except Exception as e:
        print(f"[RAG] Erro ao logar query: {e}")

    return chunks
