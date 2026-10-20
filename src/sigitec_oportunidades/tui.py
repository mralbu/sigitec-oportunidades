"""Interface interativa (Textual): filtros à esquerda, resultados e detalhe à direita."""

from datetime import date
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Select,
    SelectionList,
)

from . import query
from .constants import STATUS, STATUS_COLORS
from .render import fmt_date, to_markdown

# Menus de valor exato: (coluna, rótulo).
EXACT_FILTERS = [
    ("area", "Área de pesquisa"),
    ("theme", "Tema"),
    ("subTheme", "Subtema"),
    ("intendedTrl", "TRL pretendido"),
    ("expectedSolution", "Solução esperada"),
]
# Status curto para a tabela; o detalhe mostra o nome completo.
SHORT_STATUS = STATUS | {"A": "Aberta"}
SORTS = [("Prazo de proposta", "deadline"), ("Número da OP", "number"), ("Publicação", "published")]


def parse_day(text: str) -> date | None:
    """Data AAAA-MM-DD; ValueError se o texto não estiver vazio nem for uma data."""
    text = text.strip()
    return date.fromisoformat(text) if text else None


class OpportunitiesApp(App):
    TITLE = "SIGITEC Oportunidades"
    CSS = """
    #filters {
        width: 40;
        padding: 0 1;
        border-right: tall $panel;
    }
    #filters.-hidden { display: none; }
    #filters Label { margin-top: 1; color: $text-muted; }
    #filters SelectionList { height: auto; }
    #dates Input { width: 1fr; }
    #dates { height: auto; }
    #results { height: 1fr; }
    #count { padding: 0 1; color: $text-muted; }
    #detail {
        height: 1fr;
        border-top: tall $panel;
        padding: 0 1;
    }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Sair"),
        Binding("slash", "focus_search", "Buscar"),
        Binding("f", "toggle_filters", "Filtros"),
        Binding("x", "reset", "Limpar filtros"),
        Binding("o", "open_url", "Abrir no navegador"),
    ]

    def __init__(self, rows: list[dict], terms: str = "", statuses: set[str] | None = None) -> None:
        super().__init__()
        self.rows = rows
        self.by_op = {o["numberOP"]: o for o in rows}
        self.initial_terms = terms
        self.initial_statuses = statuses or set()
        self.current: dict | None = None
        # Os widgets avisam mudanças já ao montar, antes de a tabela ter colunas.
        self.ready = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with VerticalScroll(id="filters"):
                yield Label("Busca (todos os termos)")
                yield Input(self.initial_terms, placeholder="título, desafio, tema…", id="terms")
                yield Label("Status")
                yield SelectionList[str](
                    *(
                        (label, code, code in self.initial_statuses)
                        for code, label in STATUS.items()
                    ),
                    id="statuses",
                )
                for key, label in EXACT_FILTERS:
                    yield Label(label)
                    yield Select(
                        [(v, v) for v in query.distinct(self.rows, key)],
                        prompt="Todos",
                        id=f"eq-{key}",
                    )
                yield Label("Prazo de proposta (AAAA-MM-DD)")
                with Horizontal(id="dates"):
                    yield Input(placeholder="de", id="after")
                    yield Input(placeholder="até", id="before")
                yield Label("Ordenar por")
                yield Select(SORTS, value="deadline", allow_blank=False, id="sort")
                yield Checkbox("Ordem crescente", id="asc")
            with Vertical():
                yield DataTable(id="results", cursor_type="row", zebra_stripes=True)
                yield Label(id="count")
                with VerticalScroll(id="detail"):
                    yield Markdown(id="markdown")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results", DataTable)
        table.add_column("OP", key="op")
        table.add_column("Prazo", key="deadline")
        table.add_column("Status", key="status")
        table.add_column("Título", key="title")
        self.ready = True
        self.apply_filters()
        table.focus()

    # ------------------------------------------------------------------ filtros

    def build_filter(self) -> query.Filter:
        equals = {}
        for key, _ in EXACT_FILTERS:
            value = self.query_one(f"#eq-{key}", Select).value
            if isinstance(value, str):
                equals[key] = value
        return query.Filter(
            terms=self.query_one("#terms", Input).value.split(),
            statuses=set(self.query_one("#statuses", SelectionList).selected),
            after=self.date_input("after"),
            before=self.date_input("before"),
            equals=equals,
        )

    def date_input(self, widget_id: str) -> date | None:
        """Data do campo; inválida (ou incompleta) é ignorada e o campo fica marcado."""
        widget = self.query_one(f"#{widget_id}", Input)
        try:
            value = parse_day(widget.value)
        except ValueError:
            widget.add_class("-invalid")
            return None
        widget.remove_class("-invalid")
        return value

    @on(Input.Changed)
    @on(Select.Changed)
    @on(SelectionList.SelectedChanged)
    @on(Checkbox.Changed)
    def apply_filters(self) -> None:
        if not self.ready:
            return
        sort = self.query_one("#sort", Select).value
        results = query.search(
            self.rows,
            self.build_filter(),
            sort if isinstance(sort, str) else "deadline",
            asc=self.query_one("#asc", Checkbox).value,
        )
        table = self.query_one("#results", DataTable)
        table.clear()
        for o in results:
            st = o["status"]
            table.add_row(
                f"OP{o['numberOP']}",
                fmt_date(o.get("deadlineSubmissionOfProposal")),
                Text(SHORT_STATUS.get(st, st), style=STATUS_COLORS.get(st, "")),
                o["titleOP"].strip(),
                key=str(o["numberOP"]),
            )
        self.query_one("#count", Label).update(
            f"{len(results)} de {len(self.rows)} oportunidade(s)"
        )
        self.show_detail(results[0] if results else None)

    # ------------------------------------------------------------------ detalhe

    @on(DataTable.RowHighlighted)
    def row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key.value is not None:
            self.show_detail(self.by_op[int(event.row_key.value)])

    def show_detail(self, o: dict | None) -> None:
        self.current = o
        markdown = self.query_one("#markdown", Markdown)
        if o is None:
            markdown.update("*Nenhuma oportunidade encontrada.*")
            return
        note = ""
        if o.get("nodeBackend"):
            note = "> SIGITEC antigo: só o resumo está disponível.\n\n"
        elif not o.get("detailFetchedAt"):
            note = "> Sem detalhes no CSV; rode `sigitec-oportunidades sync`.\n\n"
        markdown.update(note + to_markdown(o))
        self.query_one("#detail", VerticalScroll).scroll_home(animate=False)

    # ------------------------------------------------------------------ ações

    def action_focus_search(self) -> None:
        self.query_one("#filters").remove_class("-hidden")
        self.query_one("#terms", Input).focus()

    def action_toggle_filters(self) -> None:
        self.query_one("#filters").toggle_class("-hidden")

    def action_reset(self) -> None:
        with self.prevent(Input.Changed, Select.Changed, SelectionList.SelectedChanged):
            for widget_id in ("terms", "after", "before"):
                self.query_one(f"#{widget_id}", Input).value = ""
            self.query_one("#statuses", SelectionList).deselect_all()
            for key, _ in EXACT_FILTERS:
                self.query_one(f"#eq-{key}", Select).clear()
        self.apply_filters()

    def action_open_url(self) -> None:
        if self.current and self.current.get("url"):
            self.open_url(self.current["url"])
