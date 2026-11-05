#!/usr/bin/env python3
"""把 FAQ 写入 pgvector，并做一次检索自检。"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag import DEFAULT_DIM, DEFAULT_MODEL, PgVectorKnowledgeBase, faq_documents  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=os.getenv("AGENT_PG_DSN", ""))
    parser.add_argument("--model", default=os.getenv("AGENT_EMBEDDING_MODEL", DEFAULT_MODEL))
    parser.add_argument("--dim", type=int, default=int(os.getenv("AGENT_EMBEDDING_DIM", str(DEFAULT_DIM))))
    parser.add_argument("--query", default="退款一般多久到账？")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    if not args.dsn:
        parser.error("请通过 --dsn 或 AGENT_PG_DSN 提供 PostgreSQL 连接串")

    kb = PgVectorKnowledgeBase(args.dsn, model_name=args.model, dim=args.dim)
    kb.ensure_schema()
    rows = faq_documents(ROOT / "data" / "faq.json")
    count = kb.ingest(rows)
    print(f"ingested={count} total={kb.count()}")
    for hit in asyncio.run(kb.search(args.query, args.limit)):
        print(f"{hit['score']:.4f}\t{hit['source']}\t{hit['title']}\t{hit['content']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
