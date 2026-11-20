"""The third version's check (upsample/, built with cargo build --release there): every 48 kHz sample against
up_ref, and the 8 kHz samples underneath (talk --8k, the output stage's cards as the upsampler reads them) against
voice_ref, on the four frame files in fixtures/ (talk-frames, which has no high band without choose's filters) and
on make_wavs.py's three texts (talk, the references end to end: text_ref, front_ref, voice_ref, up_ref). For the
texts the 48 kHz samples are checked twice, with the high band (up_ref.hiband and hmix on the upsampler's samples,
each frame's level from front_ref's noise filter for it) and without (talk --no-hiband, up_ref.upsample alone).

    python3 check_up.py            # all of them
    python3 check_up.py --frames   # the fixtures only
    python3 check_up.py --long     # and the four passages of the previews (slow: a few minutes)"""
import os
import struct
import subprocess
import sys
import front_ref as fr
import hb_table
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
LONG = [('manual', hb_table.TEXTS[0]), ('imagination', hb_table.TEXTS[1]), ('keep_talking', hb_table.TEXTS[2]),
        ('all_your_base', hb_table.TEXTS[3])]


def s16(data):
    return list(struct.unpack('<%dh' % (len(data) // 2), data))


def verdict(name, values8, got8, got48, stats, cards=None, noise=None, got48n=None):
    want8 = ur.samples(values8)
    up = ur.upsample(values8)
    want48 = ur.samples(up if cards is None else ur.hmix(up, ur.hiband(cards, noise)))
    same8, same48 = got8 == want8, got48 == want48
    plain = '' if got48n is None else (', without the high band %s' % ('exact' if got48n == ur.samples(up) else 'DIFFERENT'))
    print('%-14s %6d samples at 8 kHz %s, %7d at 48 kHz %s%s  %s' % (
        name, len(want8), 'exact' if same8 else 'DIFFERENT', len(want48), 'exact' if same48 else 'DIFFERENT', plain,
        stats))
    return same8 and same48 and (got48n is None or got48n == ur.samples(up))


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
    texts = TEXTS
    if '--long' in sys.argv:
        texts = TEXTS + LONG
    for name, text in texts:
        info = {}
        cards = fr.phonemes_to_cards(tr.compose(text), info)
        values8, _ = vr.voice(cards)
        run = lambda *a: subprocess.run([os.path.join(BIN, 'talk'), *a], input=text.encode(), capture_output=True)
        r48, r48n, r8 = run('-v'), run('--no-hiband'), run('--8k')
        ok &= verdict(name, values8, s16(r8.stdout), s16(r48.stdout), r48.stderr.decode().strip().split('\n')[-2],
                      cards, info['noise'], s16(r48n.stdout))
sys.exit(0 if ok else 1)
