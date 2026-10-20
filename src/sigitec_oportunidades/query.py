"""Filtros, ordenação e contagens sobre as linhas do CSV (sem E/S)."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from .constants import PENDING_PARTNER, STATUS, TEXT_KEYS
from .render import norm, parse_date


@dataclass
class Filter:
    """Critérios do `search`; todos os informados precisam bater."""

    terms: list[str] = field(default_factory=list)
    title: str | None = None
    objective: str | None = None
    theme: str | None = None
    code: int | None = None
    statuses: set[str] = field(default_factory=set)
    after: date | None = None
    before: date | None = None

    def __post_init__(self) -> None:
        self.terms = [norm(t) for t in self.terms]
        self.statuses = {s.upper() for s in self.statuses}

    def match(self, o: dict) -> bool:
        if self.statuses and o["status"] not in self.statuses:
            return False
        if self.code is not None and o["numberOP"] != self.code:
            return False
        if not (
            _contains(o.get("titleOP"), self.title)
            and _contains(o.get("objective"), self.objective)
        ):
            return False
        if self.theme and not _contains(_joined(o, ("theme", "subTheme", "area")), self.theme):
            return False
        if self.after or self.before:
            d = parse_date(o.get("deadlineSubmissionOfProposal"))
            if d is None:
                return False
            if (self.after and d.date() < self.after) or (self.before and d.date() > self.before):
                return False
        if self.terms:
            hay = norm(_joined(o, TEXT_KEYS))
            return all(t in hay for t in self.terms)
        return True


def _joined(o: dict, keys: Iterable[str]) -> str:
    return " ".join(str(o.get(k) or "") for k in keys)


def _contains(value, needle: str | None) -> bool:
    return needle is None or norm(needle) in norm(str(value or ""))


SORT_KEYS = {
    "deadline": lambda o: o.get("deadlineSubmissionOfProposal") or "",
    "number": lambda o: o["numberOP"],
    "published": lambda o: o.get("publicationDate") or "",
}


def search(rows: Iterable[dict], flt: Filter, sort: str = "deadline", asc: bool = False):
    """Linhas que batem com o filtro, ordenadas."""
    return sorted((o for o in rows if flt.match(o)), key=SORT_KEYS[sort], reverse=not asc)


def stat_values(o: dict, key: str) -> list[str]:
    """Valores de uma oportunidade para a contagem do `stats` (vazio = não informado)."""
    if key == "status":
        return [STATUS.get(o["status"]) or str(o["status"])]
    if key == "year":
        d = parse_date(o.get("publicationDate"))
        return [str(d.year)] if d else []
    if key == "selectedPartnership":
        partners = (p.strip() for p in o.get("selectedPartnership") or [])
        return [p for p in partners if p != PENDING_PARTNER]
    v = o.get(key)
    return [str(v).strip()] if v not in (None, "") else []


def column_stats(rows: list[dict], key: str) -> tuple[Counter[str], int]:
    """(contagem por valor, quantas linhas sem valor) de uma coluna."""
    counts: Counter[str] = Counter()
    missing = 0
    for o in rows:
        values = stat_values(o, key)
        counts.update(values)
        missing += not values
    return counts, missing
