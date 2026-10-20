"""Interface de linha de comando (click)."""

import json
import sys
from pathlib import Path

import click
import httpx2
from click.shell_completion import get_completion_class
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from . import api, query, store
from .console import console
from .constants import APP_NAME, CSV_ENVVAR, STATS_COLUMNS, STATUS, STATUS_COLORS
from .render import fmt_date, public_fields, to_markdown
from .skill import SKILL

DEFAULT_CSV_NAME = "oportunidades.csv"
DEFAULT_CSV = Path(click.get_app_dir(APP_NAME)) / DEFAULT_CSV_NAME
COMPLETE_VAR = f"_{APP_NAME.replace('-', '_').upper()}_COMPLETE"
SHELLS = ["bash", "zsh", "fish"]

status_option = click.option(
    "-s",
    "--status",
    "statuses",
    multiple=True,
    type=click.Choice(list(STATUS), case_sensitive=False),
    help="Status: A=aberta, J=julgamento, R=resultado, F=finalizada, CC=cancelada. Repetível.",
)
open_option = click.option("--open", "only_open", is_flag=True, help="Atalho para --status A.")
json_option = click.option("--json", "as_json", is_flag=True, help="Saída em JSON.")
refresh_option = click.option("-r", "--refresh", is_flag=True, help="Roda `sync` antes.")


def selected_statuses(statuses: tuple[str, ...], only_open: bool) -> set[str]:
    return {s.upper() for s in statuses} | ({"A"} if only_open else set())


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--csv",
    "csv_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CSV_NAME,
    envvar=CSV_ENVVAR,
    show_default=True,
    help=f"Arquivo CSV local (ou variável {CSV_ENVVAR}).",
)
@click.version_option(package_name=APP_NAME)
@click.pass_context
def cli(ctx: click.Context, csv_path: Path) -> None:
    """Busca oportunidades públicas no SIGITEC Competitividade (Petrobras)."""
    ctx.obj = csv_path


@cli.command()
@click.option("--full", is_flag=True, help="Baixa de novo os detalhes de todas as oportunidades.")
@click.option(
    "--no-details", is_flag=True, help="Só a listagem (1 requisição; sem desafio, tema etc.)."
)
@click.option("-j", "--concurrency", type=click.IntRange(1, 16), default=4, show_default=True)
@click.option("--retries", type=click.IntRange(0, 5), default=1, show_default=True)
@click.option(
    "--max-failures",
    type=click.IntRange(1),
    default=5,
    show_default=True,
    help="Interrompe os detalhes após N falhas seguidas.",
)
@click.option(
    "--timeout",
    type=click.IntRange(1),
    default=api.LIST_TIMEOUT,
    show_default=True,
    help="Tempo máximo de espera pela listagem, em segundos.",
)
@click.pass_obj
def sync(
    csv_path: Path,
    full: bool,
    no_details: bool,
    concurrency: int,
    retries: int,
    max_failures: int,
    timeout: int,
) -> None:
    """Baixa as oportunidades para o CSV local (incremental)."""
    store.run_sync(
        csv_path,
        details=not no_details,
        full=full,
        concurrency=concurrency,
        retries=retries,
        max_failures=max_failures,
        list_timeout=timeout,
    )


