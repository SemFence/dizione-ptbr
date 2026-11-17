"""Text -> phoneme ids: normalization, lexicon (MFA, CC BY 4.0), rule fallback, punctuation and pauses.

>>> from dizione_ptbr import phonemize
>>> r = phonemize("Oi, tudo bem?")
>>> r.symbols      # ['<bos>', 'o', 'j', ... , '?', '<eos>']
>>> r.ids, r.stress
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field

from .g2p import phonemize_word
from .normalize import normalize
from .symbols import BOS, EOS, ID, PHONES, PUNCTUATION, SP, SYMBOLS, UNK

VERSION = 1   # bump when the symbols or the shape of the output change (models record it); lexicon fixes keep it

# Clitic function words are unstressed in running speech even when they are one syllable.
FUNCTION_WORDS = frozenset(
    "o a os as um uma uns umas e de da do das dos em no na nos nas ao aos à às por pelo pela pelos pelas com sem "
    "para pra pro que se me te lhe lhes vos mas ou já".split())
# Letter names, to spell acronyms that have no vowel (RH, CPF, PSG).
LETTER_NAMES = {
    "a": "a", "b": "bê", "c": "cê", "d": "dê", "e": "é", "f": "éfi", "g": "gê", "h": "agá", "i": "i", "j": "jota",
    "k": "cá", "l": "éli", "m": "ême", "n": "êni", "o": "ó", "p": "pê", "q": "quê", "r": "érri", "s": "ésse",
    "t": "tê", "u": "u", "v": "vê", "w": "dáblio", "x": "xis", "y": "ípsilon", "z": "zê"}
# Siglas em maiúsculas (2 a 5 letras) são soletradas: GPU, CPU, USB. As de SPELLED são soletradas mesmo sendo
# também uma palavra do léxico (IA, TI); as de AS_WORD são lidas como palavra (PIX, ONU, NASA).
SPELLED = frozenset("ia ti tv pc rg ui ux ai ue eua".split())
AS_WORD = frozenset(
    "onu otan nasa fifa unesco unicef pix enem sus cep detran ibama inmetro sebrae senai sesc sesi usp unicamp "
    "embrapa anatel anvisa aneel inpe opep ok".split())
_CAPS_RUNS = re.compile(r"[A-Z]{2,}(?![a-z])|[A-Z]?[a-z]+|[A-Z]")
_LEXICON: dict[str, list[tuple[str, int]]] | None = None
_PHONE_SET = set(PHONES)
_TOKEN = re.compile(r"[a-záàâãéêíóôõúüç]+(?:-[a-záàâãéêíóôõúüç]+)*|[,.;:?!…—\"'()]|\s+|\S", re.I)
_PUNCT_MAP = {"“": '"', "”": '"', "‘": "'", "’": "'", "–": "—", "-": "—", "[": "(", "]": ")", "…": "…", "«": '"', "»": '"'}


def lexicon() -> dict[str, list[tuple[str, int]]]:
    """word -> [(phone, stress)], loaded once from data/lexicon.tsv."""
    global _LEXICON
    if _LEXICON is None:
        _LEXICON = {}
        path = os.path.join(os.path.dirname(__file__), "data", "lexicon.tsv")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as lexicon:
                for line in lexicon:
                    w, _, p = line.rstrip("\n").partition("\t")
                    _LEXICON[w] = [(t.lstrip("ˈ"), 1 if t.startswith("ˈ") else 0) for t in p.split()]
    return _LEXICON


def _spell(w: str, use_lexicon: bool) -> list[tuple[str, int]]:
    """Letter names in a row. Only the last one is stressed (GPU = jê-pê-ˈu): stressing every letter makes the
    acronym come out slow, one beat per letter, with the last sound far from the others."""
    out = []
    for c in w:
        out += pronounce(LETTER_NAMES.get(c, c), use_lexicon)
    last = max((i for i, (_, st) in enumerate(out) if st), default=-1)
    return [(p, 1 if i == last else 0) for i, (p, _) in enumerate(out)]


def pronounce(word: str, use_lexicon: bool = True) -> list[tuple[str, int]]:
    word = unicodedata.normalize("NFC", word)
    w = word.lower()
    lex = lexicon() if use_lexicon else {}
    if word.isascii() and word.isalpha() and word.isupper() and 2 <= len(word) <= 5 and w not in AS_WORD \
            and (w in SPELLED or w not in lex):
        return _spell(w, use_lexicon)
    if re.fullmatch(r"[A-Z]{2,5}s", word) and word[:-1].lower() not in AS_WORD:
        return _spell(w[:-1], use_lexicon) + [("s", 0)]   # GPUs, APIs: plural of a spelled acronym
    if w not in lex and word.isascii() and word.isalpha() and re.search(r"[A-Z]{2}", word) and re.search(r"[a-z]", word):
        out = []                                   # WebGPU -> Web + GPU
        for part in _CAPS_RUNS.findall(word):
            out += pronounce(part, use_lexicon)
        return out
    if w in lex:
        return [(p, 0) for p, _ in lex[w]] if w in FUNCTION_WORDS else lex[w]
    if not re.search(r"[aeiouáàâãéêíóôõú]", w) and len(w) > 1 and w.isalpha():
        return _spell(w, use_lexicon)
    if "-" in w:
        out = []
        for part in filter(None, w.split("-")):
            out += pronounce(part, use_lexicon)
        return out
    ph = phonemize_word(w)
    return [(p, 0) for p, _ in ph] if w in FUNCTION_WORDS else ph


@dataclass
class Phonemes:
    symbols: list[str] = field(default_factory=list)
    stress: list[int] = field(default_factory=list)       # 0 none, 1 primary

    @property
    def ids(self) -> list[int]:
        return [ID.get(s, ID[UNK]) for s in self.symbols]

    def add(self, s: str, stress: int = 0) -> None:
        self.symbols.append(s if s in ID else UNK); self.stress.append(stress)

    def __len__(self):
        return len(self.symbols)

    def __str__(self):
        return " ".join(("ˈ" if st else "") + s for s, st in zip(self.symbols, self.stress))


def _clean(text: str, do_normalize: bool = True) -> str:
    t = normalize(text) if do_normalize else text
    for a, b in _PUNCT_MAP.items():
        t = t.replace(a, b)
    return t


def pieces(text: str, use_lexicon: bool = True) -> list[tuple[bool, object]]:
    """The interface tiny-voca's "own" front end expects: ``(is_punctuation, value)`` items, where the value of a
    text piece is a list of words and each word a list of ``(phone, stress)``."""
    out: list[tuple[bool, object]] = []
    words: list[list[tuple[str, int]]] = []
    for m in _TOKEN.finditer(_clean(text)):
        tok = m.group(0)
        if tok.isspace():
            continue
        if re.match(r"[a-záàâãéêíóôõúüç]", tok, re.I):
            words.append(pronounce(tok, use_lexicon))
        elif tok in PUNCTUATION:
            if words:
                out.append((False, words)); words = []
            out.append((True, tok))
    if words:
        out.append((False, words))
    return out


def identity() -> dict:
    """Fingerprint of everything that decides the output (code, lexicon, table, symbols)."""
    import hashlib
    here = os.path.dirname(__file__)
    h = hashlib.sha256()
    for rel in ("data/lexicon.tsv", "data/open_table.json", "g2p.py", "normalize.py", "engine.py", "symbols.py"):
        with open(os.path.join(here, rel), "rb") as f:
            h.update(rel.encode()); h.update(f.read())
    return {"name": "dizione-ptbr", "version": VERSION, "fingerprint": h.hexdigest()}


def phonemize(text: str, use_lexicon: bool = True, do_normalize: bool = True) -> Phonemes:
    """Whole text to symbols. Words are separated by <sp>; punctuation is kept as its own symbol."""
    t = _clean(text, do_normalize)
    out = Phonemes()
    out.add(BOS)
    pending_space = False
    for m in _TOKEN.finditer(t):
        tok = m.group(0)
        if tok.isspace():
            pending_space = len(out) > 1
            continue
        if re.match(r"[a-záàâãéêíóôõúüç]", tok, re.I):
            if pending_space and out.symbols[-1] not in PUNCTUATION[6:]:
                out.add(SP)
            elif pending_space:
                out.add(SP)
            pending_space = False
            for ph, st in pronounce(tok, use_lexicon):
                out.add(ph, st)
        elif tok in PUNCTUATION:
            out.add(tok)
            pending_space = False if tok in "(\"'" else pending_space
        # anything else (symbols, leftover digits, emoji) is skipped
    out.add(EOS)
    return out
