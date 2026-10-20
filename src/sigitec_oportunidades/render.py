"""Normalização de texto e formatação (Markdown, datas)."""

import unicodedata
from datetime import datetime

from .constants import BRT, COLUMNS, LEGACY_PAGE_URL, NA, PAGE_URL, STATUS


def norm(text: str) -> str:
    """Minúsculas e sem acentos, para busca."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).casefold()


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(BRT)


def fmt_date(value: str | None) -> str:
    d = parse_date(value)
    return d.strftime("%d/%m/%Y") if d else "-"


def page_url(d: dict) -> str:
    return (LEGACY_PAGE_URL if d.get("nodeBackend") else PAGE_URL).format(id=d["id"])


def public_fields(d: dict) -> dict:
    return {k: d.get(k) for k in COLUMNS}


def to_markdown(d: dict) -> str:
    lines = [
        f"# OP{d['numberOP']} - {d['titleOP'].strip()}",
        "",
        f"Fonte: {page_url(d)}",
        "",
        f"- **Prazo para envio de proposta:** {fmt_date(d.get('deadlineSubmissionOfProposal'))}",
        f"- **Status:** {STATUS.get(d['status'], d['status'])}",
        f"- **Área de pesquisa:** {d.get('area') or NA}",
        "",
        "## Intenção de enquadramento",
        "",
        f"- **Obrigação:** {'Sim' if d.get('commitment') == 'SIM' else 'Não'}",
    ]
    if d.get("commitment") != "NAO":
        lines.append(f"- **Agência:** {d.get('regulatoryAgency') or NA}")
    lines += [
        f"- **Tema:** {d.get('theme') or NA}",
        f"- **Subtema:** {d.get('subTheme') or NA}",
        "",
        "## Desafio",
        "",
        d.get("challenge") or NA,
        "",
        "## Objetivo",
        "",
        d.get("objective") or NA,
        "",
        f"- **TRL pretendido:** {d.get('intendedTrl') or NA}",
        f"- **CRL pretendido:** {d.get('intendedCrl') or NA}",
        f"- **Prazo para desenvolvimento da solução:** {d.get('developmentDeadline') or 0} meses",
        "",
        "## Solução esperada",
        "",
        d.get("expectedSolution") or NA,
        "",
        "## Solução detalhada",
        "",
        d.get("expectedSolutionDetail") or NA,
        "",
        "## Pitch e Live",
        "",
        f"- **Pitch:** {d.get('linkToVideOrpresentation') or NA}",
        f"- **Live:** {d.get('liveLink') or NA}",
        f"- **Data:** {fmt_date(d['liveDate']) if d.get('liveDate') else NA}",
        f"- **Hora início:** {d.get('liveStartTime') or NA}",
        f"- **Hora término:** {d.get('liveEndTime') or NA}",
        "",
        "## Parceira(s) selecionada(s)",
        "",
    ]
    lines += [f"- {p}" for p in d.get("selectedPartnership") or [NA]]
    return "\n".join(lines).replace("\r\n", "\n").strip() + "\n"