@cli.command(short_help="Busca por termos e filtros no CSV local.")
@click.argument("terms", metavar="QUERY", nargs=-1)
@click.option("-t", "--title", help="Trecho do título.")
@click.option("-o", "--objective", help="Trecho do objetivo.")
@click.option("--theme", help="Trecho do tema, subtema ou área.")
@click.option("-c", "--code", type=int, help="Número da OP (ex.: 3449).")
@status_option
@open_option
@click.option(
    "--after",
    type=click.DateTime(["%Y-%m-%d"]),
    help="Prazo de proposta a partir de (AAAA-MM-DD).",
)
@click.option(
    "--before", type=click.DateTime(["%Y-%m-%d"]), help="Prazo de proposta até (AAAA-MM-DD)."
)
@click.option(
    "--sort", type=click.Choice(list(query.SORT_KEYS)), default="deadline", show_default=True
)
@click.option("--asc", is_flag=True, help="Ordem crescente (padrão: decrescente).")
@click.option(
    "-n",
    "--limit",
    type=int,
    default=50,
    show_default=True,
    help="Máximo de resultados (0 = todos).",
)
@json_option
@refresh_option
@click.pass_obj
def search(
    csv_path: Path,
    terms: tuple[str, ...],
    title: str | None,
    objective: str | None,
    theme: str | None,
    code: int | None,
    statuses: tuple[str, ...],
    only_open: bool,
    after,
    before,
    sort: str,
    asc: bool,
    limit: int,
    as_json: bool,
    refresh: bool,
) -> None:
    """Busca no CSV local. QUERY: termos (todos obrigatórios) em título, objetivo,
    desafio, solução, tema e área; sem diferenciar acentos/maiúsculas."""
    flt = query.Filter(
        terms=list(terms),
        title=title,
        objective=objective,
        theme=theme,
        code=code,
        statuses=selected_statuses(statuses, only_open),
        after=after.date() if after else None,
        before=before.date() if before else None,
    )
    results = query.search(store.get_rows(csv_path, refresh).values(), flt, sort, asc)
    total = len(results)
    if limit:
        results = results[:limit]

    if as_json:
        click.echo(json.dumps([public_fields(o) for o in results], ensure_ascii=False, indent=2))
        return
    if not results:
        console.print("[yellow]Nenhuma oportunidade encontrada.[/]")
        return

    table = Table(header_style="bold green")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("OP", justify="right")
    table.add_column("Prazo")
    table.add_column("Status")
    table.add_column("Título", overflow="fold")
    for o in results:
        st = o["status"]
        table.add_row(
            str(o["id"]),
            f"OP{o['numberOP']}",
            fmt_date(o.get("deadlineSubmissionOfProposal")),
            f"[{STATUS_COLORS.get(st, 'white')}]{STATUS.get(st, st)}[/]",
            o["titleOP"].strip(),
        )
    Console().print(table)
    console.print(f"[dim]{len(results)} de {total} resultado(s).[/]")


@cli.command(short_help="Mostra uma oportunidade pelo número da OP ou id.")
@click.argument("ref")
@click.option("--online", is_flag=True, help="Busca na API em vez do CSV local.")
@click.option(
    "--markdown", "as_markdown", is_flag=True, help="Imprime Markdown cru em vez de renderizado."
)
@json_option
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Salva o Markdown neste arquivo.",
)
@click.pass_obj
def show(
    csv_path: Path,
    ref: str,
    online: bool,
    as_markdown: bool,
    as_json: bool,
    output: Path | None,
) -> None:
    """Mostra uma oportunidade (REF = número da OP, ex. OP3449, ou id interno, ex. 2248)."""
    ref = ref.strip()
    by_op = ref.upper().startswith("OP")
    digits = ref[2:].strip(" -") if by_op else ref
    if not digits.isdigit():
        raise click.BadParameter("use um id numérico ou OP<número>", param_hint="REF")
    number = int(digits)

    rows = store.get_rows(csv_path, refresh=False)
    if by_op:
        row = rows.get(number)
        if row is None:
            raise click.ClickException(f"OP{number} não encontrada.")
    else:
        # O mesmo id pode existir no SIGITEC novo e no antigo; prefere o novo.
        matches = sorted(
            (r for r in rows.values() if r["id"] == number), key=lambda r: r["nodeBackend"]
        )
        row = matches[0] if matches else None
        if len(matches) > 1:
            others = ", ".join(f"OP{r['numberOP']}" for r in matches[1:])
            console.print(
                f"[dim]O id {number} também é {others} (SIGITEC antigo); use OP<número>.[/]"
            )

    data = row
    legacy = bool(row and row.get("nodeBackend"))
    if not legacy and (online or row is None or not row.get("detailFetchedAt")):
        opp_id = row["id"] if row else number
        try:
            detail = api.fetch_one(opp_id)
        except httpx2.HTTPError as e:
            if row is None:
                raise
            console.print(f"[yellow]API indisponível ({e}); mostrando só o resumo local.[/]")
        else:
            if detail is None:
                raise click.ClickException(f"Oportunidade {opp_id} não encontrada.")
            data = store.merge(row or {"id": opp_id}, detail, None)
    elif legacy:
        console.print("[dim]Oportunidade do SIGITEC antigo: só o resumo está disponível.[/]")
    assert data is not None

    if as_json:
        click.echo(json.dumps(public_fields(data), ensure_ascii=False, indent=2))
        return
    md = to_markdown(data)
    if output:
        output.write_text(md, encoding="utf-8")
        console.print(f"[green]Salvo em {output}[/]")
    elif as_markdown or not sys.stdout.isatty():
        click.echo(md, nl=False)
    else:
        Console().print(Markdown(md))


