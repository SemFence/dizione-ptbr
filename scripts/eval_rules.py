"""Mede as regras contra o dicionário MFA pt-BR.

Divisão por palavra (estável): 60% treino (só para estimar a tabela e/ɛ, o/ɔ), 20% ajuste (eu olho os erros),
20% teste (só para o número final).

  python scripts/eval_rules.py                 # métricas em treino/ajuste/teste
  python scripts/eval_rules.py --errors 40     # erros mais comuns e palavras erradas no conjunto de ajuste
  python scripts/eval_rules.py --build-table   # reestima src/dizione_ptbr/data/open_table.json com o treino
"""
import argparse, collections, importlib, json, os, re, sys, unicodedata, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
DICT = os.path.join(ROOT, "data", "sources", "portuguese_brazil_mfa.dict")
TABLE = os.path.join(ROOT, "src", "dizione_ptbr", "data", "open_table.json")
nfc = lambda s: unicodedata.normalize("NFC", s)


def normalize_gold(w, ph):
    """Convenções do dicionário que NÃO queremos copiar (o TTS fala [k] e [l] normais nesses casos):
    c→k, ɟ→ɡ (k/g palatalizados); ʎ→l e ɲ→n quando a palavra não tem 'lh'/'nh'."""
    m = {"c": "k", "ɟ": "ɡ"}
    if "lh" not in w: m["ʎ"] = "l"
    if "nh" not in w: m["ɲ"] = "n"
    return [m.get(x, x) for x in ph]


def load_dict():
    lex = collections.defaultdict(list)
    for l in open(DICT, encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if len(p) < 6 or p[0] in ("<eps>", "<unk>"):
            continue
        w = nfc(p[0].lower())
        if not re.fullmatch(r"[a-záàâãéêíóôõúüç]+(-[a-záàâãéêíóôõúüç]+)*", w):
            continue
        lex[w].append((float(p[1]), normalize_gold(w, [nfc(x) for x in p[-1].split()])))
    return lex


FOREIGN = re.compile(r"[kwy]|th|ck|sh|ph|ll|tt|ff|pp|mm|nn|dd|bb|gg|cc|zz|[bcdfghjklmnpqrstvwxz]{3}|^[bcdfghjklmnpqrstvwxz]+$|[bcdfghjklmnpqrstvwxz]$")


def is_regular(w):
    """Palavra portuguesa 'comum': sem k/w/y, sem consoantes dobradas estrangeiras, sem sigla.
    Termina em consoante só se for l, r, z, m, n, s, x (finais normais do português)."""
    if re.search(r"[bcdfghjkpqtvw]$", w) or re.search(r"[kwy]|th|ck|sh|ph|ll|tt|ff|pp|mm|nn|dd|bb|gg|zz|^[^aeiouáàâãéêíóôõú]+$", w):
        return False
    return not re.search(r"[bcdfghjklmnpqrstvwxz]{4}", w)


def split_of(w):
    h = zlib.crc32(w.encode()) % 10
    return "train" if h < 6 else "dev" if h < 8 else "test"


def lev(a, b):
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (x != y))
    return d[-1]


def align(a, b):
    """Pairs (i, j) of aligned positions (None for gaps), by edit distance."""
    n, m = len(a), len(b)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): D[i][0] = i
    for j in range(m + 1): D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i][j] = min(D[i-1][j] + 1, D[i][j-1] + 1, D[i-1][j-1] + (a[i-1] != b[j-1]))
    i, j, out = n, m, []
    while i or j:
        if i and j and D[i][j] == D[i-1][j-1] + (a[i-1] != b[j-1]):
            out.append((i - 1, j - 1)); i, j = i - 1, j - 1
        elif i and D[i][j] == D[i-1][j] + 1:
            out.append((i - 1, None)); i -= 1
        else:
            out.append((None, j - 1)); j -= 1
    return out[::-1]


def predict(g2p, w):
    return [nfc(p) for p, _ in g2p.phonemize_word(w)]


def context_of(w, start, g, width=2):
    return f"{w[max(0, start - width):start]}[{g}]{w[start + len(g):start + len(g) + width]}"


def evaluate(lex, g2p, which, show=0, regular_only=False):
    n = any_ok = top_ok = ph = err = 0
    pairs = collections.Counter(); wrong = []
    ctx = collections.Counter(); ctx_ex = collections.defaultdict(list)
    for w, vs in lex.items():
        if split_of(w) != which or (regular_only and not is_regular(w)):
            continue
        dbg = g2p.phonemize_debug(w)
        pred = [nfc(p) for p, _, _, _ in dbg]
        top = max(vs)[1]
        best = min((v for _, v in vs), key=lambda g: lev(pred, g))
        d = lev(pred, best)
        n += 1; ph += len(best); err += d
        any_ok += d == 0; top_ok += pred == top
        if d:
            wrong.append((d, w, " ".join(pred), " ".join(best)))
            if show:
                for i, j in align(pred, best):
                    if i is None: pairs[("∅", best[j])] += 1
                    elif j is None: pairs[(pred[i], "∅")] += 1
                    elif pred[i] != best[j]: pairs[(pred[i], best[j])] += 1
                    if i is not None and (j is None or pred[i] != best[j]):
                        _, _, st, gg = dbg[i]
                        key = (gg, pred[i], best[j] if j is not None else "∅")
                        ctx[key] += 1
                        if len(ctx_ex[key]) < 3: ctx_ex[key].append(w)
    r = dict(split=which, words=n, any_variant=100 * any_ok / n, top_variant=100 * top_ok / n, per=100 * err / ph)
    return r, pairs, wrong, (ctx, ctx_ex)


