"""The CARDIAC speech against the Python pipeline's (tts.sh: the float front end, then the closed-loop
CARDIAC-arithmetic synthesizer with chirp excitation), made afresh in memory with today's text_to_phonemes.py.
The two have different frame counts, so they are set side by side segment by segment: each segment's frames
mapped in proportion onto the other's. Reported: the log-spectral distance over the aligned 25 ms frames, and the
mean difference of the segments' levels (dB, after matching the overall level)."""
import math
import os
import struct
import subprocess
import sys
import front_ref as fr
import table as tb
import text_ref as tr
import voice_ref as vr
sys.path.insert(0, vr.LPC)
import common              # noqa: E402
import closedloop as cl    # noqa: E402
import synth_float as sf   # noqa: E402
import phonemes_to_frames as pf   # noqa: E402

BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'target', 'release', 'talk')
fr.load(tb.C)


def spec(x):
    a = [complex(v * (0.54 - 0.46 * math.cos(2 * math.pi * i / 255)), 0) for i, v in enumerate((x + [0] * 256)[:256])]
    common.fft(a)
    return [10 * math.log10(abs(a[k]) ** 2 + 1e-10) for k in range(1, 128)]


def frames_of(x, n):
    return [x[i * 200:(i + 1) * 200] for i in range(n)]


def level(fs):
    e = sum(v * v for f in fs for v in f) / max(1, sum(len(f) for f in fs))
    return 10 * math.log10(e + 1e-12)


def compare(text):
    phon = ' '.join(tr.tp.text_to_phonemes(text))
    info = {}
    frames = pf.phon_to_frames(phon, 1.0, info)
    sf.SHAPE = 'chirp'
    py, _, _, _ = cl.closed_loop(frames, 2)
    segs_f = [s.frames for s in info['segs']]
    toks = tr.compose(text)
    inf2 = {}
    fr.phonemes_to_cards(toks, inf2)
    segs_i = [r[3] for r in inf2['r3']]
    r = subprocess.run([BIN], input=text.encode(), capture_output=True)
    ours = [v / 32768 for v in struct.unpack('<%dh' % (len(r.stdout) // 2), r.stdout)]
    F = frames_of(py, sum(segs_f))
    I = frames_of(ours, sum(segs_i))
    pairs, lev = [], []
    a = b = 0
    for nf, ni in zip(segs_f, segs_i):
        fa, ib = F[a:a + nf], I[b:b + ni]
        if nf and ni:
            for k in range(nf):
                pairs.append((fa[k], ib[min(ni - 1, k * ni // nf)]))
            lev.append((level(fa), level(ib)))
        a += nf
        b += ni
    g = level([p[0] for p in pairs]) - level([p[1] for p in pairs])
    top = max(level([p[0]]) for p in pairs)
    d, n = 0, 0
    for p, q in pairs:
        if level([p]) < top - 40:
            continue
        A, B = spec(p), spec([v * 10 ** (g / 20) for v in q])
        d += math.sqrt(sum((x - y) ** 2 for x, y in zip(A, B)) / len(A))
        n += 1
    sl = [abs(x - y - g) for x, y in lev if x > top - 40]
    return d / n, sum(sl) / len(sl), len(py) / 8000, len(ours) / 8000


if __name__ == '__main__':
    for t in sys.argv[1:]:
        lsd, dl, a, b = compare(t)
        print('%-44s Python %.2f s, CARDIAC %.2f s; aligned log-spectral distance %.1f dB; segment levels differ by %.1f dB on average'
              % (t[:44], a, b, lsd, dl))
