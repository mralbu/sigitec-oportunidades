import pytest

from sigitec_oportunidades import store
from sigitec_oportunidades.fixtext import fix_record, fix_text


@pytest.mark.parametrize(
    ("raw", "fixed"),
    [
        (
            "Itens:\n¿\tMapeamento sísmico;\n¿ Validação",
            "Itens:\n•\tMapeamento sísmico;\n• Validação",
        ),
        ("Resultado 1 ¿ Metodologia", "Resultado 1 – Metodologia"),
        ("de 16¿20 t e pp. 2583¿2607.", "de 16–20 t e pp. 2583–2607."),
        ("um grande ¿gargalo¿ para", "um grande “gargalo” para"),
        ("manifold em ¿Y¿, a ser", "manifold em “Y”, a ser"),
        ("Sudeste (¿caso base¿)", "Sudeste (“caso base”)"),
        ("aqui ¿Mero 4¿).", "aqui “Mero 4”)."),
        ("pluma de CO¿. Gases: CO¿, N¿, H¿S e H¿O", "pluma de CO₂. Gases: CO₂, N₂, H₂S e H₂O"),
        ("(tCO¿e/t CDR) e 3 mg N-NH¿/L", "(tCO₂e/t CDR) e 3 mg N-NH₄/L"),
        ("HCR 2¿, HCR 2¿) e 1,5¿ até 3¿.", "HCR 2″, HCR 2″) e 1,5″ até 3″."),
        ("de 4 a 6 ¿C", "de 4 a 6 °C"),
        ("lâmina d¿água, O¿Brien, ROV¿s", "lâmina d’água, O’Brien, ROV’s"),
        ("Falhas Cedro¿Rio Doce", "Falhas Cedro–Rio Doce"),
        # Ambíguos: ficam como estão.
        ("Jimenez-Mart¿nez", "Jimenez-Mart¿nez"),
        ("usuário¿modelo", "usuário¿modelo"),
        ("entre 680 e 730¿°C", "entre 680 e 730¿°C"),
        ("sem nada a corrigir – “ok”", "sem nada a corrigir – “ok”"),
    ],
)
def test_fix_text(raw, fixed):
    assert fix_text(raw) == fixed
    assert fix_text(fixed) == fixed  # idempotente


def test_fix_record():
    d = {"id": 1, "titleOP": "CO¿", "selectedPartnership": ["A ¿ B"], "live": None}
    assert fix_record(d) == {
        "id": 1,
        "titleOP": "CO₂",
        "selectedPartnership": ["A – B"],
        "live": None,
    }


def test_load_cache_fixes_old_csv(tmp_path):
    path = tmp_path / "old.csv"
    path.write_text("numberOP,id,titleOP\n3483,2284,Armazenamento de CO¿\n", encoding="utf-8-sig")
    assert store.load_cache(path)[3483]["titleOP"] == "Armazenamento de CO₂"
