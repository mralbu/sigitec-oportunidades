"""Cliente da API pública do SIGITEC."""

import asyncio

import httpx2
from rich.progress import Progress, TaskID

from .console import console
from .constants import API

HEADERS = {"Accept": "application/json"}
TIMEOUT = 60


def fetch_list() -> list[dict]:
    """Listagem completa (só campos de resumo)."""
    with httpx2.Client(timeout=TIMEOUT, headers=HEADERS) as c:
        r = c.get(f"{API}/getAllPublicOpportunities")
        r.raise_for_status()
        return r.json()


def fetch_one(opp_id: int) -> dict | None:
    """Detalhe de uma oportunidade; None se não existir."""
    with httpx2.Client(timeout=TIMEOUT, headers=HEADERS) as c:
        r = c.get(f"{API}/public-opportunity/{opp_id}")
        if r.status_code == 404 or (r.is_success and not r.content):
            return None
        r.raise_for_status()
        return r.json()


async def fetch_details(
    ids: list[int], concurrency: int, retries: int, max_failures: int
) -> tuple[dict[int, dict], list[int], bool]:
    """Baixa detalhes em paralelo. Retorna (detalhes, ids com falha, abortado)."""
    results: dict[int, dict] = {}
    failed: list[int] = []
    sem = asyncio.Semaphore(concurrency)
    consecutive = 0
    aborted = asyncio.Event()

    async with httpx2.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as c:

        async def one(opp_id: int, progress: Progress, task: TaskID) -> None:
            nonlocal consecutive
            async with sem:
                if aborted.is_set():
                    failed.append(opp_id)
                    return
                for attempt in range(retries + 1):
                    try:
                        r = await c.get(f"{API}/public-opportunity/{opp_id}")
                        if r.status_code == 404:
                            break
                        r.raise_for_status()
                        results[opp_id] = r.json()
                        consecutive = 0
                        break
                    except httpx2.HTTPError, ValueError:
                        if attempt < retries:
                            await asyncio.sleep(2 * (attempt + 1))
                else:
                    failed.append(opp_id)
                    consecutive += 1
                    if consecutive >= max_failures:
                        aborted.set()
                progress.advance(task)

        with Progress(console=console, transient=True) as progress:
            task = progress.add_task("Baixando detalhes", total=len(ids))
            await asyncio.gather(*(one(i, progress, task) for i in ids))

    return results, failed, aborted.is_set()
