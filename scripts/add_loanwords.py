"""Grava em src/dizione_ptbr/data/lexicon.tsv as palavras de data/loanwords.tsv, com a pronúncia que as regras dão
para a grafia como se fala (substitui a entrada do dicionário, quando houver).   python scripts/add_loanwords.py"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from dizione_ptbr import g2p

LEXICON = os.path.join(ROOT, "src", "dizione_ptbr", "data", "lexicon.tsv")
loans = {}
with open(os.path.join(ROOT, "data", "loanwords.tsv"), encoding="utf-8") as f:
    for line in f:
        if line.strip() and not line.startswith("#"):
            word, spoken = line.rstrip("\n").split("\t")
            loans[word.lower()] = " ".join(("ˈ" + p) if s else p for p, s in g2p.phonemize_word(spoken.lower()))
rows = {}
with open(LEXICON, encoding="utf-8") as f:
    for line in f:
        w, _, p = line.rstrip("\n").partition("\t")
        rows[w] = p
replaced = sum(w in rows for w in loans)
rows.update(loans)
with open(LEXICON, "w", encoding="utf-8") as f:
    for w in sorted(rows):
        f.write(f"{w}\t{rows[w]}\n")
print(f"{len(loans)} palavras de outras línguas: {replaced} substituídas, {len(loans) - replaced} novas")
