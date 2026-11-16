"""Sonda: para um tipo de unidade, mostra o que o dicionário (treino) tem alinhado a ela, por contexto.
  python scripts/probe.py a            # unidade 'a' (vogal)  -> distribuição do fone do dicionário por contexto
"""
import collections, importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_rules as E
g2p = importlib.import_module("dizione_ptbr.g2p")
lex = E.load_dict()
target = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "ctx"
cnt = collections.defaultdict(collections.Counter)
for w, vs in lex.items():
    if E.split_of(w) != "train": continue
    dbg = g2p.phonemize_debug(w)
    pred = [E.nfc(p) for p, _, _, _ in dbg]
    best = min((v for _, v in vs), key=lambda g: E.lev(pred, g))
    mp = {i: j for i, j in E.align(pred, best) if i is not None}
    nucs = [u for u in g2p._units(w) if u.kind == "V"]
    for i, (p, s, st, gg) in enumerate(dbg):
        if gg != target: continue
        j = mp.get(i); gold = best[j] if j is not None else "∅"
        rest = w[st + len(gg):]
        final = rest in ("", "s")
        stress = "T" if s else ("final" if final else "atona")
        if mode == "ctx": key = (stress, rest[:1])
        elif mode == "next2": key = (stress, rest[:2])
        elif mode == "prev": key = (stress, w[max(0, st - 1):st])
        else: key = (stress,)
        cnt[key][gold] += 1
for key, c in sorted(cnt.items(), key=lambda kv: -sum(kv[1].values()))[:int(os.environ.get("TOP", 30))]:
    tot = sum(c.values()); print(f"{str(key):22} n={tot:5}  " + "  ".join(f"{k}:{100*v/tot:.0f}%" for k, v in c.most_common(4)))
