"""Steps 3 under heartburn: talk-phonemes on each sentence's phonemes against the integer reference
(front_ref.phonemes_to_cards, which front_machines.compose matches), card for card; then the frames through
talk-frames against the voice box's model, value for value."""
import os
import subprocess
import sys
import front_ref as fr
import table as tb
import voice_ref as vr
import sentences
import test_front as T

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, '..', 'target', 'release')
WORK = os.path.join(HERE, '..', 'work')
os.makedirs(WORK, exist_ok=True)
fr.load(tb.C)
ok = True
for t in sentences.MAIN + sentences.MORE:
    toks = T.tokens(t)
    want = fr.phonemes_to_cards(toks)
    r = subprocess.run([os.path.join(BIN, 'talk-phonemes'), '-v'], input='\n'.join(map(str, toks)), capture_output=True, text=True)
    got = [int(v) for v in r.stdout.split()]
    same = got == want
    path = os.path.join(WORK, 'front.cards')
    open(path, 'w').write(r.stdout)
    wv, peak = vr.voice(want)
    r2 = subprocess.run([os.path.join(BIN, 'talk-frames'), '--values', path], capture_output=True, text=True)
    gv = [int(v) for v in r2.stdout.split()]
    same2 = gv == wv
    ok &= same and same2
    print('%-36s frames %s (%s), samples %s, peak |yd| %d' % (t[:36], 'exact' if same else 'DIFFERENT', r.stderr.strip().split('\n')[-1],
          'exact' if same2 else 'DIFFERENT', peak))
sys.exit(0 if ok else 1)
