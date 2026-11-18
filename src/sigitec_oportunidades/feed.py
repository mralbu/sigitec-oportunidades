"""Feed RSS 2.0 com as oportunidades publicadas mais recentemente."""

from datetime import UTC, datetime
from email.utils import format_datetime
from html import escape
from xml.etree import ElementTree as ET

from .constants import NA, SITE_URL, STATUS
from .render import fmt_date, page_url, parse_date

ATOM = "http://www.w3.org/2005/Atom"
FEED_FILE = "feed.xml"
DEFAULT_LIMIT = 50
EXCERPT = 600


def excerpt(text: str | None, size: int = EXCERPT) -> str:
    text = " ".join((text or "").split())
    if len(text) <= size:
        return text
    return text[:size].rsplit(" ", 1)[0] + "…"


def item_link(d: dict, site_url: str = SITE_URL) -> str:
    return f"{site_url}#op={d['numberOP']}"


def item_description(d: dict) -> str:
    """Resumo em HTML (escapado dentro do XML): campos para decidir se vale abrir."""
    fields = [
        ("Prazo para envio de proposta", fmt_date(d.get("deadlineSubmissionOfProposal"))),
        ("Status", STATUS.get(d.get("status") or "", d.get("status") or NA)),
        ("Área de pesquisa", d.get("area") or NA),
        ("Tema", " / ".join(t for t in (d.get("theme"), d.get("subTheme")) if t) or NA),
        ("TRL pretendido", d.get("intendedTrl") or NA),
        ("Solução esperada", d.get("expectedSolution") or NA),
    ]
    parts = ["<ul>"]
    parts += [f"<li><b>{k}:</b> {escape(v)}</li>" for k, v in fields]
    parts.append("</ul>")
    if objective := excerpt(d.get("objective")):
        parts.append(f"<p><b>Objetivo:</b> {escape(objective)}</p>")
    parts.append(f'<p><a href="{escape(page_url(d))}">Página no SIGITEC</a></p>')
    return "".join(parts)


def recent(rows: dict[int, dict], limit: int) -> list[tuple[datetime, dict]]:
    """As `limit` oportunidades mais recentes que têm data de publicação."""
    dated = [(pub, d) for d in rows.values() if (pub := parse_date(d.get("publicationDate")))]
    dated.sort(key=lambda t: (t[0], t[1]["numberOP"]), reverse=True)
    return dated[:limit]


def build_rss(
    rows: dict[int, dict],
    *,
    site_url: str = SITE_URL,
    limit: int = DEFAULT_LIMIT,
    now: datetime | None = None,
) -> str:
    ET.register_namespace("atom", ATOM)
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for tag, text in [
        ("title", "SIGITEC Oportunidades"),
        ("link", site_url),
        (
            "description",
            "Novas oportunidades públicas de P&D da Petrobras no SIGITEC Competitividade. "
            "Atualizado uma vez por semana, às segundas-feiras de manhã.",
        ),
        ("language", "pt-BR"),
        ("lastBuildDate", format_datetime(now or datetime.now(UTC))),
        ("ttl", str(24 * 60)),
    ]:
        ET.SubElement(channel, tag).text = text
    ET.SubElement(
        channel,
        f"{{{ATOM}}}link",
        href=f"{site_url}{FEED_FILE}",
        rel="self",
        type="application/rss+xml",
    )

    for pub, d in recent(rows, limit):
        item = ET.SubElement(channel, "item")
        title = (d.get("titleOP") or "").strip()
        ET.SubElement(item, "title").text = f"OP{d['numberOP']} - {title}"
        ET.SubElement(item, "link").text = item_link(d, site_url)
        ET.SubElement(item, "guid", isPermaLink="false").text = f"sigitec-op-{d['numberOP']}"
        ET.SubElement(item, "pubDate").text = format_datetime(pub.astimezone(UTC))
        for cat in dict.fromkeys(c for c in (d.get("area"), d.get("theme")) if c):
            ET.SubElement(item, "category").text = cat
        ET.SubElement(item, "description").text = item_description(d)

    ET.indent(rss)
    return ET.tostring(rss, encoding="unicode", xml_declaration=True) + "\n"
