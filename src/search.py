"""Semantic search over the regulations: the retrieval step of the RAG.

Usage:
    python src/search.py "¿Cuántas horas puede conducir un camionero a la semana?"
    python src/search.py "How long is the daily rest period?" --k 3 --lang en
"""
import argparse
import os
from functools import lru_cache
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
MODEL = "intfloat/multilingual-e5-base"


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL)


def search(question: str, k: int = 5, lang: str | None = None) -> list[dict]:
    """Return the k chunks closest to the question, with a cosine similarity score."""
    load_dotenv(ROOT / ".env")
    q = _model().encode(f"query: {question}", normalize_embeddings=True)
    sql = ("SELECT id, source, lang, article, text, url, 1 - (embedding <=> %(q)s) AS score "
           "FROM chunks {where} ORDER BY embedding <=> %(q)s LIMIT %(k)s")
    where = "WHERE lang = %(lang)s" if lang else ""
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        register_vector(con)
        rows = con.execute(sql.format(where=where), {"q": q, "k": k, "lang": lang}).fetchall()
    cols = ["id", "source", "lang", "article", "text", "url", "score"]
    return [dict(zip(cols, r)) for r in rows]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--lang", choices=["en", "es"])
    args = ap.parse_args()
    for r in search(args.question, args.k, args.lang):
        print(f"{r['score']:.3f}  {r['source']} · {r['article']} [{r['lang']}]")
        print(f"       {r['text'][:160]}...\n")
