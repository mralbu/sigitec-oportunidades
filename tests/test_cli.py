import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from sigitec_oportunidades import api
from sigitec_oportunidades.cli import DEFAULT_CSV, cli
from sigitec_oportunidades.constants import APP_NAME, CSV_ENVVAR

from .conftest import detail


@pytest.fixture
def run(csv_path: Path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("o teste não deveria acessar a API")

    monkeypatch.setattr(api, "fetch_list", no_network)
    monkeypatch.setattr(api, "fetch_one", no_network)

    def invoke(*args: str):
        result = CliRunner().invoke(cli, ["--csv", str(csv_path), *args])
        assert result.exit_code == 0, result.output
        return result

    return invoke


def test_search_json(run):
    found = json.loads(run("search", "--open", "--json").stdout)
    assert [o["numberOP"] for o in found] == [3459]
    assert found[0]["theme"] == "Produção"


def test_search_table(run):
    assert "OP3400" in run("search", "petrofisica").stdout


def test_show_by_op_markdown(run):
    assert run("show", "OP3459", "--markdown").stdout.startswith("# OP3459 - ")


def test_show_by_id_prefers_current_sigitec(run):
    # O id 2259 é a OP3459 (atual) e a OP900 (antigo).
    assert json.loads(run("show", "2259", "--json").stdout)["numberOP"] == 3459


def test_show_online_prefers_fresh_detail(run, monkeypatch):
    monkeypatch.setattr(
        api, "fetch_one", lambda opp_id: detail(3459, opp_id, theme="Novo", status="F")
    )
    data = json.loads(run("show", "OP3459", "--online", "--json").stdout)
    assert data["theme"] == "Novo"
    assert data["status"] == "F"
    assert data["numberOP"] == 3459  # int da linha, não o texto do detalhe
    assert data["publicationDate"] is not None  # vem nulo no detalhe; fica o do CSV


def test_csv_defaults_to_user_data_dir(monkeypatch):
    monkeypatch.delenv(CSV_ENVVAR, raising=False)
    ctx = cli.make_context(APP_NAME, ["skill"])
    assert ctx.params["csv_path"] == DEFAULT_CSV
    assert DEFAULT_CSV.is_absolute()


def test_show_writes_file(run, tmp_path: Path):
    out = tmp_path / "op.md"
    run("show", "OP3459", "-o", str(out))
    assert out.read_text(encoding="utf-8").startswith("# OP3459")


def test_show_unknown_op(csv_path: Path):
    result = CliRunner().invoke(cli, ["--csv", str(csv_path), "show", "OP1"])
    assert result.exit_code != 0
    assert "OP1 não encontrada" in result.output


def test_stats_json(run):
    data = json.loads(run("stats", "-c", "status", "-c", "theme", "--json").stdout)
    assert data["total"] == 3
    assert data["legacy"] == 1
    assert data["columns"]["status"]["values"] == {
        "Finalizada": 2,
        "Aberta para envio de proposta": 1,
    }
    assert data["columns"]["theme"]["missing"] == 2


def test_stats_table(run):
    out = run("stats", "-c", "intendedTrl").stdout
    assert "TRL pretendido" in out
    assert "TRL7-9" in out


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion(run, shell):
    assert "_SIGITEC_OPORTUNIDADES_COMPLETE" in run("completion", shell).stdout


def test_skill(run):
    assert run("skill").stdout.startswith("# sigitec-oportunidades")
