from dataclasses import dataclass, field
from pathlib import Path

import pytest

from sigitec_oportunidades import api, store
from sigitec_oportunidades.constants import COLUMNS

from .conftest import detail, summary


@pytest.mark.parametrize(
    ("value", "cell"),
    [
        (None, ""),
        (True, "true"),
        (False, "false"),
        (["a", "b"], "a | b"),
        (3, "3"),
        ("x\r\ny", "x\ny"),
    ],
)
def test_to_cell(value, cell):
    assert store.to_cell(value) == cell


def test_save_and_load_roundtrip(csv_path: Path, rows: dict[int, dict]):
    loaded = store.load_cache(csv_path)
    assert list(loaded) == [3459, 3400, 900]
    row = loaded[3459]
    assert row["id"] == 2259
    assert row["numberOP"] == 3459
    assert row["theme"] == "Produção"
    assert row["selectedPartnership"] == ["UNICAMP", "PUC-Rio"]
    assert row["nodeBackend"] is False
    assert loaded[900]["nodeBackend"] is True
    assert loaded[3400]["theme"] is None


def test_csv_has_fixed_columns(csv_path: Path):
    header = csv_path.read_text(encoding="utf-8-sig").splitlines()[0]
    assert header.split(",") == COLUMNS


def test_load_missing_file(tmp_path: Path):
    assert store.load_cache(tmp_path / "nada.csv") == {}


def test_merge_summary_wins_over_detail():
    row = store.merge(summary(1, 10, status="J"), detail(1, 10, status="A"), None)
    assert row["status"] == "J"
    assert row["numberOP"] == 1  # o int da listagem prevalece sobre o texto do detalhe
    assert row["theme"] == "Produção"
    assert row["detailFetchedAt"]
    assert row["url"].endswith("/v2/public/opportunity/10")


def test_merge_without_detail_keeps_previous_but_marks_refetch():
    previous = store.merge(summary(1, 10), detail(1, 10), None)
    row = store.merge(summary(1, 10, status="J"), None, previous)
    assert row["theme"] == "Produção"
    assert row["detailFetchedAt"] is None


def test_legacy_url():
    row = store.merge(summary(1, 10, nodeBackend=True), None, None)
    assert "/opportunitysigitec/10" in row["url"]


@dataclass
class FakeAPI:
    """Substitui a API: `listing` é a listagem e `details` os detalhes por id."""

    listing: list[dict] = field(default_factory=list)
    details: dict[int, dict] = field(default_factory=dict)
    requested: list[list[int]] = field(default_factory=list)

    def fetch_list(self) -> list[dict]:
        return self.listing

    async def fetch_details(self, ids, concurrency, retries, max_failures):
        self.requested.append(sorted(ids))
        found = {i: self.details[i] for i in ids if i in self.details}
        return found, [i for i in ids if i not in found], False


@pytest.fixture
def fake_api(monkeypatch) -> FakeAPI:
    fake = FakeAPI()
    monkeypatch.setattr(api, "fetch_list", fake.fetch_list)
    monkeypatch.setattr(api, "fetch_details", fake.fetch_details)
    return fake


def test_sync_is_incremental(tmp_path: Path, fake_api):
    path = tmp_path / "op.csv"
    fake_api.listing = [summary(1, 10), summary(2, 20), summary(3, 10, nodeBackend=True)]
    fake_api.details = {10: detail(1, 10), 20: detail(2, 20)}

    rows = store.run_sync(path)
    assert fake_api.requested == [[10, 20]]  # o antigo (OP3) não tem detalhe acessível
    assert rows[1]["theme"] == "Produção"
    assert rows[3]["nodeBackend"] is True

    # Nada mudou: nenhum detalhe novo. Só o OP2 mudou de status: só ele é baixado de novo.
    store.run_sync(path)
    fake_api.listing[1] = summary(2, 20, status="J")
    rows = store.run_sync(path)
    assert fake_api.requested == [[10, 20], [20]]
    assert rows[2]["status"] == "J"
    assert store.load_cache(path)[1]["theme"] == "Produção"


def test_sync_failed_detail_is_retried_next_time(tmp_path: Path, fake_api):
    path = tmp_path / "op.csv"
    fake_api.listing = [summary(1, 10)]
    rows = store.run_sync(path)
    assert not rows[1].get("detailFetchedAt")

    fake_api.details = {10: detail(1, 10)}
    rows = store.run_sync(path)
    assert fake_api.requested == [[10], [10]]
    assert rows[1]["detailFetchedAt"]


def test_sync_no_details(tmp_path: Path, fake_api):
    fake_api.listing = [summary(1, 10)]
    store.run_sync(tmp_path / "op.csv", details=False)
    assert fake_api.requested == []
