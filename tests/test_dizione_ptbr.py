import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dizione_ptbr import ID, SYMBOLS, VERSION, identity, normalize, number_to_words, phonemize, phonemize_word, pieces, pronounce


def plain(word):
    return " ".join(p for p, _ in phonemize_word(word))


def stressed(word):
    return [p for p, s in phonemize_word(word) if s]


class RuleTests(unittest.TestCase):
    def test_basic_words(self):
        self.assertEqual(plain("casa"), "k a z ɐ")
        self.assertEqual(plain("quando"), "k w ɐ̃ d u")
        self.assertEqual(plain("pão"), "p ɐ̃ w̃")
        self.assertEqual(plain("mãe"), "m ɐ̃ j̃")
        self.assertEqual(plain("chuva"), "ʃ u v ɐ")

    def test_palatalization_and_reduction(self):
        self.assertEqual(plain("tarde"), "t a x dʒ i")
        self.assertEqual(plain("cidade"), "s i d a dʒ i")
        self.assertEqual(plain("leite")[-4:], "tʃ i")

    def test_epenthesis(self):
        self.assertEqual(plain("advogado"), "a dʒ i v o ɡ a d u")

    def test_stress_by_orthography(self):
        self.assertEqual(stressed("história"), ["ɔ"])
        self.assertEqual(stressed("falar"), ["a"])
        self.assertEqual(stressed("comia"), ["i"])        # unaccented -ia: stress on the i
        self.assertEqual(stressed("café"), ["ɛ"])

    def test_digraphs(self):
        self.assertEqual(plain("velho"), "v e ʎ u")
        self.assertTrue(plain("queijo").startswith("k e "))

    def test_ex_prefix(self):
        self.assertTrue(plain("exemplo").startswith("e z "))
        self.assertTrue(plain("expressivo").startswith("i s "))


class NumberTests(unittest.TestCase):
    def test_cardinals(self):
        cases = {0: "zero", 21: "vinte e um", 100: "cem", 101: "cento e um", 1000: "mil", 1001: "mil e um",
                 1100: "mil e cem", 1234: "mil duzentos e trinta e quatro", 2001: "dois mil e um",
                 1000000: "um milhão", 1000001: "um milhão e um", 2500000: "dois milhões e quinhentos mil"}
        for n, words in cases.items():
            self.assertEqual(number_to_words(n), words, n)

    def test_feminine(self):
        self.assertEqual(number_to_words(2, fem=True), "duas")
        self.assertEqual(number_to_words(200, fem=True), "duzentas")
        self.assertEqual(normalize("21 horas"), "vinte e uma horas")

    def test_money_percent_time_date(self):
        self.assertEqual(normalize("R$ 15,50"), "quinze reais e cinquenta centavos")
        self.assertEqual(normalize("R$ 1"), "um real")
        self.assertEqual(normalize("15%"), "quinze por cento")
        self.assertEqual(normalize("às 10h30"), "às dez horas e trinta minutos")
        self.assertEqual(normalize("14/03/2026"), "quatorze de março de dois mil e vinte e seis")
        self.assertEqual(normalize("1º e 2ª"), "primeiro e segunda")

    def test_abbreviations(self):
        self.assertEqual(normalize("Dr. Silva, vc viu?"), "Doutor Silva, você viu?")

    def test_no_double_period(self):
        self.assertEqual(normalize("Custa R$ 1 hoje."), "Custa um real hoje.")


class EngineTests(unittest.TestCase):
    def test_structure(self):
        r = phonemize("Oi, tudo bem?")
        self.assertEqual(r.symbols[0], "<bos>"); self.assertEqual(r.symbols[-1], "<eos>")
        self.assertIn(",", r.symbols); self.assertIn("?", r.symbols)
        self.assertEqual(r.symbols.count("<sp>"), 2)             # 3 words
        self.assertEqual(len(r.ids), len(r.stress))
        self.assertTrue(all(0 <= i < len(SYMBOLS) for i in r.ids))
        self.assertNotIn(ID["<unk>"], r.ids)

    def test_lexicon_and_rules_agree_on_shape(self):
        self.assertTrue(pronounce("casa"))
        self.assertTrue(pronounce("barbeiro"))                      # not in the lexicon: rules
        self.assertIn("ˈ", str(phonemize("barbeiro")))

    def test_function_words_unstressed(self):
        r = phonemize("de que")
        self.assertEqual(sum(r.stress), 0)

    def test_acronyms_without_vowels_are_spelled(self):
        r = phonemize("O RH e o CPF.")
        self.assertNotIn(ID["<unk>"], r.ids)
        self.assertGreater(len(r), 12)

    def test_numbers_are_read(self):
        r = phonemize("Tenho 3 gatos.")
        self.assertNotIn(ID["<unk>"], r.ids)
        self.assertIn("t", r.symbols)                               # "três"

    def test_symbols_are_append_only_snapshot(self):
        self.assertEqual(SYMBOLS[:5], ("<pad>", "<bos>", "<eos>", "<sp>", "<unk>"))
        self.assertEqual(SYMBOLS[5:8], (",", ".", "?"))
        self.assertEqual(len(SYMBOLS), 55)


class FrontEndInterfaceTests(unittest.TestCase):
    def test_pieces_are_punctuation_or_words_with_stress(self):
        result = pieces("Oi, tudo bem?")
        self.assertEqual([is_punctuation for is_punctuation, _ in result], [False, True, False, True])
        self.assertEqual(result[1], (True, ","))
        self.assertEqual(result[0][1], [[("o", 1), ("j", 0)]])
        self.assertEqual([len(word) for word in result[2][1]], [4, 3])      # "tudo" and "bem"
        self.assertEqual(pieces("😀"), [])                                         # nothing to say, nothing returned

    def test_identity_names_the_build(self):
        first, second = identity(), identity()
        self.assertEqual(first, second)
        self.assertEqual((first["name"], first["version"]), ("dizione-ptbr", VERSION))
        self.assertEqual(len(first["fingerprint"]), 64)


if __name__ == "__main__":
    unittest.main()
