from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from click.testing import CliRunner

from sigitec_oportunidades import feed, store
from sigitec_oportunidades.cli import cli

from .conftest import summary

NOW = datetime(2026, 11, 18, 12, tzinfo=UTC)


def items(xml: str) -> list[ET.Element]:
    return ET.fromstring(xml).findall("./channel/item")


def test_items_newest_first_and_skip_undated(rows):
    rows[3500] = store.merge(
        summary(3500, 2300, publicationDate="2026-11-03T19:15:55.000+00:00"), None, None
    )
    rows[901] = store.merge(summary(901, 1, publicationDate=None, nodeBackend=True), None, None)
    got = items(feed.build_rss(rows, now=NOW))
    assert [i.findtext("guid") for i in got] == [
        "sigitec-op-3500",
        "sigitec-op-3459",
        "sigitec-op-3400",
        "sigitec-op-900",
    ]
    assert feed.build_rss(rows, now=NOW, limit=2).count("<item>") == 2


def test_item_fields(rows):
    xml = feed.build_rss(rows, site_url="https://example.org/s/", now=NOW)
    root = ET.fromstring(xml)
    assert root.findtext("./channel/lastBuildDate") == "Wed, 18 Nov 2026 12:00:00 +0000"
    item = next(i for i in items(xml) if i.findtext("guid") == "sigitec-op-3459")
    assert item.findtext("title") == "OP3459 - Oportunidade 3459"
    assert item.findtext("link") == "https://example.org/s/#op=3459"
    assert item.find("guid[@isPermaLink='false']") is not None
    assert item.findtext("pubDate") == "Wed, 14 Oct 2026 19:13:39 +0000"
    assert [c.text for c in item.findall("category")] == ["Exploração e Produção", "Produção"]
    desc = item.findtext("description", "")
    assert "29/10/2026" in desc
    assert "Produção / Geologia de Reservatório" in desc
    assert "https://sigitec-competitividade.petrobras.com.br/v2/public/opportunity/2259" in desc


def test_description_escapes_html(rows):
    rows[3459]["objective"] = "<script>x</script> & mais"
    desc = items(feed.build_rss(rows, now=NOW))[0].findtext("description", "")
    assert "<script>" not in desc
    assert "&lt;script&gt;x&lt;/script&gt; &amp; mais" in desc


def test_excerpt():
    assert feed.excerpt("  a\n b  ") == "a b"
    assert feed.excerpt("palavra " * 10, size=20) == "palavra palavra…"


def test_cli_writes_file(csv_path: Path, tmp_path: Path):
    out = tmp_path / "site" / "feed.xml"
    result = CliRunner().invoke(cli, ["--csv", str(csv_path), "feed", "-o", str(out), "-n", "1"])
    assert result.exit_code == 0, result.output
    assert len(items(out.read_text(encoding="utf-8"))) == 1
