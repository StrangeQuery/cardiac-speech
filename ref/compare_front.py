"""The integer front end (front_ref, as the CARDIACs run it) against the float front end
(tools/lpc/phonemes_to_frames.py) on the same phonemes: durations, pitch, formants and level, segment by segment."""
import cmath
import math
import sys
import front_ref as fr
import voice_ref as vr
sys.path.insert(0, vr.LPC)
import phonemes_to_frames as pf   # noqa: E402
import text_to_phonemes as tp     # noqa: E402
import sentences                  # noqa: E402


def step_up(ks):
    a = [1.0]
    for i, k in enumerate(ks, 1):
        a = [1.0] + [a[j] + k * a[i - j] for j in range(1, i)] + [k]
    return a


def roots(a):
    """Durand-Kerner on z^p + a1 z^(p-1) + ... + ap."""
    p = len(a) - 1
    z = [(0.4 + 0.9j) ** i for i in range(p)]
    for _ in range(500):
        nz = []
        for i in range(p):
            num = sum(a[k] * z[i] ** (p - k) for k in range(p + 1))
            den = 1
            for j in range(p):
                if j != i:
                    den *= z[i] - z[j]
            nz.append(z[i] - num / den)
        if max(abs(x - y) for x, y in zip(z, nz)) < 1e-12:
            z = nz
            break
        z = nz
    return z


def formants(ks):
    """F1..F3 (Hz) of the all-pole filter with reflection coefficients ks: the pole angles, upper half plane,
    bandwidth under 600 Hz, lowest first."""
    fs = []
    for z in roots(step_up(ks)):
        if z.imag <= 0:
            continue
        F = cmath.phase(z) * 8000 / (2 * math.pi)
        B = -math.log(abs(z)) * 8000 / math.pi
        if B < 600 and F > 90:
            fs.append(F)
    fs.sort()
    return (fs + [0, 0, 0])[:3]


def run(text):
    phon = ' '.join(tp.text_to_phonemes(text))
    info_f = {}
    ffr = pf.phon_to_frames(phon, 1.0, info_f)
    segs = [s for s in info_f['segs']]
    info_i = {}
    cards = fr.phonemes_to_cards(fr.tokens_of(phon), info_i)
    r3 = info_i['r3']
    assert len(r3) == len(segs), (len(r3), len(segs))
    dd, f0d, fd, nseg, nv = 0, 0, [0, 0, 0], 0, 0
    fi = ff = 0
    rows = []
    for s, r in zip(segs, r3):
        nf_, ni = s.frames, r[3]
        dd += abs(nf_ - ni)
        nseg += 1
        if s.kind == 'vowel' and nf_ and ni:
            # mean f0 and formants over the middle frames of the vowel
            a = [info_f['f0'][ff + k] for k in range(nf_)]
            b = [info_i['pitch'][fi + k] for k in range(ni)]
            f0d += abs(sum(a) / len(a) - sum(b) / len(b))
            mf = formants(ffr[ff + nf_ // 2]['k'])
            ki = info_i['frames'][fi + ni // 2][4:]
            mi = formants([k / 1000 for k in reversed(ki)])
            for q in range(3):
                fd[q] += abs(mf[q] - mi[q])
            nv += 1
            rows.append((s.ph, s.stress, nf_, ni, sum(a) / len(a), sum(b) / len(b), mf, mi))
        ff += nf_
        fi += ni
    return dict(text=text, segs=nseg, dur=dd / nseg, total=(ff, fi), f0=f0d / max(1, nv), F=[x / max(1, nv) for x in fd],
                rows=rows)


if __name__ == '__main__':
    fr.load(float(sys.argv[1]) if len(sys.argv) > 1 else 40.0)
    texts = sentences.MAIN + (sentences.MORE if '--more' in sys.argv else [])
    for t in texts:
        r = run(t)
        print('%-44s frames %4d float %4d int | mean |frames diff| a segment %.2f | vowel f0 %.1f Hz | F1 %3.0f F2 %3.0f F3 %3.0f Hz'
              % (t[:44], r['total'][0], r['total'][1], r['dur'], r['f0'], *r['F']))
        if '-v' in sys.argv:
            for row in r['rows']:
                print('   %-3s%d frames %2d %2d  f0 %5.1f %5.1f  F %s  %s' % (row[0], row[1], row[2], row[3], row[4], row[5],
                      ' '.join('%4.0f' % x for x in row[6]), ' '.join('%4.0f' % x for x in row[7])))
