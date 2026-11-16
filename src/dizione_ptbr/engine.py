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

# Clitic function words are unstressed in running speech even when they are one syllable.
FUNCTION_WORDS = frozenset(
    "o a os as um uma uns umas e de da do das dos em no na nos nas ao aos à às por pelo pela pelos pelas com sem "
    "para pra pro que se me te lhe lhes vos mas ou já".split())
# Letter names, to spell acronyms that have no vowel (RH, CPF, PSG).
LETTER_NAMES = {
    "a": "a", "b": "bê", "c": "cê", "d": "dê", "e": "é", "f": "éfi", "g": "gê", "h": "agá", "i": "i", "j": "jota",
    "k": "cá", "l": "éli", "m": "ême", "n": "êni", "o": "ó", "p": "pê", "q": "quê", "r": "érri", "s": "ési",
    "t": "tê", "u": "u", "v": "vê", "w": "dáblio", "x": "xis", "y": "ípsilon", "z": "zê"}
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
            for line in open(path, encoding="utf-8"):
                w, _, p = line.rstrip("\n").partition("\t")
                _LEXICON[w] = [(t.lstrip("ˈ"), 1 if t.startswith("ˈ") else 0) for t in p.split()]
    return _LEXICON


def pronounce(word: str, use_lexicon: bool = True) -> list[tuple[str, int]]:
    w = unicodedata.normalize("NFC", word.lower())
    lex = lexicon() if use_lexicon else {}
    if w in lex:
        return [(p, 0) for p, _ in lex[w]] if w in FUNCTION_WORDS else lex[w]
    if not re.search(r"[aeiouáàâãéêíóôõú]", w) and len(w) > 1 and w.isalpha():
        out = []
        for c in w:
            out += pronounce(LETTER_NAMES.get(c, c), use_lexicon)
        return out
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


def phonemize(text: str, use_lexicon: bool = True, do_normalize: bool = True) -> Phonemes:
    """Whole text to symbols. Words are separated by <sp>; punctuation is kept as its own symbol."""
    t = normalize(text) if do_normalize else text
    for a, b in _PUNCT_MAP.items():
        t = t.replace(a, b)
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
