import sys
from . import normalize, phonemize

text = " ".join(sys.argv[1:]) or sys.stdin.read()
print("texto normalizado:", normalize(text))
r = phonemize(text)
print("fonemas:", r)
print("ids:", r.ids)
