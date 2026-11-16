"""Rule-based grapheme-to-phoneme for Brazilian Portuguese.

``phonemize_word("porta")`` -> ``[("p", 0), ("ɔ", 1), ("x", 0), ("t", 0), ("ɐ", 0)]``

Phone inventory (the symbols of the MFA Brazilian Portuguese dictionary):
a b d dʒ e ẽ f i ĩ j j̃ k l m n o õ p s t tʃ u ũ v w w̃ x z ɐ ɐ̃ ɔ ɛ ɡ ɲ ɾ ʃ ʎ ʒ
The second item of each pair is lexical stress: 1 on the stressed vowel, else 0.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import NamedTuple

VOWELS = "aeiouáàâãéêíóôõúü"
ACCENT = set("áàâéêíóôú")           # explicit stress marks (the tilde is handled apart)
STRONG = set("aeoáàâãéêóôõ")
NASAL_OF = {"a": "ɐ̃", "e": "ẽ", "i": "ĩ", "o": "õ", "u": "ũ"}
STOPS = set("pbdɡtk")
NOT_AFTER_STOP = set("lɾwj") | set("aeiouɐɛɔ") | {"ɐ̃", "ẽ", "ĩ", "õ", "ũ", "w̃", "j̃"}
_HERE = os.path.dirname(__file__)


def _load_open_table():
    path = os.path.join(_HERE, "data", "open_table.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


OPEN_TABLE = _load_open_table()   # "e|rt" -> "open" | "close"  (learned from the dictionary)


class Unit(NamedTuple):
    kind: str      # "V" nucleus or "C" consonant unit
    g: str         # letters of the unit (special tokens for silent/glide cases)
    start: int     # offset of the first letter in the word


# ───────────────────────────── 1. letters -> units ─────────────────────────────
def _split_run(run: str) -> list[str]:
    """Split a run of vowel letters into nuclei (one per syllable)."""
    out, cur = [], run[0]
    for c in run[1:]:
        p = cur[-1]
        hiatus = (p in STRONG and c in STRONG and not (p in "ãõ" and c in "oe")) or c in "íú" or p in "íú"
        if hiatus:
            out.append(cur); cur = c
        else:
            cur += c
    out.append(cur)
    return out


def _units(w: str) -> list[Unit]:
    n, i, out = len(w), 0, []
    while i < n:
        c = w[i]
        if c == "ü":
            out.append(Unit("C", "uw", i)); i += 1; continue
        if c in VOWELS:
            j = i
            while j < n and w[j] in VOWELS and w[j] != "ü":
                j += 1
            pos = i
            for piece in _split_run(w[i:j]):
                out.append(Unit("V", piece, pos)); pos += len(piece)
            i = j; continue
        two = w[i:i + 2]
        if two in ("ch", "lh", "nh", "rr", "ss", "sç", "xc"):
            out.append(Unit("C", two, i)); i += 2; continue
        if two == "sc" and i + 2 < n and w[i + 2] in "eéêií":
            out.append(Unit("C", "sc", i)); i += 2; continue
        if c in "qg" and i + 1 < n and w[i + 1] == "u" and i + 2 < n:
            nxt = w[i + 2]
            if nxt in "eéêií":                       # que, qui, gue, gui: the u is silent
                out.append(Unit("C", c + "_", i)); i += 2; continue
            if nxt in "aáâãoóôõ":                    # qua, quo, gua, guo: the u is a glide
                out.append(Unit("C", c, i)); out.append(Unit("C", "uw", i + 1)); i += 2; continue
        out.append(Unit("C", c, i)); i += 1
    return out


# ───────────────────────────── 2. stress ─────────────────────────────
def _stress_nucleus(nuclei: list[str], word: str) -> int:
    if len(nuclei) == 1:
        return 0
    for k, nu in enumerate(nuclei):
        if any(c in ACCENT for c in nu):
            return k
    # comia, tio, alegria, rua: unaccented final -ia/-io/-ie/-ua/-ue/-uo carries the stress on the i/u
    if nuclei[-1] in ("ia", "io", "ie", "ua", "ue", "uo") and re.search(r"(ia|io|ie|ua|ue|uo)(s|m)?$", word) \
            and not any(c in "ãõ" for c in word):
        return len(nuclei) - 1
    for k, nu in enumerate(nuclei):
        if any(c in "ãõ" for c in nu):
            return k
    if re.search(r"(a|e|o|as|es|os|am|em|ens)$", word):
        return len(nuclei) - 2
    return len(nuclei) - 1


def _stressed_letter(nu: str) -> int:
    for k, c in enumerate(nu):
        if c in ACCENT or c in "ãõ":
            return k
    return 0


def _open_or_close(vowel: str, word: str, after: int) -> str:
    tail = word[after:]
    for L in (3, 2, 1, 0):
        key = f"{vowel}|{tail[:L]}"
        if key in OPEN_TABLE:
            return OPEN_TABLE[key]
    return "close"


# ───────────────────────────── 3. units -> phones ─────────────────────────────
def phonemize_word(word: str) -> list[tuple[str, int]]:
    return [(p, s) for p, s, _, _ in phonemize_debug(word)]


def phonemize_debug(word: str):
    """Like phonemize_word, but each item is (phone, stress, unit_start, unit_grapheme) (for error analysis)."""
    w = unicodedata.normalize("NFC", word.lower().strip())
    if "-" in w:
        out = []
        for part in filter(None, w.split("-")):
            out += phonemize_debug(part)
        return out
    units = _units(w)
    vidx = [k for k, u in enumerate(units) if u.kind == "V"]
    if not vidx:
        return [(c, 0, i, c) for i, c in enumerate(w)]
    nuclei = [units[k].g for k in vidx]
    st = _stress_nucleus(nuclei, w)
    stressed_unit = vidx[st]
    last_v = vidx[-1]
    n_units = len(units)
    ph: list[list] = []        # [phone, stress, unit_index]

    def put(p, s=0, k=-1):
        ph.append([p, s, k])

    k = 0
    while k < n_units:
        u = units[k]
        # ───────── vowels
        if u.kind == "V":
            letters = u.g
            is_stressed = k == stressed_unit
            tail = units[k + 1:]
            word_final = k == last_v and all(t == Unit(t.kind, "s", t.start) and t.kind == "C" for t in tail)
            pre = vidx.index(k) < st
            if letters in ("ão", "ãe", "õe", "ãi"):
                first = "õ" if letters == "õe" else "ɐ̃"
                put(first, 1 if is_stressed else 0, k)
                put("w̃" if letters == "ão" else "j̃", 0, k)
                k += 1; continue
            nasal = False
            nasal_nh = bool(tail) and tail[0].kind == "C" and tail[0].g == "nh"
            before_nasal_v = (bool(tail) and tail[0].kind == "C" and tail[0].g in ("m", "n")
                              and k + 2 < n_units and units[k + 2].kind == "V")
            if tail and tail[0].kind == "C" and tail[0].g in ("m", "n"):
                after = units[k + 2] if k + 2 < n_units else None
                nasal = after is None or after.kind == "C"
            nasal = nasal or nasal_nh
            initial_es = (k == 0 and bool(tail) and tail[0].kind == "C" and tail[0].g in ("s", "x")
                          and k + 2 < n_units and units[k + 2].kind == "C")
            sl = _stressed_letter(letters)
            for ci, c in enumerate(letters):
                last_letter = ci == len(letters) - 1
                if ci > 0 and c in "iu":                         # off-glide: ai, ei, oi, au, eu, ou, ui, iu
                    put("j" if c == "i" else "w", 0, k); continue
                if ci == 0 and c == "i" and len(letters) == 2 and letters[1] in "aeo" and not is_stressed and not pre:
                    put("j", 0, k); continue                           # pós-tônico: história, vário, ciência -> j
                s = 1 if (is_stressed and ci == sl) else 0
                base = unicodedata.normalize("NFD", c)[0]
                fin = word_final and last_letter
                if c == "ã": p = "ɐ̃"
                elif c == "õ": p = "õ"
                elif base == "a": p = "ɐ" if ((fin and not s) or (s and before_nasal_v and last_letter)) else "a"
                elif base == "e":
                    if c == "é": p = "ɛ"
                    elif c == "ê": p = "e"
                    elif s: p = "ɛ" if _open_or_close("e", w, u.start + ci + 1) == "open" else "e"
                    elif fin or initial_es: p = "i"
                    else: p = "e"
                elif base == "o":
                    if c == "ó": p = "ɔ"
                    elif c == "ô": p = "o"
                    elif s: p = "ɔ" if _open_or_close("o", w, u.start + ci + 1) == "open" else "o"
                    elif fin: p = "u"
                    else: p = "o"
                else:
                    p = base
                if nasal and last_letter and base in NASAL_OF and c not in "ãõ":
                    p = NASAL_OF[base]
                put(p, s, k)
            if nasal_nh:
                put("j̃", 0, k); k += 2; continue
            if nasal:
                tail_after = "".join(t.g for t in units[k + 2:])
                if letters.endswith("e") and tail_after in ("", "s"):
                    put("j̃", 0, k)
                elif letters.endswith("a") and tail_after == "" and not is_stressed:
                    put("w̃", 0, k)
                k += 2; continue
            k += 1; continue

        # ───────── consonants
        prev_u = units[k - 1] if k else None
        next_u = units[k + 1] if k + 1 < n_units else None
        prev_v = prev_u is not None and prev_u.kind == "V"
        next_v = next_u is not None and next_u.kind == "V"
        nl = next_u.g[:1] if next_u else ""
        c = u.g
        if c == "uw": put("w", 0, k)
        elif c == "h": pass
        elif c == "ch": put("ʃ", 0, k)
        elif c == "lh": put("ʎ", 0, k)
        elif c == "nh": put("ɲ", 0, k)
        elif c == "rr": put("x", 0, k)
        elif c in ("ss", "sç", "ç", "sc", "xc"): put("s", 0, k)
        elif c in ("q", "q_"): put("k", 0, k)
        elif c == "g_": put("ɡ", 0, k)
        elif c == "c": put("s" if (next_v and nl in "eéêií") else "k", 0, k)
        elif c == "g": put("ʒ" if (next_v and nl in "eéêií") else "ɡ", 0, k)
        elif c == "j": put("ʒ", 0, k)
        elif c == "l": put("l" if next_v else "w", 0, k)
        elif c == "r":
            if prev_u is None or (prev_u.kind == "C" and prev_u.g in ("n", "l", "s")): put("x", 0, k)
            elif next_v and prev_u is not None: put("ɾ", 0, k)
            else: put("x", 0, k)
        elif c == "s":
            if prev_v and next_v: put("z", 0, k)
            elif next_u and next_u.kind == "C" and nl in "bdgvzjlmnr" and next_u.g not in ("nh", "lh"): put("z", 0, k)
            else: put("s", 0, k)
        elif c == "z": put("s" if next_u is None else "z", 0, k)
        elif c == "x":
            if prev_u is None: put("ʃ", 0, k)
            elif prev_u.kind == "V" and prev_u.g == "e":                       # ex-
                if not next_v: put("s", 0, k)
                elif k == 1 or w.startswith(("inex", "hex")): put("z", 0, k)   # exame, inexistente
                else: put("k", 0, k); put("s", 0, k)                           # sexo, anexo, reflexo
            else: put("ʃ", 0, k)
        elif c == "y": put("i", 0, k)
        else: put(c, 0, k)                      # b d f k m n p t v w
        k += 1

    # ───────── epenthetic [i] between a stop and a non-liquid consonant (ad-vo-ga-do -> a dʒ i v o ɡ a d u)
    out: list[list] = []
    for idx, (p, s, k) in enumerate(ph):
        out.append([p, s, k])
        nxt = ph[idx + 1] if idx + 1 < len(ph) else None
        if nxt and p in STOPS and nxt[2] != k and nxt[0] not in NOT_AFTER_STOP and units[nxt[2]].g != "x":
            out.append(["i", 0, k])
    # ───────── palatalization: t, d before [i]
    res = []
    for idx, (p, s, k) in enumerate(out):
        nxt = out[idx + 1][0] if idx + 1 < len(out) else ""
        if p == "t" and nxt in ("i", "ĩ"): p = "tʃ"
        elif p == "d" and nxt in ("i", "ĩ"): p = "dʒ"
        res.append((p, s, units[k].start if k >= 0 else -1, units[k].g if k >= 0 else ""))
    return res
