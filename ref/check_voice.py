"""Step 2 under heartburn: talk-frames on the frame cards of each .frames file named, against voice_ref.voice,
value for value."""
import os
import bins
import subprocess
import sys
import voice_ref as vr

BIN = os.path.join(bins.RELEASE, 'talk-frames')
WORK = os.path.join(os.path.dirname(__file__), '..', 'work')
os.makedirs(WORK, exist_ok=True)
ok = True
for name in sys.argv[1:]:
    frames = vr.sc.read_frames(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', '%s.frames' % name))
    deck = vr.frame_cards(frames)
    path = os.path.join(WORK, name + '.frames.cards')
    open(path, 'w').write('\n'.join(map(str, deck)) + '\n')
    want, peak = vr.voice(deck)
    r = subprocess.run([BIN, '--values', '-v', path] + bins.EXTRA, capture_output=True, text=True)
    got = [int(v) for v in r.stdout.split()]
    same = got == want
    ok &= same
    print('%-14s %6d samples  %s  %s' % (name, len(want) // 2, 'exact' if same else 'DIFFERENT', r.stderr.strip().split('\n')[-1]))
sys.exit(0 if ok else 1)
