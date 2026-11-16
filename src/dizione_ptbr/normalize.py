"""Text normalization for Brazilian Portuguese: digits, money, percent, times, dates, ordinals, abbreviations.

``normalize("Paguei R$ 15,50 às 10h30.")`` -> ``"Paguei quinze reais e cinquenta centavos às dez horas e trinta minutos."``
Pure Python with no dependencies, written so it can be ported line by line to JavaScript.
"""
from __future__ import annotations

import re

UNITS = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze",
         "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
TENS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
HUNDREDS = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos",
            "oitocentos", "novecentos"]
FEM = {"um": "uma", "dois": "duas"}
FEMININE_NOUNS = "horas?|semanas?|vez|vezes|pessoas?|casas?|coisas?|mulheres|mulher|meninas?|cadeiras?|páginas?|partes?|crianças?|famílias?|aulas?"
MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
          "novembro", "dezembro"]
ORD_M = {1: "primeiro", 2: "segundo", 3: "terceiro", 4: "quarto", 5: "quinto", 6: "sexto", 7: "sétimo", 8: "oitavo",
         9: "nono", 10: "décimo", 20: "vigésimo", 30: "trigésimo", 40: "quadragésimo", 50: "quinquagésimo",
         60: "sexagésimo", 70: "septuagésimo", 80: "octogésimo", 90: "nonagésimo", 100: "centésimo"}
ABBREVIATIONS = {
    "dr": "doutor", "dra": "doutora", "sr": "senhor", "sra": "senhora", "srta": "senhorita", "prof": "professor",
    "profa": "professora", "av": "avenida", "tel": "telefone", "etc": "etcétera", "obs": "observação",
    "vc": "você", "vcs": "vocês", "pq": "porque", "tb": "também", "tbm": "também", "blz": "beleza", "msg": "mensagem",
    "obg": "obrigado", "td": "tudo", "hj": "hoje", "q": "que", "ñ": "não",
}


def _fem(words: str, fem: bool) -> str:
    if not fem:
        return words
    out = []
    for w in words.split():
        w = FEM.get(w, w)
        if w.endswith("entos") and w != "cento":
            w = w[:-2] + "as"
        out.append(w)
    return " ".join(out)


def _below_1000(n: int) -> str:
    if n < 20:
        return UNITS[n]
    if n < 100:
        t, u = divmod(n, 10)
        return TENS[t] + (f" e {UNITS[u]}" if u else "")
    if n == 100:
        return "cem"
    h, r = divmod(n, 100)
    return HUNDREDS[h] + (f" e {_below_1000(r)}" if r else "")


def number_to_words(n: int, fem: bool = False) -> str:
    """Cardinal in words, 0 .. 999 999 999 999. ``fem`` gives uma/duas/duzentas… (for 'horas')."""
    if n < 0:
        return "menos " + number_to_words(-n, fem)
    if n == 0:
        return "zero"
    if n >= 10**12:
        return " ".join(number_to_words(int(d)) for d in str(n))
    scales = [(10**9, "bilhão", "bilhões"), (10**6, "milhão", "milhões"), (10**3, "mil", "mil")]
    parts, rest = [], n
    for value, sing, plur in scales:
        g, rest = divmod(rest, value)
        if g:
            if value == 10**3:
                parts.append(("mil" if g == 1 else _fem(_below_1000(g), fem) + " mil", g))
            else:
                parts.append((f"{_below_1000(g)} {sing if g == 1 else plur}", g))
    if rest:
        parts.append((_fem(_below_1000(rest), fem), rest))
    out = parts[0][0]
    for i, (txt, g) in enumerate(parts[1:], 1):
        last = i == len(parts) - 1
        out += (" e " if last and (g < 100 or g % 100 == 0) else " ") + txt
    return out


def _decimal(frac: str) -> str:
    if frac.startswith("0") or len(frac) > 3:
        return " ".join(number_to_words(int(d)) for d in frac)
    return number_to_words(int(frac))


def _money(m: re.Match) -> str:
    whole = int(m.group(1).replace(".", ""))
    cents = int((m.group(2) or "0").ljust(2, "0")[:2])
    out = []
    if whole:
        out.append(f"{number_to_words(whole)} {'real' if whole == 1 else 'reais'}")
    if cents:
        out.append(f"{number_to_words(cents)} {'centavo' if cents == 1 else 'centavos'}")
    return " e ".join(out) or "zero reais"


def _percent(m: re.Match) -> str:
    n = number_to_words(int(m.group(1).replace(".", "")))
    return f"{n}{' vírgula ' + _decimal(m.group(2)) if m.group(2) else ''} por cento"


def _hours(h: int) -> str:
    return f"{number_to_words(h, fem=True)} {'hora' if h == 1 else 'horas'}"


def _time(m: re.Match) -> str:
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if h > 24 or mi > 59:
        return m.group(0)
    out = _hours(h)
    if mi:
        out += f" e {number_to_words(mi)} {'minuto' if mi == 1 else 'minutos'}"
    return out


def _date(m: re.Match) -> str:
    d, mo = int(m.group(1)), int(m.group(2))
    if not (1 <= d <= 31 and 1 <= mo <= 12):
        return m.group(0)
    day = "primeiro" if d == 1 else number_to_words(d)
    out = f"{day} de {MONTHS[mo - 1]}"
    if m.group(3):
        y = int(m.group(3)); y = y + 2000 if y < 100 else y
        out += f" de {number_to_words(y)}"
    return out


def _ordinal(m: re.Match) -> str:
    n, fem = int(m.group(1)), m.group(2) in ("ª", "a")
    if n in ORD_M:
        w = ORD_M[n]
    elif 10 < n < 100 and n % 10 and (n // 10 * 10) in ORD_M:
        w = ORD_M[n // 10 * 10] + " " + ORD_M[n % 10]
    else:
        return m.group(0)
    return " ".join(x[:-1] + "a" if x.endswith("o") else x for x in w.split()) if fem else w


def _abbr(m: re.Match) -> str:
    rep = ABBREVIATIONS.get(m.group(1).lower())
    if rep is None:
        return m.group(0)
    return rep[0].upper() + rep[1:] if m.group(1)[0].isupper() and len(m.group(1)) > 1 else rep


def normalize(text: str) -> str:
    t = text
    t = re.sub(r"R\$\s*(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?", _money, t)
    t = re.sub(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?\s*%", _percent, t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?\b", _date, t)
    t = re.sub(r"\b(\d{1,2})(?:h|:)(\d{2})?(?!\d)", _time, t)
    t = re.sub(r"\b(\d+)\s?([ºª])", _ordinal, t)
    t = re.sub(r"(\d{1,3}(?:\.\d{3})+|\d+),(\d+)", lambda m: f"{number_to_words(int(m.group(1).replace('.', '')))} vírgula {_decimal(m.group(2))}", t)
    # feminine nouns: "21 horas" -> "vinte e uma horas"
    t = re.sub(r"\b(\d{1,3}(?:\.\d{3})*|\d+)(\s+)(" + FEMININE_NOUNS + r")\b",
               lambda m: number_to_words(int(m.group(1).replace(".", "")), fem=True) + m.group(2) + m.group(3), t)
    t = re.sub(r"\d{1,3}(?:\.\d{3})+|\d+", lambda m: number_to_words(int(m.group(0).replace(".", ""))), t)
    # abbreviations, with or without the final dot ("Dr." and "Dr" -> doutor)
    t = re.sub(r"\b([A-Za-zñ]{1,5})\b\.?",
               lambda m: _abbr(m), t)
    return re.sub(r"[ \t]+", " ", t).strip()
