"""Writes js/test/golden.json: what the Python implementation produces, for the TypeScript port to match exactly."""
import json, sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dizione_ptbr import phonemize, pronounce, pieces, normalize, number_to_words
from dizione_ptbr.engine import lexicon

root = Path(__file__).resolve().parents[1]
corpus = Path.home() / "Projects/fun/ptbr-voz-dataset/frases/corpus.jsonl"
sentences = [json.loads(l)["text"] for l in open(corpus, encoding="utf-8")]
edge = [
    "Oi, tudo bem? Paguei R$ 15,50 às 10h30.", "Dr. Silva chegou às 21 horas.", "Dra. Ana e o Sr. João, vc viu?",
    "RH, CPF e PSG são siglas.", "Eram 1.234.567 pessoas, 3,14% e 1º lugar, 2ª vez, 21ª aula.", "Nasceu em 05/03/1990 e 1/1/24.",
    "Faltam 2 horas e 1 hora; 101 casas, 200 coisas, 1000 vezes, 2000 semanas.", "R$ 1,00 e R$ 0,50 e R$ 1.000.000,00",
    "Número enorme: 1234567890123456789012 e 999999999999 e 1000000000000.", "“Aspas” ‘simples’ — travessão – meio… [colchetes] «francesas»",
    "guarda-chuva, bem-vindo, pé-de-moleque, -x- --", "Éxito, exame, sexo, inexistente, hexágono, reflexo, texto, exceção.",
    "advogado, pneu, psicologia, ritmo, afta, ação, cãibra, órgão, órfã, mãe, põe, pão, vão, cantam", "ÁRVORE ÔNIBUS Ação ÓTIMO",
    "Ã mãe (NFD) e café", "Emoji 😀 e símbolos ©®™ @ # $ & * + = < > ~ ^ _ |", "   espaços   múltiplos\tcom\ttab\n e quebra",
    "", "   ", "...", "?!", "a", "q", "ñ", "tel. 1234", "vc pq hj tb td blz obg msg etc. av. Prof. Profa. Srta.",
    "10:30 e 25h e 24h60 e 0h e 12:00 e 7h05", "31/12 e 32/01 e 15/13 e 00/00", "11º 21º 55ª 100º 101º 0º", "0,5% 0,05% 12,3456%",
    "R$12 R$ 1.5 e R$1,5", "1,5 e 0,05 e 3,14159 e 1.000,25", "quê? quem? porquê! por quê.", "wifi, whatsapp, pix, mouse, show, web, site",
    "hoje é dia 1 e amanhã dia 2", "um dois três quatro cinco seis sete oito nove dez",
]
words = sorted(lexicon())
gold = {"sentences": [], "edge": [], "words_rules": [], "words_lex": [], "numbers": [], "normalize": []}
for t in sentences:
    gold["sentences"].append([t, str(phonemize(t)), json.dumps(pieces(t), ensure_ascii=False)])
for t in edge:
    gold["edge"].append([t, str(phonemize(t)), json.dumps(pieces(t), ensure_ascii=False), normalize(t)])
for w in words:
    gold["words_rules"].append([w, " ".join(("ˈ" if s else "") + p for p, s in pronounce(w, use_lexicon=False))])
    gold["words_lex"].append([w, " ".join(("ˈ" if s else "") + p for p, s in pronounce(w))])
rng = random.Random(7)
ints = list(range(0, 3001)) + [rng.randrange(0, 10**12) for _ in range(3000)] + [10**12 - 1, 10**12, 10**15 + 7, 2**70, 123456789012345678901234567890]
for n in ints:
    gold["numbers"].append([str(n), number_to_words(n), number_to_words(n, fem=True)])
out = Path(sys.argv[1]) if len(sys.argv) > 1 else root.parent / "dizione-ptbr-js" / "test" / "golden.json"
out.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
print({k: len(v) for k, v in gold.items()}, out.stat().st_size // 1024, "KB")
