"""Reconstrói caracteres que o SIGITEC trocou por "¿".

O SIGITEC novo guarda os textos numa codificação de 1 byte (Latin-1): tudo o que não
cabe nela (marcadores •, travessões –, aspas “ ”, apóstrofos ’, subscritos ₂…) chega
da API como "¿". O caractere original se perdeu na origem; aqui ele é deduzido pelo
contexto, só nos padrões sem ambiguidade. O resto (ex.: "Mart¿nez") fica como está.
As regras são idempotentes: aplicá-las de novo não muda o texto.
"""

import re

BAD = "¿"
L = r"[^\W\d_]"  # letra (com acentos)

RULES: list[tuple[re.Pattern[str], str]] = [
    # Marcador de lista colado do Word: "¿\tItem" no começo da linha.
    (re.compile(rf"^([ \t]*){BAD}(?=[ \t])", re.M), r"\1•"),
    # Fórmulas químicas (antes das aspas, para "CO¿ " não virar aspa de fechamento).
    (re.compile(rf"(?<![A-Za-z])(t?CO){BAD}"), r"\1₂"),
    (re.compile(rf"(?<![A-Za-z])H{BAD}(?=[SO](?![A-Za-z]))"), "H₂"),
    (re.compile(rf"(?<![A-Za-z])NH{BAD}(?![A-Za-z])"), "NH₄"),
    (re.compile(rf"(?<![A-Za-z])N{BAD}(?![A-Za-z])"), "N₂"),
    # Travessão entre espaços e intervalos numéricos (16¿20, 2583¿2607).
    (re.compile(rf"(?<= ){BAD}(?= )"), "–"),
    (re.compile(rf"(?<=\d){BAD}(?=\d)"), "–"),
    # Aspas em par na mesma linha: ¿palavra¿ → “palavra”.
    (
        re.compile(rf"(?<![^\s(\[/]){BAD}(?=[^\W_])([^{BAD}\n]*?(?<=\S)){BAD}(?!\w)", re.M),
        r"“\1”",
    ),
    # Graus Celsius (℃, que também não cabe em Latin-1): "4 a 6 ¿C".
    (re.compile(rf"(?<=\d ){BAD}C\b"), "°C"),
    # Polegadas: HCR 2¿, 1,5¿.
    (re.compile(rf"(?<=\d){BAD}(?=[\s,.;:)]|$)", re.M), "″"),
    # Apóstrofos: d¿água, O¿Brien, ROV¿s.
    (re.compile(rf"(?<=\b[dD]){BAD}(?=[aeiouáéíóúâêôãõ])"), "’"),
    (re.compile(rf"(?<=\bO){BAD}(?=[A-Z][a-z])"), "’"),
    (re.compile(rf"(?<=[A-Z]){BAD}(?=s\b)"), "’"),
    # Hífen/travessão entre palavras, quando a segunda começa com maiúscula
    # (Cedro¿Rio Doce, Cenomaniano¿Turoniano).
    (re.compile(rf"(?<={L}{L}){BAD}(?=[A-ZÀ-Þ][a-zà-ÿ])"), "–"),
]


def fix_text(text: str) -> str:
    if BAD not in text:
        return text
    for pattern, repl in RULES:
        text = pattern.sub(repl, text)
    return text


def fix_record(d: dict) -> dict:
    """Aplica `fix_text` a todos os campos de texto (e listas de texto) do registro."""
    out = {}
    for k, v in d.items():
        if isinstance(v, str):
            v = fix_text(v)
        elif isinstance(v, list):
            v = [fix_text(x) if isinstance(x, str) else x for x in v]
        out[k] = v
    return out
