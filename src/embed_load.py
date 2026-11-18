"""Embed every chunk and load it into Postgres + pgvector.

Usage (from the project root, with the database running: docker compose up -d):
    python src/embed_load.py

Embedding model: intfloat/multilingual-e5-base (free, runs locally, Spanish and
English in the same vector space, 768 dimensions). The first run downloads the
model (~1 GB). e5 models expect the prefixes "passage: " for documents and
"query: " for questions.
"""
import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
MODEL = "intfloat/multilingual-e5-base"
DIM = 768

SCHEMA = f"""
CREATE EXTENSION IF NOT EXISTS vector;
DROP TABLE IF EXISTS chunks;
CREATE TABLE chunks (
    id         text PRIMARY KEY,
    source_id  text NOT NULL,
    source     text NOT NULL,
    lang       text NOT NULL,
    article    text NOT NULL,
    text       text NOT NULL,
    url        text NOT NULL,
    embedding  vector({DIM}) NOT NULL
);
"""
# HNSW index for fast approximate nearest-neighbour search with cosine distance
INDEX = "CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);"


def main() -> None:
    load_dotenv(ROOT / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
    if not CHUNKS.exists():
        sys.exit("Missing chunks.jsonl. Run python src/parse.py first.")

    chunks = [json.loads(line) for line in CHUNKS.open(encoding="utf-8")]
    print(f"Embedding {len(chunks)} chunks with {MODEL} ...")
    model = SentenceTransformer(MODEL)
    # Prepend the article label so the vector also captures what the article is about
    texts = [f"passage: {c['source']} {c['article']}\n{c['text']}" for c in chunks]
    vectors = model.encode(texts, batch_size=16, normalize_embeddings=True, show_progress_bar=True)

    with psycopg.connect(url, autocommit=True) as con:
        con.execute(SCHEMA)
        register_vector(con)
        with con.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (id, source_id, source, lang, article, text, url, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                [(c["id"], c["source_id"], c["source"], c["lang"], c["article"], c["text"], c["url"], v)
                 for c, v in zip(chunks, vectors)],
            )
        con.execute(INDEX)
        n = con.execute("SELECT count(*) FROM chunks").fetchone()[0]
    print(f"Loaded {n} chunks into the chunks table.")


if __name__ == "__main__":
    main()
