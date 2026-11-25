"""Download the raw regulation texts into data/raw/.

Usage (from the project root):
    python src/download.py

Files already downloaded are skipped; pass --force to download them again.
"""
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from sources import SOURCES  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
HEADERS = {
    "User-Agent": "document-agent-rag/0.1 (portfolio project; github.com/crobleto97/document-agent-rag)",
    "Accept": "application/xml, text/html;q=0.9",
}


def main(force: bool = False) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    failed = []
    for src in SOURCES:
        ext = "xml" if src["format"] == "boe" else "html"
        for lang, url in src["versions"].items():
            out = RAW / f"{src['id']}.{lang}.{ext}"
            if out.exists() and out.stat().st_size > 0 and not force:
                print(f"skip  {out.name} (already downloaded)")
                continue
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            # EUR-Lex sits behind an AWS WAF bot challenge: it answers 202 with an
            # empty body instead of the text. Don't save that; ask for a manual save.
            if r.status_code != 200 or not r.content:
                print(
                    f"FAIL  {out.name}: got HTTP {r.status_code} with {len(r.content)} bytes"
                    f" (waf: {r.headers.get('x-amzn-waf-action', '-')}).\n"
                    f"      Open {url} in a browser, save it as 'Web page, HTML only'"
                    f" to {out}"
                )
                failed.append(out.name)
                continue
            out.write_bytes(r.content)
            print(f"saved {out.name}  {len(r.content) / 1024:.0f} KB")
            time.sleep(1)  # be polite to the public servers
    if failed:
        sys.exit(f"{len(failed)} file(s) need a manual download: {', '.join(failed)}")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
