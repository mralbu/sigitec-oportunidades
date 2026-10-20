import asyncio

import pytest
from textual.widgets import DataTable, Input, Markdown, Select, SelectionList

from sigitec_oportunidades.tui import OpportunitiesApp, parse_day


def run_app(rows: dict[int, dict], scenario, **kw) -> None:
    """Roda a TUI sem terminal e executa `scenario(app, pilot)`."""

    async def main():
        app = OpportunitiesApp(list(rows.values()), **kw)
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await scenario(app, pilot)

    asyncio.run(main())


def shown(app: OpportunitiesApp) -> list[str]:
    table = app.query_one("#results", DataTable)
    return [str(table.get_row_at(i)[0]) for i in range(table.row_count)]


def detail(app: OpportunitiesApp) -> str:
    return app.query_one("#markdown", Markdown).source


def test_parse_day():
    assert parse_day(" 2026-10-29 ") is not None
    assert parse_day("") is None
    with pytest.raises(ValueError):
        parse_day("2026-1")


def test_initial_filters(rows):
    async def scenario(app, pilot):
        assert shown(app) == ["OP3459"]
        assert detail(app).startswith("# OP3459")

    run_app(rows, scenario, statuses={"A"})


def test_filters(rows):
    async def scenario(app, pilot):
        assert len(shown(app)) == 3

        app.query_one("#terms", Input).value = "petrofisica"
        await pilot.pause()
        assert shown(app) == ["OP3400"]
        assert "Sem detalhes no CSV" in detail(app)

        await pilot.press("escape")
        app.action_reset()
        await pilot.pause()
        assert len(shown(app)) == 3

        app.query_one("#eq-theme", Select).value = "Produção"
        await pilot.pause()
        assert shown(app) == ["OP3459"]

        app.action_reset()
        app.query_one("#statuses", SelectionList).select("F")
        await pilot.pause()
        assert sorted(shown(app)) == ["OP3400", "OP900"]

    run_app(rows, scenario)


def test_invalid_date_is_ignored(rows):
    async def scenario(app, pilot):
        after = app.query_one("#after", Input)
        after.value = "2026-1"
        await pilot.pause()
        assert after.has_class("-invalid")
        assert len(shown(app)) == 3

        after.value = "2026-10-30"
        await pilot.pause()
        assert not after.has_class("-invalid")
        assert shown(app) == []
        assert "Nenhuma oportunidade" in detail(app)

    run_app(rows, scenario)


def test_highlight_shows_detail(rows):
    async def scenario(app, pilot):
        app.query_one("#sort", Select).value = "number"
        await pilot.pause()
        app.query_one("#results", DataTable).focus()
        await pilot.press("down")
        await pilot.pause()
        assert detail(app).startswith("> Sem detalhes")
        assert "# OP3400" in detail(app)

    run_app(rows, scenario)