@cli.command()
@status_option
@open_option
@click.option(
    "-c",
    "--column",
    "columns",
    multiple=True,
    type=click.Choice([k for k, _ in STATS_COLUMNS]),
    help="Só estas colunas (repetível).",
)
@click.option(
    "-n", "--top", type=int, default=10, show_default=True, help="Valores por coluna (0 = todos)."
)
@json_option
@refresh_option
@click.pass_obj
def stats(
    csv_path: Path,
    statuses: tuple[str, ...],
    only_open: bool,
    columns: tuple[str, ...],
    top: int,
    as_json: bool,
    refresh: bool,
) -> None:
    """Contagens por status, ano, área, tema, TRL, parceiras etc. no CSV local."""
    rows = list(store.get_rows(csv_path, refresh).values())
    wanted = selected_statuses(statuses, only_open)
    if wanted:
        rows = [o for o in rows if o["status"] in wanted]
    selected = [(k, label) for k, label in STATS_COLUMNS if not columns or k in columns]
    legacy = sum(1 for o in rows if o.get("nodeBackend"))
    with_detail = sum(1 for o in rows if o.get("detailFetchedAt"))
    # Oportunidades sem valor na coluna contam como "missing" (as do SIGITEC antigo nunca
    # têm detalhe).
    per_column = {k: query.column_stats(rows, k) for k, _ in selected}

    if as_json:
        out = {
            "total": len(rows),
            "legacy": legacy,
            "withDetails": with_detail,
            "columns": {
                k: {"missing": missing, "values": dict(counts.most_common(top or None))}
                for k, (counts, missing) in per_column.items()
            },
        }
        click.echo(json.dumps(out, ensure_ascii=False, indent=2))
        return

    stdout = Console()
    stdout.print(
        f"[bold]{len(rows)}[/] oportunidades · com detalhes: {with_detail} · "
        f"SIGITEC antigo (só resumo): {legacy}"
    )
    if rows and with_detail == 0 and legacy < len(rows):
        console.print(
            "[yellow]Nenhuma oportunidade com detalhes; rode `sync` para ter tema, área etc.[/]"
        )
    for k, label in selected:
        counts, missing = per_column[k]
        if not counts:
            continue
        table = Table(title=label, title_justify="left", header_style="bold green")
        table.add_column("Valor", overflow="fold")
        table.add_column("Qtd.", justify="right")
        table.add_column("%", justify="right", style="dim")
        base = counts.total()
        shown = counts.most_common(top or None)
        for value, n in shown:
            table.add_row(value, str(n), f"{100 * n / base:.0f}")
        footer = [f"{len(counts)} valores distintos"]
        if len(counts) > len(shown):
            footer.append(f"{len(counts) - len(shown)} omitidos (use -n 0)")
        if missing:
            footer.append(f"{missing} sem valor")
        stdout.print()
        stdout.print(table)
        stdout.print(f"[dim]{' · '.join(footer)}[/]")


@cli.command()
@click.argument("terms", metavar="QUERY", nargs=-1)
@status_option
@open_option
@refresh_option
@click.pass_obj
def tui(
    csv_path: Path,
    terms: tuple[str, ...],
    statuses: tuple[str, ...],
    only_open: bool,
    refresh: bool,
) -> None:
    """Navega e filtra as oportunidades numa interface interativa.

    QUERY, --status e --open definem os filtros iniciais.
    """
    from .tui import OpportunitiesApp  # importa o Textual só quando necessário

    rows = list(store.get_rows(csv_path, refresh).values())
    OpportunitiesApp(rows, " ".join(terms), selected_statuses(statuses, only_open)).run()


@cli.command()
@click.argument("shell", type=click.Choice(SHELLS))
def completion(shell: str) -> None:
    """Imprime o script de autocompletar para SHELL (bash, zsh ou fish).

    \b
    bash:  eval "$(sigitec-oportunidades completion bash)"     # no ~/.bashrc
    zsh:   eval "$(sigitec-oportunidades completion zsh)"      # no ~/.zshrc
    fish:  sigitec-oportunidades completion fish \
             > ~/.config/fish/completions/sigitec-oportunidades.fish
    """
    comp_cls = get_completion_class(shell)
    assert comp_cls is not None  # SHELLS só tem shells suportados pelo click
    click.echo(comp_cls(cli, {}, APP_NAME, COMPLETE_VAR).source())


@cli.command()
def skill() -> None:
    """Explica este CLI e a API do SIGITEC (em Markdown)."""
    click.echo(SKILL, nl=False)


def main() -> None:
    try:
        cli(prog_name=APP_NAME)
    except httpx2.HTTPError as e:
        console.print(f"[red]Erro ao acessar a API:[/] {e}")
        sys.exit(1)
