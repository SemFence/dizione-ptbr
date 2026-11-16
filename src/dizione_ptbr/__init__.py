"""dizione-ptbr: Brazilian Portuguese (pt-BR) text to phonemes. Dictionary + rules, Apache-2.0 code, no GPL.
Not for European Portuguese."""
from .engine import Phonemes, phonemize, pronounce
from .g2p import phonemize_word
from .normalize import normalize, number_to_words
from .symbols import ID, SYMBOLS

__all__ = ["phonemize", "pronounce", "phonemize_word", "normalize", "number_to_words", "Phonemes", "SYMBOLS", "ID"]
__version__ = "0.0.1"
