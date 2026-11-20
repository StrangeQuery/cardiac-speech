"""The 48 kHz version's high-band levels, upsample/tables/hiband.cards: one card for each filter of the phoneme
table (front/filters.cards, record for record), the level hnoise gives a frame that speaks through that filter.
It is 0 but for the noise filters, the fricatives' and affricates' and the bursts of the stops. Like the other
tables it is worked out once, ahead of time, in floating point, and none of it depends on the text.

A sound's level is set so that the high band carries the share of the sound's energy above 4 kHz that Klatt's
synthesizer gives it (Klatt 1980, Table III): the frication source through his parallel formants F2 to F6 at their
amplitudes A2 to A6, and the bypass AB, as the prototype reads them (phonemes_to_frames.parallel_power: resonances
at their peak levels, summed in power with the flat bypass). For each voiceless sound, and each stop's burst,
R = E(4-8 kHz) / E(0-4 kHz) of that spectrum.

A voiced fricative (V, DH, Z, ZH, and JH) has the same parallel amplitudes in Table III as its voiceless cognate
(F, TH, S, SH, CH), and Klatt drives its frication 10 dB lower, AF 50 dB against 60 dB. Below 4 kHz the 8 kHz speech
speaks it with voicing, so its speech band is mostly voicing and can't set its frication. So a voiced fricative's
level is its cognate's, 10 dB down: L x 10^(-10/20).

E(0-4 kHz) is measured: the mean square of the 48 kHz speech (the first version's 8 kHz samples, upsampled by the
CARDIAC arithmetic of up_ref) over the frames of each noise filter in the texts below, each frame of 1,200 samples
(taken 245 samples late, the 48 kHz speech's delay) under a Hann window. The high band's own power is
measured too, from up_ref's hnoise and hfilt at a steady level: G2, its mean square for a level of 1 in units of
y, and PHI, the share of it from 4 to 8 kHz. Then the level is

    L = sqrt(R E(0-4 kHz) / (16 G2 PHI))      (a sample of the high band is 4 y)

rounded to a whole number. That holds for a steady level, but hnoise ramps the level across a frame towards the
next frame's (as interp ramps A), so a burst followed by its aspiration, or a fricative by a vowel of the same
voicing, gets less than that. So the level is then corrected by measurement, twice: the high band is made from the
texts at the levels so far, by up_ref's hnoise and hfilt, its mean square over each sound's frames is measured in the
same way (PHI of it taken as the part from 4 to 8 kHz), and the level is multiplied by the square root of what was
wanted over what was measured.

    python3 hb_table.py           # writes upsample/tables/hiband.cards and prints the levels"""
import math
import os
import sys
import front_ref as fr
import table as tb
import text_ref as tr
import up_measure as um
import up_ref as ur
import voice_ref as vr

pf = tb.pf
HERE = os.path.dirname(os.path.abspath(__file__))
# the texts the speech band is measured over: the four passages of the previews, and sentences for the sounds
# they have few of
TEXTS = [
    'Cardiac is an acronym for CARDboard Illustrative Aid to Computation. The key word here is "illustrative." It '
    'means that Cardiac illustrates the operation of a computer without actually being a computer. In fact, it is '
    'not even a practical aid to computing. On the other hand, it is a very practical aid to understanding '
    'computers and computer programming. You\'ll need this kind of understanding to keep up with the Computer Age '
    'you are about to enter. These are fast-moving times, and those who make no effort to understand computers may '
    'very well get left behind.',
    'for millions of years, mankind lived just like the animals. Then something happened, which unleashed the '
    'power of our imagination. and we learned. to talk.',
    'It doesn\'t have to be like this. All we need to do is make sure. we keep. talking.',
    'All your base are belong to us. You have no chance to survive. Make your time.',
    'The usual measure of vision is a pleasure.',
    'Judge each church, and watch the cheap jam.',
    'Go get the good gold bag, and give the dog a big egg.',
    'Think through three things with both thumbs.',
    'She sells sea shells, and the zoo has six zebras.',
    'The fox gave seven vases of fine coffee.',
    'Put a cup of pepper by the top, and cut the kite.',
    'Could you cook a cookie, good Kate?',
]
COGNATE = {'V': 'F', 'DH': 'TH', 'Z': 'S', 'ZH': 'SH', 'JH': 'CH'}   # a voiced fricative's voiceless one
AF_VOICED_DB = 50 - 60


def klatt_ratio(ph, alt=False):
    """E(4-8 kHz) / E(0-4 kHz) of Klatt's frication spectrum for ph (with A2 60 for a velar before a back vowel)."""
    F1, F2, F3, B1, B2, B3, A2, A3, A4, A5, A6, AB = pf.OBSTRUENT_TARGETS[ph]
    if alt:
        A2 = 60
    amps = (A2, A3, A4, A5, A6, AB)
    par = lambda f: pf.parallel_power((F2, B2), (F3, B3), amps, f)
    return sum(par(f) for f in range(4000, 8000, 25)) / sum(par(f) for f in range(25, 4000, 25))


def noise_filters():
    """{filter number: (phoneme, whether it is the velars' form before a back vowel)} for the noise filters."""
    out = {}
    for code, r in fr.FEATS.items():
        p = tb.NAME[code]
        if r[tb.F_NOISE] and p != 'WH':
            out[r[tb.F_NOISE]] = (p, False)
        if r[tb.F_ALT]:
            out[r[tb.F_ALT]] = (p, True)
    return out


