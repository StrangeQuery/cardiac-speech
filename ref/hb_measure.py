"""How much the 48 kHz version's high band adds, sound by sound: for the frames of each noise filter (each fricative,
affricate and burst), the energy of the 48 kHz speech from 4 to 8 kHz and from 4 to 24 kHz against its energy below
4 kHz, the speech band, with Klatt's figure for the same ratio beside it (hb_table.klatt_ratio), and the high band's
own energy below 4 kHz against the speech band (what it adds there). Each frame is 1,200 samples at 48 kHz, taken
245 samples late (the 48 kHz speech's delay), under a Hann window, its spectrum the FFT of 2,048 points. It runs
upsample/target/release/talk with and without the high band (--no-hiband) on the texts given, or hb_table's.
It needs numpy (work/venv).

    work/venv/bin/python ref/hb_measure.py [TEXT ...]"""
import math
import os
import subprocess
import sys
import numpy as np
import front_ref as fr
import hb_table as ht
import table as tb
import text_ref as tr
import up_ref as ur

TALK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'upsample', 'target', 'release', 'talk')
N = 2048
FREQ = np.arange(N // 2 + 1) * 48000 / N
WIN = np.hanning(1200)


def talk(text, *flags):
    r = subprocess.run([TALK, *flags], input=text.encode(), capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype='<i2').astype(float)


def power(x):
    return np.abs(np.fft.rfft(x * WIN, N)) ** 2


def band(p, lo, hi):
    return p[(FREQ >= lo) & (FREQ < hi)].sum()


def measure(texts):
    names = ht.noise_filters()
    acc = {}
    whole = np.zeros(3)
    for text in texts:
        info = {}
        fr.phonemes_to_cards(tr.compose(text), info)
        up, plain = talk(text), talk(text, '--no-hiband')
        for f, nz in enumerate(info['noise']):
            if not nz:
                continue
            at = 1200 * f + ur.HB_DELAY
            pw, ps, ph = power(up[at:at + 1200]), power(plain[at:at + 1200]), power(up[at:at + 1200] - plain[at:at + 1200])
            a = acc.setdefault(names[nz], np.zeros(5))
            a += [band(ps, 0, 4000), band(pw, 4000, 8000), band(pw, 4000, 24000), band(ph, 0, 4000), 1]
        whole += [np.sum(plain ** 2), np.sum((up - plain) ** 2), np.sum(up ** 2)]
    return acc, whole


def db(x):
    return 10 * math.log10(x) if x > 0 else float('-inf')


if __name__ == '__main__':
    fr.load(tb.C)
    texts = sys.argv[1:] or ht.TEXTS
    acc, whole = measure(texts)
    print('%-10s %6s %10s %10s %10s %14s' % ('sound', 'frames', '4-8k dB', 'Klatt dB', '4-24k dB', 'hb <4k dB'))
    for (p, alt), a in sorted(acc.items(), key=lambda kv: (kv[0][0] in ht.COGNATE, kv[0])):
        k = ('%10.1f' % db(ht.klatt_ratio(p, alt))) if p not in ht.COGNATE else '%10s' % ('(%s-10)' % ht.COGNATE[p])
        print('%-10s %6d %10.1f %s %10.1f %14.1f' % (p + (' back' if alt else ''), a[4], db(a[1] / a[0]), k,
                                                   db(a[2] / a[0]), db(a[3] / a[0])))
    print('over the whole of the texts: the high band\'s power is %.1f dB against the speech\'s' % db(whole[1] / whole[0]))
