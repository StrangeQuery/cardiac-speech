"""The phoneme table: the one piece of offline precomputation (the Speak & Spell's ROM).

Turning the published formant figures (Klatt 1980) and powers (Sacia and Beck 1926) into reflection coefficients
and gains needs cosines, exponentials, square roots and the Levinson recursion, so it is done here, once, in
floating point, with the prototype's own functions (prototype/phonemes_to_frames.py), and stored as cards:

  front/features.cards   one record of FEAT cards for each phoneme code (codes 3-43, record r at r*FEAT)
  front/filters.cards    one record of 11 cards for each filter: K10..K1 (k x 1000) and a gain G
  front/glides.cards     one record of 3 x 97 cards for each filter up to the last a segment glides from:
                         the level factors for its glides (see glide_table)

Everything else (durations, glides, pitch, levels, the choice of filter for each frame) is worked out by the
CARDIACs.  The gains fold in only what is fixed for a filter: 1/sqrt(E) of its impulse response (with the 0.9
de-emphasis, and for a voiced filter the excitation's low-pass e = pulse + 0.5 e in front), the phoneme's own power where the filter always speaks for one phoneme, the fixed level offsets
(-10 dB for a sonorant, -14 dB for aspiration), and the scale C.  Unvoiced filters are scaled by sqrt(60)/100
so that a voiced frame's sqrt(P), worked out on the CARDIAC as isqrt(60 P) / 100, keeps the float model's
voiced to unvoiced balance."""
import math
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'prototype'))
import phonemes_to_frames as pf   # noqa: E402

# codes 3-12 the vowels that take secondary stress, 13-18 the others, AX last; then the consonants
PHONEMES = ['IY', 'EY', 'AE', 'AA', 'AO', 'OW', 'UW', 'AY', 'AW', 'OY', 'IH', 'EH', 'AH', 'UH', 'ER', 'AX',
            'W', 'Y', 'R', 'L', 'M', 'N', 'NX', 'P', 'T', 'K', 'B', 'D', 'G',
            'F', 'TH', 'S', 'SH', 'V', 'DH', 'Z', 'ZH', 'CH', 'JH', 'HH', 'WH']
CODE = {p: i + 3 for i, p in enumerate(PHONEMES)}
NAME = {c: p for p, c in CODE.items()}
KIND = {'vowel': 1, 'sonorant': 2, 'nasal': 3, 'stop': 4, 'fric': 5, 'affricate': 6, 'aspirate': 7}
FEAT = 17
# feature record fields
F_KIND, F_INH, F_MN, F_CLS9, F_LIQ, F_VLS, F_BACK, F_TS, F_TE, F_ASP, F_VOICED, F_NOISE, F_ALT, F_VBAR, F_LOUD, \
    F_CINH, F_CTOT = range(FEAT)

C = 36.0         # the scale: the loudest test sentences then reach about 750 in the lattice (cells hold 999)
UNVOICED = math.sqrt(60) / 100
LOUD = 999 / math.sqrt(1870)          # loudness sqrt(POWER) scaled so AO is 999


def kind_of(p):
    if p == 'WH':
        p = 'W'
    if p in pf.VOWELS: return 'vowel'
    if p in pf.SONORANTS: return 'sonorant'
    if p in pf.NASALS: return 'nasal'
    if p in pf.STOPS: return 'stop'
    if p in pf.VL_FRIC | pf.VD_FRIC: return 'fric'
    if p in pf.AFFRICATES: return 'affricate'
    return 'aspirate'


def energy(a, voiced, n=600):
    """E of a filter: the energy of the impulse response of 1/A(z) and the de-emphasis (the prototype's
    impulse_energy), with a voiced filter's input the excitation's low-pass, 0.5^n, instead of one pulse."""
    if not voiced:
        return pf.impulse_energy(a, n)
    p = len(a) - 1
    y = [0.0] * n
    e, zd = 0.0, 0.0
    for i in range(n):
        v = 0.5 ** i
        for j in range(1, p + 1):
            if i - j >= 0:
                v -= a[j] * y[i - j]
        y[i] = v
        zd = v + pf.PRE * zd
        e += zd * zd
    return e


def kcards(ks):
    return [max(-999, min(999, int(round(k * 1000)))) for k in reversed(ks)]


