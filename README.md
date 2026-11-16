# dizione-ptbr

**Brazilian Portuguese (pt-BR) text to phonemes**, built as the front end of small open text-to-speech models
(the [tiny-voca](https://github.com/n4ze3m/tiny-voca) recipe, in Brazilian Portuguese).

> **pt-BR only.** The pronunciations, the rules and the lexicon describe the Portuguese spoken in Brazil
> (palatalized "t" and "d" before "i", final "l" as `w`, nasal vowels as in Brazil). **It is not for European
> Portuguese (pt-PT)**, which has different vowel reduction and different "s" and "r", and would need its own
> lexicon and rules.

Dictionary plus rules, pure Python with no dependencies, **no GPL** (it does not use eSpeak NG).

Created by **SemFence** · researcher: **Gustavo Toledo**.

```python
from dizione_ptbr import phonemize

r = phonemize("Oi, tudo bem? Paguei R$ 15,50 às 10h30.")
print(r)         # <bos> ˈo j , <sp> t ˈu d u <sp> b ˈẽ j̃ ? <sp> ...
r.ids            # ids into dizione_ptbr.SYMBOLS (55 symbols)
r.stress         # 0 none, 1 primary
```

```bash
python -m dizione_ptbr "Dr. Silva chegou às 21 horas."
```

## What it does

1. **Normalizes the text**: numbers (up to 999,999,999,999, with gender: "vinte e uma horas"), money, percent,
   times, dates, ordinals, abbreviations ("Dr.", "vc").
2. **Looks each word up** in a 32,990-word lexicon (the MFA Brazilian Portuguese dictionary, CC BY 4.0).
3. **Falls back to rules** for words that are not in it: stress from the spelling, open/close "e" and "o"
   (a small table learned from the dictionary), nasal vowels, "t"/"d" before "i", final "l" as "w",
   epenthetic "i" (ad-vo-gado), and more.
4. **Spells acronyms** with no vowel ("RH", "CPF").
5. Returns symbols with `<bos>`, `<eos>`, `<sp>` between words and punctuation as its own symbols.

## How well it works

Measured against the MFA dictionary, word by word. The words are split by hash into train (60%, only used to
estimate the open/close table), dev (20%, where the rules were tuned) and test (20%, looked at once at the end).
"Same as a variant" counts a word as right if it equals any pronunciation variant of the dictionary.
"Phone error" is the edit distance to the closest variant.

| Rules only, no lexicon | Words | Same as a variant | Phone error |
|---|---:|---:|---:|
| dev, all words | 6,610 | 64.8% | 7.2% |
| **test, all words** | 6,557 | **65.4%** | **6.9%** |
| dev, regular Portuguese words | 6,183 | 68.1% | 5.7% |
| **test, regular Portuguese words** | 6,164 | **68.3%** | **5.7%** |

"Regular" leaves out foreign names, acronyms and spellings with k, w, y, th, double consonants and the like,
which are most of what the rules cannot get right and not what is usually missing from the lexicon.

- **Lexicon coverage** on the 10,675 sentences of the [SemFence PT-BR sentence bank](https://huggingface.co/datasets/semfence/ptbr-sentences):
  **96.4% of the words** come from the lexicon (79% of the distinct words). The rest go through the rules.
- **Open or close "e"/"o"** in stressed syllables with no accent mark (festa/mesa, porta/rosa): the learned table
  gets **84.9%** right, against 74.4% for always choosing the close vowel. It is the hardest decision, and the spelling alone does not say.
- **Speed**: about 16,000 sentences per second on a laptop, in plain Python. All 10,675 sentences convert with no unknown symbol.

These numbers use the dictionary as the reference, and the dictionary has its own inconsistencies (the same
unstressed "a" is sometimes `a` and sometimes `ɐ`, and some entries look like errors). Read them as a
lower bound of how well it matches careful pronunciation, not as human-rated quality.

## Phone set

The symbols of the MFA dictionary: `a b d dʒ e ẽ f i ĩ j j̃ k l m n o õ p s t tʃ u ũ v w w̃ x z ɐ ɐ̃ ɔ ɛ ɡ ɲ ɾ ʃ ʎ ʒ`.
Two of them (`j̃`, `w̃`) are not labels of the `wav2vec2-lv-60-espeak-cv-ft` aligner that tiny-voca uses to time
phonemes, so the alignment step will need a small mapping for them (not written yet). The symbol table is
**append-only** (`symbols.py`): changing the order breaks every model trained with it.

## Known limits

- Homographs ("almoço" noun/verb, "sede") are not told apart.
- Foreign words and names are read with Portuguese rules ("pix" comes out as `p i ʃ`).
- Dialect: standard Brazilian Portuguese with palatalized "t"/"d" before "i", final "l" as `w` and "r" as `x`
  at the end of a syllable. Carioca "s" (`ʃ`) and r-dropping are not modeled.
- Text normalization covers common cases only. Telephone numbers, URLs, roman numerals and units are not handled.
- Python only for now. A JavaScript port (for in-browser demos) is planned and must give identical output.

## Rebuilding the data

```bash
./scripts/fetch_sources.sh          # downloads the MFA dictionary into data/sources (not in git)
python scripts/eval_rules.py --build-table --splits train,dev,test
python scripts/eval_rules.py --regular --splits dev,test
python scripts/build_lexicon.py
python -m unittest discover -s tests
```

## License and credit

- **Code**: Apache-2.0.
- **Lexicon** (`src/dizione_ptbr/data/lexicon.tsv`): CC BY 4.0, derived from the MFA Brazilian Portuguese dictionary by
  Michael McAuliffe and Morgan Sonderegger. See `src/dizione_ptbr/data/LICENSE.mfa-dictionary.md`.

If you use this package, please credit **SemFence (Gustavo Toledo)** and the MFA dictionary.

The design follows [dizione](https://github.com/n4ze3m/dizione) by Muhammed Nazeem (lexicon, rules, small model for unknown words,
same output shape), for Portuguese.