def build_table(lex, g2p):
    cnt = collections.defaultdict(collections.Counter)
    for w, vs in lex.items():
        if split_of(w) != "train" or "-" in w:
            continue
        out = g2p.phonemize_word(w)
        idx = [i for i, (_, s) in enumerate(out) if s]
        if len(idx) != 1:
            continue
        i = idx[0]
        # which letter is the stressed vowel? find 'e' or 'o' without accent at the stressed nucleus
        pred = [nfc(p) for p, _ in out]
        if pred[i] not in ("e", "o"):
            continue
        # locate the vowel letter in the word: use the g2p internals
        units = g2p._units(w)
        vidx = [k for k, u in enumerate(units) if u.kind == "V"]
        st = g2p._stress_nucleus([units[k].g for k in vidx], w)
        u = units[vidx[st]]
        sl = g2p._stressed_letter(u.g)
        letter = u.g[sl]
        if letter not in "eo":
            continue                                   # accented: not ambiguous
        top = max(vs)[1]
        for g in {tuple(v) for _, v in vs}:
            pass
        best = min((v for _, v in vs), key=lambda gg: lev(pred, gg))
        mp = {a: b for a, b in align(pred, best) if a is not None}
        j = mp.get(i)
        if j is None:
            continue
        gold = best[j]
        cls = "open" if gold in ("ɛ", "ɔ") else "close" if gold in ("e", "o") else None
        if cls is None:
            continue
        after = u.start + sl + 1
        for L in range(0, 4):
            cnt[f"{letter}|{w[after:after + L]}"][cls] += 1
    table, keep = {}, []
    for key in sorted(cnt, key=lambda k: len(k)):
        c = cnt[key]; dec = "open" if c["open"] > c["close"] else "close"
        v, tail = key.split("|")
        parent = table_lookup(table, v, tail[:-1]) if tail else None
        if tail == "" or (c["open"] + c["close"] >= 3 and dec != parent):
            table[key] = dec
    json.dump(table, open(TABLE, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    return table


def table_lookup(table, v, tail):
    for L in range(len(tail), -1, -1):
        k = f"{v}|{tail[:L]}"
        if k in table: return table[k]
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", type=int, default=0)
    ap.add_argument("--build-table", action="store_true")
    ap.add_argument("--splits", default="train,dev,test")
    ap.add_argument("--regular", action="store_true", help="só palavras portuguesas regulares (sem estrangeirismos/siglas)")
    a = ap.parse_args()
    lex = load_dict()
    print(f"{len(lex):,} palavras no dicionário (só letras): treino {sum(split_of(w)=='train' for w in lex):,}, ajuste {sum(split_of(w)=='dev' for w in lex):,}, teste {sum(split_of(w)=='test' for w in lex):,}")
    g2p = importlib.import_module("dizione_ptbr.g2p")
    if a.build_table:
        if os.path.exists(TABLE): os.remove(TABLE)
        importlib.reload(g2p)
        t = build_table(lex, g2p); print("tabela e/ɛ, o/ɔ:", len(t), "entradas"); importlib.reload(g2p)
    for s in a.splits.split(","):
        r, pairs, wrong, (ctx, ctx_ex) = evaluate(lex, g2p, s, show=a.errors if s == "dev" else 0, regular_only=a.regular)
        print(("[regulares] " if a.regular else "") + f"{r['split']:5} palavras {r['words']:6,} | iguais a alguma variante {r['any_variant']:5.1f}% | iguais à variante principal {r['top_variant']:5.1f}% | erro de fones {r['per']:5.2f}%")
        if a.errors and s == "dev":
            print("  trocas mais comuns (nosso → dicionário):", [(f"{x}→{y}", c) for (x, y), c in pairs.most_common(a.errors // 2)])
            print("  erros por letra [nosso→dicionário] (exemplos):")
            for (gg, pp, bb), c in ctx.most_common(a.errors // 2):
                print(f"    {c:5} [{gg}] {pp}→{bb}   {', '.join(ctx_ex[(gg, pp, bb)])}")
            import random; random.Random(1).shuffle(wrong)
            for d, w, p, g in sorted(wrong[:a.errors], reverse=True)[:a.errors]:
                print(f"   {w:18} nosso: {p:34} dicionário: {g}")