# each frame is weighed by a Hann window (squared, for power), as hb_measure.py measures it, so that the start of a
# frame, where the sound before it may still be dying away in the filters, counts for less
HANN2 = [(0.5 - 0.5 * math.cos(2 * math.pi * i / 1199)) ** 2 for i in range(1200)]


def renderings(texts):
    """For each text: its frame cards, each frame's noise filter (0 for the rest), and its 48 kHz speech."""
    out = []
    for text in texts:
        info = {}
        cards = fr.phonemes_to_cards(tr.compose(text), info)
        values8, _ = vr.voice(cards)
        out.append((cards, info['noise'], ur.samples(ur.upsample(values8))))
    return out


def by_frames(texts, signal):
    """{noise filter: (the Hann-weighted mean square of signal(text) over the filter's frames, frames)}."""
    acc = {}
    for t in texts:
        x, noise = signal(t), t[1]
        for f, nz in enumerate(noise):
            if nz:
                seg = x[1200 * f + ur.HB_DELAY:1200 * f + ur.HB_DELAY + 1200]
                e, n = acc.get(nz, (0.0, 0))
                acc[nz] = (e + sum(w * v * v for w, v in zip(HANN2, seg)), n + 1)
    return {k: (e / (n * sum(HANN2)), n) for k, (e, n) in acc.items()}


def high_band(table):
    """signal() for by_frames: a text's high band at the levels of table, 4 y, delayed as hmix adds it."""
    return lambda t: [0] * ur.HB_DELAY + [ur.HB_UNIT * y for y in ur.hiband(t[0], t[1], table)]


def unit_band(level=40, steps=2000):
    """G2 and PHI: the high band's mean square for a level of 1 (in y), and its share from 4 to 8 kHz."""
    y = ur.hfilt(ur.hnoise([(0, level)] * (steps // 10) + [(-1, 0)]))
    g2 = sum(v * v for v in y) / len(y) / level ** 2
    p = um.spectrum(y)
    return g2, um.band(p, 4000, 8000) / sum(p)


def build():
    fr.load(tb.C)
    g2, phi = unit_band()
    texts = renderings(TEXTS)
    lo = by_frames(texts, lambda t: t[2])
    names = noise_filters()
    for idx, (p, _) in names.items():
        if idx not in lo:
            raise SystemExit('no frames of %s in the texts' % p)
    order = sorted(names, key=lambda i: (names[i][0] in COGNATE, names[i]))
    # the voiceless sounds' levels: first from the high band's power at a steady level, then corrected twice by
    # the high band as hnoise and hfilt make it in the texts, ramps and all
    want = {i: klatt_ratio(*names[i]) * lo[i][0] for i in order if names[i][0] not in COGNATE}
    level = {i: math.sqrt(w / (ur.HB_UNIT ** 2 * g2 * phi)) for i, w in want.items()}
    for _ in range(PASSES):
        table = tabulate(level, names, len(fr.FILTERS))
        hb = by_frames(texts, high_band(table))
        level = {i: table[i] * math.sqrt(w / (phi * hb[i][0])) for i, w in want.items()}
    table = tabulate(level, names, len(fr.FILTERS))
    rows = []
    for i in order:
        p, alt = names[i]
        R = None if p in COGNATE else klatt_ratio(p, alt)
        rows.append((p + (' (back)' if alt else ''), i, lo[i][1], '%.1f' % (10 * math.log10(R)) if R else
                     COGNATE[p] + ' - 10 dB', math.sqrt(lo[i][0]), table[i]))
    return table, rows, g2, phi


PASSES = 2


def tabulate(level, names, nf):
    """The table: the voiceless sounds' levels rounded, and each voiced fricative its cognate's, 10 dB down."""
    table = [0] * nf
    by_name = {names[i]: v for i, v in level.items()}
    for i, (p, alt) in names.items():
        v = level[i] if p not in COGNATE else by_name[(COGNATE[p], False)] * 10 ** (AF_VOICED_DB / 20)
        table[i] = int(round(v))
        assert 0 < table[i] <= 60, (p, table[i])
    return table


# By ear (Jason, 2026-11-19): at Klatt's levels the high band sounded like static. In a blind test of the
# fricatives' band at full, half and a quarter level, with no high band on the stops' bursts, a quarter level
# was clearest. So the table keeps a quarter of each fricative's level (a level that would round to 0 stays 0)
# and gives the bursts none.
SCALE = 0.25
STOPS = ('P', 'T', 'K', 'B', 'D', 'G')


def by_ear(table, rows):
    out = list(table)
    for name, i, *_ in rows:
        v = table[i] * SCALE
        out[i] = 0 if name.split()[0] in STOPS or v < 0.5 else max(1, round(v))
    return out


if __name__ == '__main__':
    table, rows, g2, phi = build()
    table = by_ear(table, rows)
    open(os.path.join(ur.TABLES, 'hiband.cards'), 'w').write('\n'.join(map(str, table)) + '\n')
    print('the high band at a level of 1: mean square %.3f, %.1f percent of it from 4 to 8 kHz' % (g2, 100 * phi))
    print('%-10s %6s %6s %18s %18s %5s' % ('sound', 'filter', 'frames', 'Klatt 4-8/0-4 dB', 'speech rms 0-4k', 'level'))
    for r in rows:
        print('%-10s %6d %6d %18s %18.1f %5d' % r)
