"""Parser tests on small samples copied from the real EUR-Lex and BOE formats."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from parse import article_key, boe_articles, eurlex_articles, split_long  # noqa: E402

CONSOLIDATED = """<html><body>
<div class="eli-subdivision" id="art_7">
  <p class="title-article-norm">Article&nbsp;7</p>
  <p class="norm">After a driving period of four and a half hours a driver shall take an uninterrupted break of not less than 45 minutes, unless he takes a rest period.</p>
  <p class="modref"><a href="#">▼M4</a></p>
  <p class="norm">For a&nbsp;driver engaged in an occasional passenger service, the break may be replaced by two breaks.</p>
</div>
<div class="eli-subdivision" id="art_8"><p class="title-article-norm">Article 8</p><p class="norm">A driver shall take daily and weekly rest periods.</p></div>
</body></html>"""

ORIGINAL = """<html><body><div id="TexteOnly">
<p>HAVE ADOPTED THIS DIRECTIVE:</p>
<p>Article 3</p><p>Definitions</p><p>For the purposes of this Directive:</p><p>(a) "working time" shall mean:</p>
<p>Article 4</p><p>Maximum weekly working time</p><p>The average weekly working time may not exceed 48 hours.</p>
<p>Done at Brussels, 11 March 2002.</p><p>Article 99</p><p>should not appear</p>
</div></body></html>"""

BOE = """<?xml version="1.0" encoding="utf-8"?><response><data><texto>
<bloque id="ci" tipo="encabezado" titulo="CAPÍTULO I"><version id_norma="X" fecha_publicacion="20091112"><p class="capitulo_num">CAPÍTULO I</p></version></bloque>
<bloque id="a47" tipo="precepto" titulo="Artículo 47">
 <version id_norma="X" fecha_publicacion="20091112"><p class="articulo">Artículo 47. Supuestos de responsabilidad.</p><p class="parrafo">Texto antiguo.</p></version>
 <version id_norma="X" fecha_publicacion="20220802"><p class="articulo">Artículo 47. Supuestos de responsabilidad.</p><p class="parrafo">1. El porteador responderá de la pérdida total o parcial de las mercancías.</p><blockquote><p>Se modifica por la Ley X</p></blockquote></version>
</bloque></texto></data></response>"""


def test_consolidated_eurlex_skips_markers():
    arts = eurlex_articles(CONSOLIDATED)
    assert [a for a, _ in arts] == ["Article 7", "Article 8"]
    text = " ".join(arts[0][1])
    assert "▼" not in text and "45 minutes" in text and "\xa0" not in text
    assert len(arts[0][1]) == 2


def test_original_eurlex_stops_at_signature():
    arts = eurlex_articles(ORIGINAL)
    assert [a for a, _ in arts] == ["Article 3", "Article 4"]
    assert arts[1][1][0] == "Maximum weekly working time"


def test_boe_uses_latest_version_and_skips_notes():
    arts = boe_articles(BOE.encode())
    assert len(arts) == 1
    label, paras = arts[0]
    assert label == "Artículo 47. Supuestos de responsabilidad."
    assert paras == ["1. El porteador responderá de la pérdida total o parcial de las mercancías."]


def test_split_long_keeps_parts_under_limit():
    parts = split_long(["x" * 1000, "y" * 1000, "z" * 500])
    assert len(parts) == 2 and all(len(p) <= 1800 for p in parts)


def test_article_key_keeps_inserted_articles_distinct():
    assert article_key("Article 9") == "9"
    assert article_key("Article 9a") == "9a"
    assert article_key("Artículo 9 bis") == "9bis"
    assert article_key("Artículo 47. Supuestos de responsabilidad.") == "47"
    assert article_key("Article 12") == "12"
