from datetime import date

import pytest

from sigitec_oportunidades import query
from sigitec_oportunidades.render import fmt_date, norm, to_markdown


def test_norm_ignores_accents_and_case():
    assert norm("Petrofísica ÁGUA") == "petrofisica agua"


def test_fmt_date_uses_brasilia_time():
    assert fmt_date("2026-10-29T03:00:00.000+00:00") == "29/10/2026"
    assert fmt_date("2026-10-29T02:00:00.000+00:00") == "28/10/2026"
    assert fmt_date(None) == "-"


def ops(rows, **kw) -> list[int]:
    return [o["numberOP"] for o in query.search(rows.values(), query.Filter(**kw), "number")]


def test_filter_terms_search_all_text_fields(rows):
    assert ops(rows, terms=["MICROTOMOGRAFIA"]) == [3459]  # está no desafio
    assert ops(rows, terms=["petrofisica", "rochas"]) == [3400]
    assert ops(rows, terms=["petrofisica", "inexistente"]) == []


@pytest.mark.parametrize(
    ("kw", "expected"),
    [
        ({}, [3459, 3400, 900]),
        ({"statuses": {"a"}}, [3459]),
        ({"code": 3400}, [3400]),
        ({"title": "petrofísica"}, [3400]),
        ({"theme": "geologia"}, [3459]),
        ({"after": date(2026, 10, 29)}, [3459, 3400, 900]),
        ({"after": date(2026, 10, 30)}, []),
        ({"before": date(2026, 10, 28)}, []),
    ],
)
def test_filter_fields(rows, kw, expected):
    assert ops(rows, **kw) == expected


def test_filter_equals(rows):
    assert ops(rows, equals={"theme": "Produção"}) == [3459]
    assert ops(rows, equals={"theme": "Produ"}) == []  # exato, não trecho


def test_distinct(rows):
    assert query.distinct(rows.values(), "status") == ["A", "F"]
    assert query.distinct(rows.values(), "theme") == ["Produção"]


def test_search_sort_ascending(rows):
    found = query.search(rows.values(), query.Filter(), "number", asc=True)
    assert [o["numberOP"] for o in found] == [900, 3400, 3459]


def test_stat_values(rows):
    assert query.stat_values(rows[3459], "status") == ["Aberta para envio de proposta"]
    assert query.stat_values(rows[3459], "year") == ["2026"]
    assert query.stat_values(rows[3459], "selectedPartnership") == ["UNICAMP", "PUC-Rio"]
    assert query.stat_values(rows[3400], "theme") == []


def test_stat_values_skips_pending_partner():
    o = {"selectedPartnership": ["Aguardando resultado do certame"]}
    assert query.stat_values(o, "selectedPartnership") == []


def test_column_stats(rows):
    counts, missing = query.column_stats(list(rows.values()), "status")
    assert counts == {"Finalizada": 2, "Aberta para envio de proposta": 1}
    assert missing == 0
    counts, missing = query.column_stats(list(rows.values()), "theme")
    assert counts == {"Produção": 1}
    assert missing == 2


def test_to_markdown(rows):
    md = to_markdown(rows[3459])
    assert md.startswith("# OP3459 - Oportunidade 3459\n")
    assert "- **Tema:** Produção" in md
    assert "- **Agência:** ANP" in md
    assert md.endswith("- UNICAMP\n- PUC-Rio\n")
    assert "- **Tema:** Não aplicável" in to_markdown(rows[3400])
