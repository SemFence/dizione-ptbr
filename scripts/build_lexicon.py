"""Constrói src/dizione_ptbr/data/lexicon.tsv a partir do dicionário MFA pt-BR (CC BY 4.0).

- uma pronúncia por palavra: a variante de maior probabilidade;
- as convenções do dicionário que não queremos copiar são normalizadas (c→k, ɟ→ɡ; ʎ→l e ɲ→n em palavras sem lh/nh);
- o dicionário não marca a tônica: ela vem das regras (tonicidade por ortografia) e é transportada para a vogal
  correspondente da pronúncia do dicionário por alinhamento.
"""
import collections, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "scripts"))
from dizione_ptbr import g2p
from dizione_ptbr.symbols import PHONES, VOWEL_PHONES
import eval_rules as E

lex = E.load_dict()
valid = set(PHONES)
rows, skipped = [], collections.Counter()
for w in sorted(lex):
    vs = lex[w]
    prob, gold = max(vs, key=lambda v: v[0])
    if any(p not in valid for p in gold):
        skipped["fone fora do inventário"] += 1; continue
    dbg = g2p.phonemize_debug(w)
    pred = [E.nfc(p) for p, _, _, _ in dbg]
    sidx = [i for i, (_, s, _, _) in enumerate(dbg) if s]
    mark = -1
    if sidx:
        mp = {i: j for i, j in E.align(pred, gold) if i is not None and j is not None}
        j = mp.get(sidx[0])
        cand = [j] if j is not None else []
        if j is None or gold[j] not in VOWEL_PHONES:
            cand = [k for k in range(len(gold)) if gold[k] in VOWEL_PHONES and (j is None or abs(k - j) <= 2)]
            cand.sort(key=lambda k: abs(k - (j if j is not None else 0)))
        mark = cand[0] if cand else -1
    if mark < 0:
        vs_ = [k for k, p in enumerate(gold) if p in VOWEL_PHONES]
        mark = vs_[0] if len(vs_) == 1 else -1
    toks = [("ˈ" + p) if k == mark else p for k, p in enumerate(gold)]
    rows.append((w, " ".join(toks)))
out = os.path.join(ROOT, "src", "dizione_ptbr", "data", "lexicon.tsv")
with open(out, "w", encoding="utf-8") as f:
    for w, p in rows:
        f.write(f"{w}\t{p}\n")
print(f"{len(rows):,} palavras gravadas em {out} ({os.path.getsize(out)/1e6:.2f} MB); ignoradas: {dict(skipped)}")
print("sem tônica marcada:", sum("ˈ" not in p for _, p in rows))
