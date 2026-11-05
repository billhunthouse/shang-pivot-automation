"""pgvector 知识库：文档入库、向量检索、FAQ 数据源。"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_DIM = 512
DEFAULT_TABLE = "agent_knowledge_chunk"


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class PgVectorKnowledgeBase:
    """同步 psycopg + 异步包装；Phase-0 单连接即可，生产换连接池。"""

    backend = "pgvector"

    def __init__(
        self,
        dsn: str,
        model_name: str = DEFAULT_MODEL,
        dim: int = DEFAULT_DIM,
        table: str = DEFAULT_TABLE,
    ):
        if not table.replace("_", "").isalnum():
            raise ValueError(f"invalid table name: {table}")
        self.dsn = dsn
        self.model_name = model_name
        self.dim = dim
        self.table = table
        self._embedder = None
        self._embedder_lock = threading.Lock()

    def _get_embedder(self):
        if self._embedder is None:
            with self._embedder_lock:
                if self._embedder is None:
                    from fastembed import TextEmbedding

                    self._embedder = TextEmbedding(self.model_name)
        return self._embedder

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._get_embedder().embed(texts)
        return [vector.tolist() for vector in vectors]

    def _connect(self):
        import psycopg

        return psycopg.connect(self.dsn, connect_timeout=5)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table} (
                        id BIGSERIAL PRIMARY KEY,
                        source TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        content_hash TEXT NOT NULL UNIQUE,
                        embedding vector({self.dim}) NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table}_source_idx ON {self.table} (source)"
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS {self.table}_embedding_idx
                    ON {self.table} USING hnsw (embedding vector_cosine_ops)
                    """
                )

    def count(self) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT count(*) FROM {self.table}")
                return int(cur.fetchone()[0])

    def ingest(self, rows: list[dict[str, Any]]) -> int:
        """按 source 全量替换；title/content/source 相同的块幂等更新。"""
        if not rows:
            return 0
        self.ensure_schema()
        sources = sorted({str(row["source"]) for row in rows})
        vectors = self._embed([f"{row['title']}\n{row['content']}" for row in rows])
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {self.table} WHERE source = ANY(%s)", (sources,))
                cur.executemany(
                    f"""
                    INSERT INTO {self.table} (source, title, content, content_hash, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)
                    ON CONFLICT (content_hash) DO UPDATE SET
                        source = EXCLUDED.source,
                        title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        updated_at = now()
                    """,
                    [
                        (
                            row["source"],
                            row["title"],
                            row["content"],
                            _content_hash(f"{row['source']}\n{row['title']}\n{row['content']}"),
                            _vector_literal(vector),
                        )
                        for row, vector in zip(rows, vectors)
                    ],
                )
        return len(rows)

    def _search_sync(self, query: str, limit: int) -> list[dict[str, Any]]:
        vector = _vector_literal(self._embed([query])[0])
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT source, title, content,
                           1 - (embedding <=> %s::vector) AS score
                    FROM {self.table}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vector, vector, limit),
                )
                return [
                    {
                        "source": row[0],
                        "title": row[1],
                        "content": row[2],
                        "score": round(float(row[3]), 4),
                    }
                    for row in cur.fetchall()
                ]

    async def search(self, query: str, limit: int = 2) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._search_sync, query, limit)


def faq_documents(path: Path, source: str = "faq.json") -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        {
            "source": source,
            "title": row["question"],
            "content": row["answer"],
        }
        for row in rows
    ]


def build_knowledge_base() -> PgVectorKnowledgeBase | None:
    if os.getenv("AGENT_RAG_ENABLED", "0").strip().lower() not in {"1", "true", "yes", "on"}:
        return None
    dsn = os.getenv("AGENT_PG_DSN", "").strip()
    if not dsn:
        raise RuntimeError("AGENT_PG_DSN 未配置")
    return PgVectorKnowledgeBase(
        dsn=dsn,
        model_name=os.getenv("AGENT_EMBEDDING_MODEL", DEFAULT_MODEL),
        dim=int(os.getenv("AGENT_EMBEDDING_DIM", str(DEFAULT_DIM))),
    )
