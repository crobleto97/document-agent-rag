"""Split each downloaded regulation into one chunk per article.

Usage (from the project root, after src/download.py):
    python src/parse.py

Output: data/processed/chunks.jsonl, one JSON object per chunk:
    id, source_id, source, lang, article, text, url

Articles are the natural unit of a legal text: a question is usually answered by one
article, and citing "Article 7 of Regulation 561/2006" is what a user needs.
Articles longer than MAX_CHARS are split on paragraph boundaries into parts that
keep the article number, so the embedding model never truncates them.
"""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from sources import SOURCES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "chunks.jsonl"
MAX_CHARS = 1800  # ~450 tokens, inside the 512-token limit of the embedding model

ARTICLE_RE = re.compile(r"^(Article|Artículo)\s+\d+(\s*(bis|ter|quater|[a-z]))?$", re.IGNORECASE)
END_RE = re.compile(r"^(ANNEX|ANEXO)\b", re.IGNORECASE)


def clean(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[▼►◄]\s*[A-Z]\d*", "", text)  # consolidation markers like ▼M4
    return re.sub(r"\s+", " ", text).strip()


def eurlex_articles(html: str) -> list[tuple[str, list[str]]]:
    """Return [(article label, [paragraphs])] from a EUR-Lex HTML page."""
    soup = BeautifulSoup(html, "lxml")

    # Consolidated texts wrap each article in <div class="eli-subdivision" id="art_N">
    divs = soup.select('div.eli-subdivision[id^="art_"]')
    if divs:
        out = []
        for d in divs:
            title = d.find("p", class_="title-article-norm")
            paras = [clean(p.get_text(" ")) for p in d.find_all("p")
                     if p is not title and "modref" not in (p.get("class") or [])]
            out.append((clean(title.get_text(" ")), [p for p in paras if p]))
        return out

    # Original Official Journal texts: a flat run of <p>; "Article N" starts an article
    out, label, paras = [], None, []
    body = soup.find(id="TexteOnly") or soup
    for p in body.find_all("p"):
        t = clean(p.get_text(" "))
        if not t:
            continue
        if END_RE.match(t) or t.startswith("Done at") or t.startswith("Hecho en"):
            break
        if ARTICLE_RE.match(t):
            if label:
                out.append((label, paras))
            label, paras = t, []
        elif label:
            paras.append(t)
    if label:
        out.append((label, paras))
    return out


def boe_articles(xml: bytes) -> list[tuple[str, list[str]]]:
    """Return [(article label, [paragraphs])] from the BOE consolidated-text API."""
    soup = BeautifulSoup(xml, "lxml-xml")
    out = []
    for b in soup.find_all("bloque", attrs={"tipo": "precepto"}):
        version = b.find_all("version")[-1]  # the version in force today
        paras = [clean(p.get_text(" ")) for p in version.find_all("p", recursive=False)]
        paras = [p for p in paras if p]
        if paras and paras[0].lower().startswith(("artículo", "disposición")):
            label = paras[0]          # e.g. "Artículo 47. Supuestos de responsabilidad."
            paras = paras[1:]
        else:
            label = b.get("titulo")
        if paras:
            out.append((label, paras))
    return out


def article_key(label: str) -> str:
    """Stable id part for an article label: "Article 9a" -> "9a", "Artículo 9 bis" -> "9bis".

    Amended EU texts insert articles with a letter (EN "9a") or a Latin suffix (ES "9 bis");
    both must stay distinct from the plain article or their ids collide.
    """
    num = re.search(r"\d+(?:\s*(?:bis|ter|quater)\b|[a-z]\b)?", label, re.IGNORECASE)
    if num:
        return num.group(0).replace(" ", "").lower()
    return re.sub(r"\W+", "_", label)[:40]


def split_long(paras: list[str]) -> list[str]:
    parts, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > MAX_CHARS:
            parts.append(cur)
            cur = ""
        cur = f"{cur}\n{p}" if cur else p
    if cur:
        parts.append(cur)
    return parts


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    total, seen = 0, set()
    with OUT.open("w", encoding="utf-8") as f:
        for src in SOURCES:
            for lang, url in src["versions"].items():
                ext = "xml" if src["format"] == "boe" else "html"
                path = RAW / f"{src['id']}.{lang}.{ext}"
                if not path.exists():
                    sys.exit(f"Missing {path.name}. Run python src/download.py first.")
                if src["format"] == "boe":
                    arts = boe_articles(path.read_bytes())
                else:
                    arts = eurlex_articles(path.read_text(encoding="utf-8"))
                n = 0
                for label, paras in arts:
                    art_key = article_key(label)
                    parts = split_long(paras)
                    for i, text in enumerate(parts, 1):
                        suffix = f"_p{i}" if len(parts) > 1 else ""
                        chunk_id = f"{src['id']}.{lang}.art{art_key}{suffix}"
                        if chunk_id in seen:
                            sys.exit(f"Duplicate chunk id {chunk_id} (article label: {label!r}).")
                        seen.add(chunk_id)
                        chunk = {
                            "id": chunk_id,
                            "source_id": src["id"],
                            "source": src["short"],
                            "lang": lang,
                            "article": label,
                            "text": text,
                            "url": url,
                        }
                        f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                        n += 1
                print(f"{src['id']}.{lang}: {len(arts)} articles -> {n} chunks")
                total += n
    print(f"\n{total} chunks written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
