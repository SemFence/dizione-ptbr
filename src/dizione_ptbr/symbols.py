"""Symbol table of the front end. APPEND-ONLY: changing the order or removing a symbol invalidates every
model trained with it (the model embeds ids, not strings)."""

PAD, BOS, EOS, SP, UNK = "<pad>", "<bos>", "<eos>", "<sp>", "<unk>"
SPECIALS = (PAD, BOS, EOS, SP, UNK)
PUNCTUATION = (",", ".", "?", "!", ";", ":", '"', "'", "(", ")", "—", "…")
PHONES = (
    # consonants
    "p", "b", "t", "d", "k", "ɡ", "f", "v", "s", "z", "ʃ", "ʒ", "x", "m", "n", "ɲ", "l", "ʎ", "ɾ", "tʃ", "dʒ",
    # glides
    "j", "w", "j̃", "w̃",
    # oral vowels
    "a", "ɐ", "e", "ɛ", "i", "o", "ɔ", "u",
    # nasal vowels
    "ɐ̃", "ẽ", "ĩ", "õ", "ũ",
)
SYMBOLS = SPECIALS + PUNCTUATION + PHONES
ID = {s: i for i, s in enumerate(SYMBOLS)}
assert len(ID) == len(SYMBOLS), "duplicated symbol"
VOWEL_PHONES = set("a ɐ e ɛ i o ɔ u ɐ̃ ẽ ĩ õ ũ".split())