VOICED = []      # build fills it: whether each filter speaks voiced (its gain counts the excitation's low-pass)
OWN = set()      # build fills it: the filters a segment's frames glide from (vowels' ts, te and aspirated
                 # forms, sonorants' and nasals' ts)


def build(C):
    filters = [None]          # record 0: none
    VOICED[:] = [False]
    OWN.clear()

    def add(ks, a, power, voiced, son=False):
        E = energy(a, voiced)
        g = C * math.sqrt(power / E)
        if son:
            g *= 1000 / LOUD
        if not voiced:
            g *= UNVOICED
        G = int(round(g))
        assert G <= 999 or C > 1e5, ('gain', G, power)
        filters.append(kcards(ks) + [G])
        VOICED.append(voiced)
        return len(filters) - 1

    def cascade(fb):
        a = pf.poly_from_formants(fb)
        return pf.step_down(a), a

    F45 = [(pf.F4, pf.B4), (pf.F5, pf.B5)]
    feats = {}
    asp = {}
    for p in PHONEMES:
        if p == 'WH':
            continue
        k = kind_of(p)
        r = [0] * FEAT
        r[F_KIND] = KIND[k]
        if k == 'affricate':
            (ci, cm), (fi, fm) = pf.DUR[p]
            r[F_INH], r[F_MN], r[F_CINH], r[F_CTOT] = ci + fi, cm + fm, ci, ci + fi
        else:
            r[F_INH], r[F_MN] = pf.DUR[p]
        r[F_CLS9] = (160 if (p in pf.VD_FRIC or p == 'JH') else 120 if p in ('B', 'D', 'G') else
                     70 if p in pf.VL_STOPS else 85 if k == 'nasal' else 100)
        r[F_LIQ] = 1 if p in ('L', 'R', 'M', 'N', 'NX') else 0
        r[F_VLS] = 1 if p in pf.VL_STOPS else 0
        r[F_BACK] = 1 if p in pf.BACK_VOWELS else 0
        r[F_VOICED] = 1 if p in ('B', 'D', 'G', 'JH') or p in pf.VD_FRIC else 0
        if k in ('vowel', 'aspirate'):
            r[F_LOUD] = int(round(math.sqrt(pf.POWER[p]) * LOUD)) if k == 'vowel' else 0
        if k == 'vowel':
            tv = pf.VOWEL_TARGETS[p]
            for slot, t in ((F_TS, tv[0]), (F_TE, tv[-1])):
                ks, a = cascade([(t[0], t[3]), (t[1], t[4]), (t[2], t[5])] + F45)
                r[slot] = add(ks, a, pf.POWER[p], True)
            t = tv[0]
            ks, a = cascade([(t[0], 300), (t[1], t[4]), (t[2], t[5])] + F45)
            r[F_ASP] = add(ks, a, pf.POWER[p] * pf.db(pf.ASPIRATION_DB), False)
            asp[p] = r[F_ASP]
        elif k == 'sonorant':
            t = pf.SONORANT_TARGETS[p]
            ks, a = cascade([(t[0], t[3]), (t[1], t[4]), (t[2], t[5])] + F45)
            r[F_TS] = r[F_TE] = add(ks, a, pf.db(pf.SONORANT_DB), True, son=True)
            ks, a = cascade([(t[0], 300), (t[1], t[4]), (t[2], t[5])] + F45)
            r[F_ASP] = add(ks, a, pf.db(pf.ASPIRATION_DB), False, son=True)
        elif k == 'nasal':
            t = pf.NASAL_TARGETS[p]
            ks, a = cascade([(pf.FNP, pf.BNP), (t[3], t[6]), (t[4], t[7])] + F45)
            r[F_TS] = r[F_TE] = add(ks, a, pf.POWER[p], True)
        elif k in ('stop', 'fric', 'affricate'):
            t = pf.OBSTRUENT_TARGETS[p][:6]
            ks, a = cascade([(t[0], t[3]), (t[1], t[4]), (t[2], t[5])] + F45)
            r[F_TS] = r[F_TE] = add(ks, a, 1.0, True)        # the locus, for the neighbours' glides only
            filters[r[F_TS]][10] = 0
            if k == 'stop':
                pw = pf.POWER[p] * pf.DUR[p][0] / pf.FRAME_MS
                ks, a = pf.noise_filter(p, False)
                r[F_NOISE] = add(ks, a, pw, False)
                if p in ('K', 'G'):
                    ks, a = pf.noise_filter(p, True)
                    r[F_ALT] = add(ks, a, pw, False)
                # the bursts at twice the gain of their power (+6 dB), chosen by ear
                for slot in (F_NOISE, F_ALT):
                    if r[slot]:
                        filters[r[slot]][10] *= 2
                if p in ('B', 'D', 'G'):
                    ks, a = pf.voicebar_filter(p)
                    r[F_VBAR] = add(ks, a, pf.VOICEBAR_POWER, True)
            else:
                vd = r[F_VOICED]
                ks, a = pf.voiced_fric_filter(p) if vd else pf.noise_filter(p, False)
                r[F_NOISE] = add(ks, a, pf.POWER[p], bool(vd))
        if k == 'vowel':
            OWN.update([r[F_TS], r[F_TE], r[F_ASP]])
        elif k in ('sonorant', 'nasal'):
            OWN.add(r[F_TS])
        feats[p] = r
    # HH: its filter is the aspirated form of the vowel after it (or AX): the vowels' F_ASP records
    feats['HH'][F_TS] = 0
    feats['WH'] = list(feats['W'])
    return feats, filters


