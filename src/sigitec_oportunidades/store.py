"""CSV local e sincronização incremental com a API."""

import asyncio
import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import api
from .console import console
from .constants import COLUMNS, LIST_SEP, STALE_AFTER, SUMMARY_KEYS
from .render import page_url


def to_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return LIST_SEP.join(str(v) for v in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("\r\n", "\n")


def from_row(row: dict[str, str]) -> dict:
    d: dict = {k: (v if v != "" else None) for k, v in row.items()}
    for k in ("id", "numberOP"):
        d[k] = int(d[k])
    d["nodeBackend"] = d.get("nodeBackend") == "true"
    sp = d.get("selectedPartnership")
    d["selectedPartnership"] = sp.split(LIST_SEP) if sp else None
    return d


def load_cache(path: Path) -> dict[int, dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {(d := from_row(row))["numberOP"]: d for row in csv.DictReader(f)}


def save_cache(path: Path, rows: dict[int, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for d in sorted(rows.values(), key=lambda d: d["numberOP"], reverse=True):
            w.writerow({k: to_cell(d.get(k)) for k in COLUMNS})
    tmp.replace(path)


def cache_age(path: Path) -> timedelta | None:
    if not path.exists():
        return None
    return datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)


def merge(summary: dict, detail: dict | None, previous: dict | None) -> dict:
    """Combina detalhe (ou o detalhe antigo) com o resumo mais recente da listagem."""
    if detail is not None:
        row = dict(detail)
        row["detailFetchedAt"] = datetime.now(UTC).isoformat(timespec="seconds")
    elif previous is not None:
        row = dict(previous)
        row["detailFetchedAt"] = None  # resumo mudou mas o detalhe falhou: tentar de novo
    else:
        row = {}
    row.update({k: v for k, v in summary.items() if v is not None})
    row["url"] = page_url(row)
    return row


def with_fresh_detail(row: dict | None, opp_id: int, detail: dict) -> dict:
    """Detalhe recém-baixado da API (`show --online`) sobre a linha do CSV.

    O detalhe prevalece; da linha ficam só id/numberOP (já inteiros) e o que o detalhe
    não traz (ex.: publicationDate vem nulo no detalhe).
    """
    ids = {k: row[k] for k in ("id", "numberOP")} if row else {"id": opp_id}
    fresh = {k: v for k, v in merge(ids, detail, None).items() if v is not None}
    return {k: v for k, v in (row or {}).items() if v is not None} | fresh


def run_sync(
    path: Path,
    *,
    details: bool = True,
    full: bool = False,
    concurrency: int = 4,
    retries: int = 1,
    max_failures: int = 5,
    list_timeout: float = api.LIST_TIMEOUT,
) -> dict[int, dict]:
    cache = load_cache(path)
    # A chave é o numberOP: o mesmo id aparece no SIGITEC novo e no antigo.
    with console.status("Baixando listagem…"):
        summaries = {o["numberOP"]: o for o in api.fetch_list(list_timeout)}

    def needs_detail(op: int) -> bool:
        new = summaries[op]
        if new.get("nodeBackend"):
            return False
        old = cache.get(op)
        if full or old is None or not old.get("detailFetchedAt"):
            return True
        return any(to_cell(old.get(k)) != to_cell(new.get(k)) for k in SUMMARY_KEYS)

    todo = [op for op in summaries if needs_detail(op)] if details else []
    fetched: dict[int, dict] = {}
    aborted = False
    if todo:
        console.print(f"Detalhes a baixar: {len(todo)} de {len(summaries)}")
        by_id, _failed, aborted = asyncio.run(
            api.fetch_details(
                [summaries[op]["id"] for op in todo], concurrency, retries, max_failures
            )
        )
        fetched = {op: by_id[summaries[op]["id"]] for op in todo if summaries[op]["id"] in by_id}

    rows: dict[int, dict] = {}
    for op, summary in summaries.items():
        old = cache.get(op)
        if op in fetched:
            rows[op] = merge(summary, fetched[op], old)
        elif op in todo or old is None:
            rows[op] = merge(summary, None, old)
        else:
            # Mantém o detalhe antigo; o resumo da listagem sempre prevalece.
            rows[op] = {k: v for k, v in old.items() if v is not None} | merge(summary, None, None)
    save_cache(path, rows)

    new = len(summaries.keys() - cache.keys())
    gone = len(cache.keys() - summaries.keys())
    legacy = sum(1 for r in rows.values() if r.get("nodeBackend"))
    missing = sum(
        1 for r in rows.values() if not r.get("detailFetchedAt") and not r.get("nodeBackend")
    )
    console.print(
        f"[green]{len(rows)} oportunidades salvas em {path}[/] "
        f"(novas: {new}, removidas: {gone}, detalhes baixados: {len(fetched)}, "
        f"SIGITEC antigo só com resumo: {legacy})"
    )
    if aborted:
        console.print(
            f"[yellow]A API de detalhes falhou {max_failures} vezes seguidas e o download foi "
            "interrompido (o SIGITEC às vezes fica instável).[/]"
        )
    if missing:
        console.print(
            f"[yellow]{missing} oportunidade(s) sem detalhes; rode `sync` de novo mais tarde.[/]"
        )
    return rows


def get_rows(path: Path, refresh: bool) -> dict[int, dict]:
    if refresh:
        return run_sync(path)
    age = cache_age(path)
    if age is None:
        console.print("[dim]Cache local não encontrado; baixando a listagem (sem detalhes)…[/]")
        console.print("[dim]Rode `sync` para baixar os detalhes completos.[/]")
        return run_sync(path, details=False)
    if age > STALE_AFTER:
        console.print(
            f"[yellow]Cache com {age.days}d {age.seconds // 3600}h; use `sync` ou `--refresh`.[/]"
        )
    return load_cache(path)
