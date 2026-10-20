from pathlib import Path

import pytest

from sigitec_oportunidades import store


def summary(op: int, opp_id: int, **kw) -> dict:
    """Item como vem da listagem da API (só campos de resumo)."""
    return {
        "id": opp_id,
        "numberOP": op,
        "titleOP": f"Oportunidade {op}",
        "status": "A",
        "deadlineSubmissionOfProposal": "2026-10-29T03:00:00.000+00:00",
        "publicationDate": "2026-10-14T19:13:39.000+00:00",
        "objective": "Objetivo",
        "nodeBackend": False,
        "theme": None,
    } | kw


def detail(op: int, opp_id: int, **kw) -> dict:
    """Item como vem do detalhe da API (ids como texto, campos extras)."""
    return (
        summary(op, opp_id)
        | {
            "id": str(opp_id),
            "numberOP": str(op),
            "theme": "Produção",
            "subTheme": "Geologia de Reservatório",
            "area": "Exploração e Produção",
            "commitment": "SIM",
            "regulatoryAgency": "ANP",
            "intendedTrl": "TRL7-9",
            "challenge": "Desafio de microtomografia",
            "selectedPartnership": ["Aguardando resultado do certame"],
            "nodeBackend": None,
            "publicationDate": None,
        }
        | kw
    )


@pytest.fixture
def rows() -> dict[int, dict]:
    """Linhas já no formato do CSV: uma com detalhe, uma só resumo e uma do SIGITEC antigo."""
    return {
        3459: store.merge(
            summary(3459, 2259),
            detail(3459, 2259, selectedPartnership=["UNICAMP", "PUC-Rio"]),
            None,
        ),
        3400: store.merge(
            summary(3400, 2200, status="F", titleOP="Petrofísica de rochas"), None, None
        ),
        900: store.merge(summary(900, 2259, status="F", nodeBackend=True), None, None),
    }


@pytest.fixture
def csv_path(tmp_path: Path, rows: dict[int, dict]) -> Path:
    path = tmp_path / "oportunidades.csv"
    store.save_cache(path, rows)
    return path
