"""The third version's check (upsample/, built with cargo build --release there): every 48 kHz sample against
up_ref.upsample, and the 8 kHz samples underneath (talk --8k, the output stage's cards as the upsampler reads them)
against voice_ref, on the four frame files in fixtures/ (talk-frames) and on make_wavs.py's three texts (talk, the
references end to end: text_ref, front_ref, voice_ref, up_ref).

    python3 check_up.py            # all of them
    python3 check_up.py --frames   # the fixtures only"""
import os
import struct
import subprocess
import sys
import front_ref as fr
import table as tb
import text_ref as tr
import up_ref as ur
import voice_ref as vr

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, '..', 'upsample', 'target', 'release')
WORK = os.path.join(HERE, '..', 'work')
FIXTURES = ['hello_tts', 'mtv_tts', 'fox_tts', 'born1968_tts']
TEXTS = [('born1968', "Hello, my name is cardiac and I was born in 1968 to D W Hagelbarger. And now I can talk."),
         ('mtv', "I want my MTV"),
         ('fox', "the quick brown fox jumps over the lazy dog")]


def s16(data):
    return list(struct.unpack('<%dh' % (len(data) // 2), data))


def verdict(name, values8, got8, got48, stats):
    want8 = ur.samples(values8)
    want48 = ur.samples(ur.upsample(values8))
    same8, same48 = got8 == want8, got48 == want48
    print('%-14s %6d samples at 8 kHz %s, %7d at 48 kHz %s  %s' % (
        name, len(want8), 'exact' if same8 else 'DIFFERENT', len(want48), 'exact' if same48 else 'DIFFERENT', stats))
    return same8 and same48


ok = True
os.makedirs(WORK, exist_ok=True)
for name in FIXTURES:
    frames = vr.sc.read_frames(os.path.join(HERE, 'fixtures', '%s.frames' % name))
    deck = vr.frame_cards(frames)
    path = os.path.join(WORK, name + '.frames.cards')
    open(path, 'w').write('\n'.join(map(str, deck)) + '\n')
    values8, _ = vr.voice(deck)
    run = lambda *a: subprocess.run([os.path.join(BIN, 'talk-frames'), *a, path], capture_output=True)
    r48, r8 = run('-v'), run('--8k')
    ok &= verdict(name, values8, s16(r8.stdout), s16(r48.stdout), r48.stderr.decode().strip().split('\n')[-2])
if '--frames' not in sys.argv:
    fr.load(tb.C)
    for name, text in TEXTS:
        values8, _ = vr.voice(fr.phonemes_to_cards(tr.compose(text)))
        run = lambda *a: subprocess.run([os.path.join(BIN, 'talk'), *a], input=text.encode(), capture_output=True)
        r48, r8 = run('-v'), run('--8k')
        ok &= verdict(name, values8, s16(r8.stdout), s16(r48.stdout), r48.stderr.decode().strip().split('\n')[-2])
sys.exit(0 if ok else 1)
