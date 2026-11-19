"""Step 4 under heartburn: talk --phonemes on each test text against text_to_phonemes.py's tokens, card for card."""
import os
import bins
import subprocess
import sys
import front_ref as fr
import text_ref as tr
import test_text as T

BIN = os.path.join(bins.RELEASE, 'talk')
bad = 0
for t in T.texts:
    want = fr.tokens_of(' '.join(tr.tp.text_to_phonemes(t)))
    r = subprocess.run([BIN, '--phonemes'], input=t, capture_output=True, text=True)
    got = [int(v) for v in r.stdout.split()]
    if got != want:
        bad += 1
        print('DIFFERENT', repr(t), got, want, r.stderr[-300:])
print(len(T.texts), 'texts,', bad, 'differ')
sys.exit(1 if bad else 0)