GLIDE_W = (3, 5, 9)          # the glides' weights (front_ref.glide_weight), in this order in a record


def blend(x, y, u):
    v = x * (10 - u) + y * u
    return -((-v) // 10) if v < 0 else v // 10


def k_energy(K, voiced, n=600):
    """E of a filter given as its cards K10..K1: the lattice's impulse response through the de-emphasis, with a
    voiced filter's input the excitation's low-pass (as energy() for a polynomial)."""
    ks = [k / 1000 for k in reversed(K)]
    b = [0.0] * 11
    yd = tot = 0.0
    for i in range(n):
        f = 0.5 ** i if voiced else (1.0 if i == 0 else 0.0)
        for j in range(10, 0, -1):
            f = f - ks[j - 1] * b[j - 1]
            b[j] = b[j - 1] + ks[j - 1] * f
        b[0] = f
        yd = f + pf.PRE * yd
        tot += yd * yd
    return tot


def glide_table(filters):
    """The glides' level factors. A frame at a segment's end glides its own filter o towards halfway to a
    neighbour's n, K = (m (10 - w) + Ko w) / 10 with m = (Kn + Ko) / 2, and that filter speaks more quietly (or
    loudly) than o, which the gain was made for. Its factor puts the power back: c = 100 sqrt(E(o) / E(K)), at
    most 999, in percent. Record o (for o up to the largest own filter) holds c for each neighbour n (0 to the last
    filter) and weight w, card 3 n + 0, 1, 2 for w = 3, 5, 9; filters that aren't an own filter get 100."""
    nf = len(filters)
    deck = []
    for o in range(max(OWN) + 1):
        if o not in OWN:
            deck += [100] * (3 * nf)
            continue
        Ko = filters[o][:10]
        Eo = k_energy(Ko, VOICED[o])
        for n in range(nf):
            Kn = filters[n][:10] if n else [0] * 10
            for w in GLIDE_W:
                K = [blend(blend(a, b, 5), b, w) for a, b in zip(Kn, Ko)]
                deck.append(min(999, int(round(100 * (Eo / k_energy(K, VOICED[o])) ** 0.5))))
    return deck


def write(C, folder):
    feats, filters = build(C)
    deck = [8] + [0] * (FEAT - 1) + [0] * (FEAT * 2)       # row 0: a pause (kind 8)
    for p in PHONEMES:
        deck += feats[p]
    fl = []
    for rec in filters[1:]:
        fl += rec
    fl = [0] * 11 + fl
    open(os.path.join(folder, 'features.cards'), 'w').write('\n'.join(map(str, deck)) + '\n')
    open(os.path.join(folder, 'filters.cards'), 'w').write('\n'.join(map(str, fl)) + '\n')
    gl = glide_table(filters)
    open(os.path.join(folder, 'glides.cards'), 'w').write('\n'.join(map(str, gl)) + '\n')
    return feats, filters


if __name__ == '__main__':
    C = float(sys.argv[1]) if len(sys.argv) > 1 else C
    feats, filters = write(C, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'front'))
    print(len(feats), 'phonemes,', len(filters) - 1, 'filters,', max(OWN) + 1, 'glide records of', 3 * len(filters))
