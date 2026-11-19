#!/opt/homebrew/bin/python3
"""Phonemes -> LPC frame cards (25 ms frames: voiced, pitch period, gain, k1..k10) for the synthesizers here.

usage: phonemes_to_frames.py in.phon out.frames [--rate R]

in.phon is text_to_phonemes.py output (one line of tokens; lines starting with # are comments).

Every phoneme is a set of formant targets (Klatt 1980, Tables I-III), a duration from Klatt's 1979
duration rules, and a relative power (Sacia and Beck 1926, Table V).  Voiced frames: the formants become
pole pairs at 8 kHz (Klatt's resonator, Eq. 2: r = exp(-pi B T), angle 2 pi F T), the product polynomial
A(z) of order 10 is stepped down to 10 reflection coefficients.  Noise frames: the Klatt parallel-branch
spectrum (formant amplitudes A2..A6 and bypass AB in dB) is turned into an autocorrelation and fitted by
Levinson's recursion, order 10.  Gains are set so each frame's output power (after the synthesizer's
de-emphasis) matches the phoneme's power.  See TTS_SOURCES.md for where each number comes from and which
numbers are my estimates.
"""
import math
import sys
from common import write_frames, RATE, ORDER, PRE
from encode import levinson

FRAME_MS = 25.0
T = 1.0 / RATE

# ---------------------------------------------------------------------------------------------------
# Klatt (1980) Table I typical constant values: F4 3300/B4 250, F5 3750/B5 200, F6 4900/B6 1000.
F4, B4, F5, B5, F6, B6 = 3300, 250, 3750, 200, 4900, 1000
FNP, BNP = 270, 100          # nasal pole: Klatt 1980 text, "270 Hz (the frequency of the fixed nasal pole)"; BNP Table I

# Klatt (1980) Table II vowels: (F1, F2, F3, B1, B2, B3); a second row is the off-glide.
# AX (schwa) is not in Table II: Table I's typical F1-F3/B1-B3 (450/1450/2450, 50/70/110) are used.
VOWEL_TARGETS = {
    'IY': [(310, 2020, 2960, 45, 200, 400), (290, 2070, 2960, 60, 200, 400)],
    'IH': [(400, 1800, 2570, 50, 100, 140), (470, 1600, 2600, 50, 100, 140)],
    'EY': [(480, 1720, 2520, 70, 100, 200), (330, 2020, 2600, 55, 100, 200)],
    'EH': [(530, 1680, 2500, 60, 90, 200), (620, 1530, 2530, 60, 90, 200)],
    'AE': [(620, 1660, 2430, 70, 150, 320), (650, 1490, 2470, 70, 100, 320)],
    'AA': [(700, 1220, 2600, 130, 70, 160)],
    'AO': [(600, 990, 2570, 90, 100, 80), (630, 1040, 2600, 90, 100, 80)],
    'AH': [(620, 1220, 2550, 80, 50, 140)],
    'OW': [(540, 1100, 2300, 80, 70, 70), (450, 900, 2300, 80, 70, 70)],
    'UH': [(450, 1100, 2350, 80, 100, 80), (500, 1180, 2390, 80, 100, 80)],
    'UW': [(350, 1250, 2200, 65, 110, 140), (320, 900, 2200, 65, 110, 140)],
    'ER': [(470, 1270, 1540, 100, 60, 110), (420, 1310, 1540, 100, 60, 110)],
    'AY': [(660, 1200, 2550, 100, 70, 200), (400, 1880, 2500, 70, 100, 200)],
    'AW': [(640, 1230, 2550, 80, 70, 140), (420, 940, 2350, 80, 70, 80)],
    'OY': [(550, 960, 2400, 80, 50, 130), (360, 1820, 2450, 60, 50, 160)],
    'AX': [(450, 1450, 2450, 50, 70, 110)],
}

# Klatt (1980) Table III.  Sonorants: (F1, F2, F3, B1, B2, B3).
SONORANT_TARGETS = {
    'W': (290, 610, 2150, 50, 80, 60),
    'Y': (260, 2070, 3020, 40, 250, 500),
    'R': (310, 1060, 1380, 70, 100, 120),
    'L': (310, 1050, 2880, 50, 100, 280),
}
# Nasals: FNP FNZ F1 F2 F3 B1 B2 B3.  NX is not in the table: estimated, Klatt's velar locus (k/g F2 1990,
# F3 2850) with the n bandwidths.
NASAL_TARGETS = {
    'M': (270, 450, 480, 1270, 2130, 40, 200, 200),
    'N': (270, 450, 480, 1340, 2470, 40, 300, 300),
    'NX': (270, 450, 480, 1990, 2850, 40, 300, 300),
}
# Fricatives, affricates (frication part), plosives (burst): F1 F2 F3 B1 B2 B3 A2 A3 A4 A5 A6 AB.
# [th] A5 is blank in the printed table: taken as 0.  ZH is not in the table: estimated as SH with
# Klatt's voiced/voiceless difference (lower F1 and B1, as z vs s: F1 240, B1 70).
OBSTRUENT_TARGETS = {
    'F':  (340, 1100, 2080, 200, 120, 150, 0, 0, 0, 0, 0, 57),
    'V':  (220, 1100, 2080, 60, 90, 120, 0, 0, 0, 0, 0, 57),
    'TH': (320, 1290, 2540, 200, 90, 200, 0, 0, 0, 0, 28, 48),
    'DH': (270, 1290, 2540, 60, 80, 170, 0, 0, 0, 0, 28, 48),
    'S':  (320, 1390, 2530, 200, 80, 200, 0, 0, 0, 0, 52, 0),
    'Z':  (240, 1390, 2530, 70, 60, 180, 0, 0, 0, 0, 52, 0),
    'SH': (300, 1840, 2750, 200, 100, 300, 0, 57, 48, 48, 46, 0),
    'ZH': (240, 1840, 2750, 70, 100, 300, 0, 57, 48, 48, 46, 0),
    'CH': (350, 1800, 2820, 200, 90, 300, 0, 44, 60, 53, 53, 0),
    'JH': (260, 1800, 2820, 60, 80, 270, 0, 44, 60, 53, 53, 0),
    'P':  (400, 1100, 2150, 300, 150, 220, 0, 0, 0, 0, 0, 63),
    'B':  (200, 1100, 2150, 60, 110, 130, 0, 0, 0, 0, 0, 63),
    'T':  (400, 1600, 2600, 300, 120, 250, 0, 30, 45, 57, 63, 0),
    'D':  (200, 1600, 2600, 60, 100, 170, 0, 47, 60, 62, 60, 0),
    'K':  (300, 1990, 2850, 250, 160, 330, 0, 53, 43, 45, 45, 0),
    'G':  (200, 1990, 2850, 60, 150, 280, 0, 53, 43, 45, 45, 0),
}
# Klatt 1980 source amplitudes (dB): voiceless fricative AF 60; voiced fricative AF 50, AV 47, AVS 47.

# Klatt (1979) Table 1: inherent and minimum duration, ms.  ER here is Klatt's RR ("bird").
# Affricates: (closure, frication) pairs.
DUR = {
    'IY': (160, 50), 'EY': (190, 70), 'OW': (220, 70), 'UW': (210, 60), 'AE': (230, 60), 'AO': (240, 80),
    'AY': (250, 90), 'OY': (280, 110), 'AX': (120, 40), 'IH': (130, 40), 'EH': (150, 60), 'AH': (140, 50),
    'UH': (160, 50), 'AA': (240, 80), 'ER': (180, 60), 'AW': (260, 100),
    'W': (80, 60), 'R': (80, 30), 'WH': (70, 60), 'Y': (80, 40), 'L': (80, 40), 'HH': (80, 20),
    'M': (70, 60), 'N': (65, 35), 'NX': (80, 50),
    'F': (120, 60), 'TH': (110, 40), 'S': (125, 50), 'SH': (125, 50),
    'V': (60, 40), 'DH': (50, 30), 'Z': (75, 40), 'ZH': (70, 40),
    'P': (85, 50), 'T': (65, 40), 'K': (65, 50), 'B': (80, 50), 'D': (65, 40), 'G': (65, 50),
    'CH': ((70, 50), (60, 40)), 'JH': ((70, 50), (30, 20)),
}

# Sacia and Beck (1926) Table V, column A: mean conversational power, arbitrary units (16 speakers).
# Entries marked est. are not in column A: scaled from column B (peak power) by a measured neighbour,
# power_A(x) = power_B(x) * power_A(ref) / power_B(ref); the reference is named.  Vowels absent from the
# table use the vowel named.
POWER = {
    'AO': 1870, 'AA': 1380, 'OW': 875, 'EY': 808, 'EH': 664, 'AH': 616, 'UW': 532, 'IY': 484,
    'ER': 384, 'AE': 366, 'IH': 346, 'N': 84, 'M': 74, 'SH': 73, 'CH': 58, 'S': 38, 'Z': 29, 'JH': 19,
    'NX': 14, 'K': 14, 'L': 13, 'T': 6, 'D': 3, 'F': 3, 'V': 1,
    'UH': 616,            # est.: B(took)=688, ref AH: A 616 / B 688
    'ZH': 24,             # est.: B 63, ref SH: 73/192
    'DH': 5.5,            # est.: B 15, ref V: 1/41 gives 0.4; ref F (3/6) gives 7.5; mean of the two
    'G': 18,              # est.: B 13, ref K: 14/10
    'B': 2.5, 'P': 2.5,   # est.: B 11, ref T: 6/26
    'TH': 0.5,            # est.: B 1, ref F: 3/6
    'AY': 1380, 'AW': 1380, 'OY': 1870,     # diphthongs: their onset vowel (AA, AA, AO)
    'AX': 616,            # schwa: AH ("ton")
}

VOWELS = set(VOWEL_TARGETS)
SONORANTS = set(SONORANT_TARGETS)
NASALS = set(NASAL_TARGETS)
STOPS = {'P', 'B', 'T', 'D', 'K', 'G'}
VL_STOPS = {'P', 'T', 'K'}
VL_FRIC = {'F', 'TH', 'S', 'SH'}
VD_FRIC = {'V', 'DH', 'Z', 'ZH'}
AFFRICATES = {'CH', 'JH'}
ASPIRATES = {'HH'}
BACK_VOWELS = {'AA', 'AO', 'OW', 'UH', 'UW', 'AH', 'AW', 'ER'}
PHONEMES = sorted(VOWELS | SONORANTS | NASALS | STOPS | VL_FRIC | VD_FRIC | AFFRICATES | ASPIRATES | {'WH'})
PAUSES = {',': 300, '.': 600, '?': 600, '!': 600}    # Klatt 1979 rule 1 gives 200 ms at a comma; lengthened by ear

# ----- my estimates (see TTS_SOURCES.md) -----
TRANS_MS = 40.0           # formant transition length on each side of a boundary
UNSTRESSED_DB = -3.0      # unstressed vowel level re stressed
VOWEL_DECAY_DB = -3.0     # "falls gradually by a few dB near the end of the syllable" (Klatt 1980)
SONORANT_DB = -10.0       # Klatt 1980: prevocalic sonorant AV about 10 dB below the vowel (stated)
ASPIRATION_DB = -14.0     # aspiration (HH, release of p t k) re the following vowel
VOICEBAR_POWER = 1.5      # voiced-stop closure murmur, Sacia-Beck units
F0_START, F0_END = 130.0, 100.0   # Klatt 1980: isolated vowel F0 falls 130 -> 100 Hz (applied per sentence)
F0_STRESS1, F0_STRESS2 = 0.15, 0.07   # rise at a stressed vowel's onset, fraction of the baseline
F0_FINAL = 85.0           # end of a statement
F0_QUESTION = 160.0       # end of a question
END_PAD_MS = 150.0
START_PAD_MS = 50.0


# ===================================================================================================
# Pole pairs, polynomials, reflection coefficients

def poly_from_formants(fb):
    """A(z) = prod (1 - 2 r cos(theta) z^-1 + r^2 z^-2), r = exp(-pi B T), theta = 2 pi F T (Klatt Eq. 2)."""
    a = [1.0]
    for F, B in fb:
        r = math.exp(-math.pi * B * T)
        c1, c2 = -2 * r * math.cos(2 * math.pi * F * T), r * r
        n = [0.0] * (len(a) + 2)
        for i, v in enumerate(a):
            n[i] += v
            n[i + 1] += v * c1
            n[i + 2] += v * c2
        a = n
    return a


def step_down(a):
    """Backward Levinson: A(z) = 1 + sum a_j z^-j  ->  k_1..k_p with k_i = a_i^(i) (encode.py's convention)."""
    a = list(a)
    p = len(a) - 1
    ks = [0.0] * p
    for i in range(p, 0, -1):
        k = a[i]
        assert abs(k) < 1, 'unstable polynomial (|k%d| = %.4f)' % (i, abs(k))
        ks[i - 1] = k
        d = 1 - k * k
        a = [1.0] + [(a[j] - k * a[i - j]) / d for j in range(1, i)]
    return ks


def impulse_energy(a, n=600):
    """Energy of the impulse response of 1/A(z) followed by the synthesizer's de-emphasis 1/(1 - 0.9 z^-1)."""
    p = len(a) - 1
    y = [0.0] * n
    e, zd = 0.0, 0.0
    for i in range(n):
        v = 1.0 if i == 0 else 0.0
        for j in range(1, p + 1):
            if i - j >= 0:
                v -= a[j] * y[i - j]
        y[i] = v
        zd = v + PRE * zd
        e += zd * zd
    return e


def resonance(f, F, B):
    """Peak-normalized magnitude of an analog formant resonance at frequency f."""
    x = 1 - (f / F) ** 2
    return (B / F) / math.sqrt(x * x + (f * B / (F * F)) ** 2)


NGRID = 256


def fit_spectrum(power_at):
    """All-pole order-10 fit (autocorrelation method) to a power spectrum given as a function of Hz.
    The target is pre-multiplied by |1 - 0.9 e^-jw|^2 so that the synthesizer's de-emphasis restores it."""
    P = []
    for i in range(NGRID + 1):
        w = math.pi * i / NGRID
        f = w * RATE / (2 * math.pi)
        pre = 1 + PRE * PRE - 2 * PRE * math.cos(w)
        P.append(max(power_at(f), 1e-12) * pre)
    r = []
    for m in range(ORDER + 1):
        s = P[0] + P[NGRID] * math.cos(math.pi * m)
        s += 2 * sum(P[i] * math.cos(math.pi * i * m / NGRID) for i in range(1, NGRID))
        r.append(s / (2 * NGRID))
    r[0] *= 1.0001
    ks, a = levinson(r, ORDER)
    return ks, a


def parallel_power(F2, F3, amps, f, extra=None):
    """Klatt parallel branch: sum of formant resonances with amplitudes A2..A6 (dB) plus bypass AB."""
    A2, A3, A4, A5, A6, AB = amps
    s = 0.0
    for A, F, B in ((A2, F2[0], F2[1]), (A3, F3[0], F3[1]), (A4, F4, B4), (A5, F5, B5), (A6, F6, B6)):
        if A > 0:
            s += (10 ** (A / 20) * resonance(f, F, B)) ** 2
    if AB > 0:
        s += 10 ** (AB / 10)
    return s


def cascade_power(fb, f):
    s = 1.0
    for F, B in fb:
        s *= resonance(f, F, B) ** 2 * (F / B) ** 2       # unity gain at DC, natural peak heights
    return s


# ===================================================================================================
# Segments

class Seg:
    def __init__(self, ph, stress=0):
        self.ph = ph
        self.stress = stress
        self.word = -1
        self.dur = 0.0
        self.frames = 0
        self.kind = ''


def parse_phon(text):
    toks = []
    for line in text.splitlines():
        if line.startswith('#') and not line.startswith('# ') and line.strip() != '#':
            pass
        if line.startswith('# ') or not line.strip():
            continue
        toks.extend(line.split())
    return toks


def build_segments(toks):
    segs = []
    word = 0
    for t in toks:
        t = t.lstrip('~')
        if t == '#':
            word += 1
            continue
        if t in PAUSES or t == '?':
            s = Seg(t)
            s.kind = 'pause'
            segs.append(s)
            word += 1
            continue
        st = 0
        if t[-1].isdigit():
            st, t = int(t[-1]), t[:-1]
        if t == 'WH':
            t = 'W'           # WH spoken as W (the wine/whine merger): my choice
        assert t in PHONEMES, 'unknown phoneme %s' % t
        s = Seg(t, st)
        s.word = word
        segs.append(s)
    for s in segs:
        if s.kind:
            continue
        s.kind = ('vowel' if s.ph in VOWELS else 'sonorant' if s.ph in SONORANTS else 'nasal' if s.ph in NASALS
                  else 'stop' if s.ph in STOPS else 'fric' if s.ph in VL_FRIC | VD_FRIC
                  else 'affricate' if s.ph in AFFRICATES else 'aspirate')
    return segs


def assign_consonant_stress(segs):
    """Klatt 1979: consonants before a stressed vowel in the same word are stressed (if they form a
    word-initial-like cluster: here a word-initial cluster, or the last consonant before the vowel)."""
    for i, s in enumerate(segs):
        if s.kind != 'vowel' or s.stress == 0:
            continue
        j = i - 1
        n = 0
        while j >= 0 and segs[j].kind not in ('vowel', 'pause') and segs[j].word == s.word:
            j -= 1
            n += 1
        word_initial = j < 0 or segs[j].word != s.word
        for m in range(i - n, i):
            if word_initial or m == i - 1:
                segs[m].stress = 1


def klatt_durations(segs, rate=1.0):
    """Klatt (1979) duration rules 1-7, 9-11: DUR = (INHDUR - MINDUR) * PRCNT / 100 + MINDUR."""
    n = len(segs)
    # phrase structure: a phrase ends at a pause token
    def next_real(i, step):
        j = i + step
        while 0 <= j < n and segs[j].kind == 'pause':
            return None
        return j if 0 <= j < n else None
    words = {}
    for i, s in enumerate(segs):
        if s.kind != 'pause':
            words.setdefault(s.word, []).append(i)
    word_vowels = {w: [i for i in idx if segs[i].kind == 'vowel'] for w, idx in words.items()}
    # last word before each pause
    phrase_final_word = set()
    for i, s in enumerate(segs):
        if s.kind == 'pause' and i > 0 and segs[i - 1].kind != 'pause':
            phrase_final_word.add(segs[i - 1].word)
    for i, s in enumerate(segs):
        if s.kind == 'pause':
            s.dur = PAUSES.get(s.ph, 0)
            continue
        if s.kind == 'affricate':
            (inh, mn), (inh2, mn2) = DUR[s.ph]
            inh, mn = inh + inh2, mn + mn2
        else:
            inh, mn = DUR[s.ph]
        w = s.word
        wv = word_vowels[w]
        last_v = wv[-1] if wv else None
        in_final_syll = last_v is not None and (i >= last_v or all(segs[j].kind != 'vowel' for j in range(i + 1, words[w][-1] + 1)))
        phrase_final = w in phrase_final_word and in_final_syll
        pr = 100.0
        syllabic = s.kind == 'vowel'
        # 2: clause-final lengthening (vowel of the last syllable and the consonants after it)
        if phrase_final and (syllabic or (last_v is not None and i > last_v)):
            pr *= 1.4
        # 3: non-phrase-final shortening; phrase-final postvocalic liquid or nasal lengthened
        if syllabic and not phrase_final:
            pr *= 0.6
        if phrase_final and last_v is not None and i > last_v and s.ph in ('L', 'R', 'M', 'N', 'NX'):
            pr *= 1.4
        # 4: non-word-final shortening
        if syllabic and not in_final_syll:
            pr *= 0.85
        # 5: polysyllabic shortening
        if syllabic and len(wv) > 1:
            pr *= 0.8
        # 6: non-initial consonant shortening
        if not syllabic and i != words[w][0]:
            pr *= 0.85
        # 7: unstressed shortening
        if s.stress != 1:
            if s.stress == 0:
                mn = mn / 2
            if syllabic:
                pr *= 0.5 if (wv and i not in (wv[0], wv[-1])) else 0.7
            elif s.kind in ('sonorant',) and i + 1 < n and segs[i + 1].kind == 'vowel':
                pr *= 0.1
            else:
                pr *= 0.7
        # 9: postvocalic context of vowels
        if syllabic:
            j = i + 1
            post = [k for k in range(j, n) if segs[k].kind != 'pause' and segs[k].word == w]
            cons = []
            for k in post:
                if segs[k].kind == 'vowel':
                    break
                cons.append(segs[k])
            obs = [c for c in cons if c.kind in ('stop', 'fric', 'affricate')]
            c = obs[0] if obs else (cons[0] if cons else None)
            if c is None:
                p1 = 1.2 if in_final_syll else 1.0
            elif c.ph in VD_FRIC or c.ph == 'JH':
                p1 = 1.6
            elif c.ph in ('B', 'D', 'G'):
                p1 = 1.2
            elif c.kind == 'nasal' and c.stress == 0:
                p1 = 0.85
            elif c.ph in VL_STOPS:
                p1 = 0.7
            else:
                p1 = 1.0
            if not phrase_final:
                p1 = 0.7 + 0.3 * p1
            pr *= p1
        # 10: clusters (across words, not across pauses)
        prev = segs[i - 1] if i > 0 and segs[i - 1].kind != 'pause' else None
        nxt = segs[i + 1] if i + 1 < n and segs[i + 1].kind != 'pause' else None
        if syllabic:
            if nxt is not None and nxt.kind == 'vowel':
                pr *= 1.2
            if prev is not None and prev.kind == 'vowel':
                pr *= 0.7
        else:
            pc = prev is not None and prev.kind != 'vowel'
            nc = nxt is not None and nxt.kind != 'vowel'
            if pc and nc:
                pr *= 0.5
            elif pc or nc:
                pr *= 0.7
        dur = (inh - mn) * pr / 100 + mn
        # 11: lengthening due to plosive aspiration
        if s.stress >= 1 and s.kind in ('vowel', 'sonorant') and prev is not None and prev.ph in VL_STOPS:
            dur += 25
        s.dur = dur / rate


# ===================================================================================================
# Frames

def frames_from_ms(segs):
    """Quantize durations to 25 ms frames, carrying the rounding error so the total stays right.
    Stops get one burst frame (and p t k before a vowel or sonorant an aspiration frame taken from the
    next segment); every sounding segment keeps at least one frame."""
    acc = 0.0
    t = 0.0
    for i, s in enumerate(segs):
        acc += s.dur
        n = int(round(acc / FRAME_MS)) - int(round(t / FRAME_MS))
        t = acc
        minimum = 0 if s.kind == 'pause' else 2 if s.kind in ('stop', 'affricate') else 1
        s.frames = max(minimum, n)


def lerp(a, b, u):
    return tuple(x + (y - x) * u for x, y in zip(a, b))


def targets(s, nxt):
    """(start, end) formant target tuples (F1 F2 F3 B1 B2 B3) for transitions."""
    if s.kind == 'vowel':
        tv = VOWEL_TARGETS[s.ph]
        return tv[0], tv[-1]
    if s.kind == 'sonorant':
        return SONORANT_TARGETS[s.ph], SONORANT_TARGETS[s.ph]
    if s.kind == 'nasal':
        t = NASAL_TARGETS[s.ph][2:]
        return t, t
    if s.kind == 'aspirate':
        # Klatt 1980: [h] takes the following vowel's formants with B1 about 300 Hz
        if nxt is not None and nxt.kind == 'vowel':
            t = VOWEL_TARGETS[nxt.ph][0]
        else:
            t = VOWEL_TARGETS['AX'][0]
        t = (t[0], t[1], t[2], 300, t[4], t[5])
        return t, t
    if s.kind in ('stop', 'fric', 'affricate'):
        t = OBSTRUENT_TARGETS[s.ph][:6]
        return t, t
    return None, None


def build_frames(segs):
    # per-frame list of (segment index, position 0..1 in segment)
    fl = []
    for i, s in enumerate(segs):
        for j in range(s.frames):
            fl.append((i, (j + 0.5) / s.frames))
    nf = len(fl)
    # segment start frames
    start = []
    c = 0
    for s in segs:
        start.append(c)
        c += s.frames
    tg = []
    for i, s in enumerate(segs):
        nxt = next((x for x in segs[i + 1:] if x.kind != 'pause'), None)
        tg.append(targets(s, nxt))

    def target_at(i, u):
        a, b = tg[i]
        if segs[i].kind == 'vowel' and len(VOWEL_TARGETS[segs[i].ph]) == 2:
            return lerp(a, b, u)
        return a

    # formant tracks with transitions: halfway "virtual locus" at each boundary (Klatt 1980 Sec. V.B),
    # linear over TRANS_MS on each side (capped at half the segment)
    track = []
    for f, (i, u) in enumerate(fl):
        s = segs[i]
        if tg[i][0] is None:
            track.append(None)
            continue
        val = target_at(i, u)
        t_ms = (f - start[i] + 0.5) * FRAME_MS
        dur_ms = s.frames * FRAME_MS
        cap = min(TRANS_MS, dur_ms / 2)
        # left boundary
        if i > 0 and tg[i - 1][0] is not None and segs[i - 1].frames > 0:
            b = lerp(target_at(i - 1, 1.0), target_at(i, 0.0), 0.5)
            if t_ms < cap:
                val = lerp(b, val, t_ms / cap)
        if i + 1 < len(segs) and tg[i + 1][0] is not None and segs[i + 1].frames > 0:
            b = lerp(target_at(i, 1.0), target_at(i + 1, 0.0), 0.5)
            d = dur_ms - t_ms
            if d < cap:
                val = lerp(b, val, d / cap)
        track.append(val)
    return fl, start, track


def f0_contour(segs, fl, start):
    """Pitch per frame: per sentence a linear fall F0_START -> F0_END, a rise at stressed vowel onsets
    decaying across the vowel, and a final fall (statement) or rise (question)."""
    nf = len(fl)
    # sentence spans: up to and including a . ? ! pause
    spans = []
    a = 0
    for i, s in enumerate(segs):
        if s.kind == 'pause' and s.ph in '.?!':
            spans.append((start[a], start[i] + s.frames, s.ph, a, i))
            a = i + 1
    if a < len(segs):
        spans.append((start[a], nf, '.', a, len(segs) - 1))
    f0 = [F0_END] * nf
    for (fa, fb, end, ia, ib) in spans:
        # voiced extent of the sentence (ignore trailing pause)
        last_sound = max([start[i] + segs[i].frames for i in range(ia, ib + 1) if segs[i].kind != 'pause'] or [fb])
        L = max(1, last_sound - fa)
        last_stress = max([i for i in range(ia, ib + 1) if segs[i].kind == 'vowel' and segs[i].stress == 1] or [ia])
        for f in range(fa, fb):
            x = min(1.0, (f - fa) / L)
            base = F0_START + (F0_END - F0_START) * x
            i, u = fl[f]
            s = segs[i]
            if s.kind == 'vowel' and s.stress:
                rise = F0_STRESS1 if s.stress == 1 else F0_STRESS2
                base *= 1 + rise * (1 - 0.6 * u)
            if i >= last_stress and segs[last_stress].kind == 'vowel':
                tail_a = start[last_stress]
                y = min(1.0, (f - tail_a) / max(1, last_sound - tail_a))
                goal = F0_QUESTION if end == '?' else F0_FINAL
                base = base + (goal - base) * y * (1.0 if end == '?' else 0.8)
            f0[f] = base
    return f0


def frame_filter(s, trk, prev_seg, next_seg):
    """Returns (voiced, ks, a, power) for one frame of segment s with transition formants trk."""
    F1, F2, F3, B1, B2, B3 = trk if trk is not None else (0,) * 6
    p = s.ph
    if s.kind in ('vowel', 'sonorant'):
        fb = [(F1, B1), (F2, B2), (F3, B3), (F4, B4), (F5, B5)]
        a = poly_from_formants(fb)
        return 1, step_down(a), a
    if s.kind == 'nasal':
        # all-pole murmur: the nasal pole replaces F1 (Klatt's nasal zero FNZ 450 sits on F1 480 and
        # cancels it); F2, F3 from the table, F4, F5 defaults
        fb = [(FNP, BNP), (F2, B2), (F3, B3), (F4, B4), (F5, B5)]
        a = poly_from_formants(fb)
        return 1, step_down(a), a
    if s.kind == 'aspirate':
        fb = [(F1, B1), (F2, B2), (F3, B3), (F4, B4), (F5, B5)]
        a = poly_from_formants(fb)
        return 0, step_down(a), a
    raise ValueError(s.kind)


def noise_filter(ph, back_vowel_next):
    """Frication / burst spectrum from Klatt's parallel amplitudes, fitted all-pole."""
    F1, F2, F3, B1, B2, B3, A2, A3, A4, A5, A6, AB = OBSTRUENT_TARGETS[ph]
    if ph in ('K', 'G') and back_vowel_next:
        A2 = 60       # Klatt 1980: velars before nonfront vowels, A2 about 60 dB
    amps = (A2, A3, A4, A5, A6, AB)
    ks, a = fit_spectrum(lambda f: parallel_power((F2, B2), (F3, B3), amps, f))
    return ks, a


def voiced_fric_filter(ph):
    """Voiced fricative: one excitation (pulses) through a fit of voicing (cascade with the table's
    formants, AV 47 dB) plus frication (parallel, AF 50 dB re 60)."""
    F1, F2, F3, B1, B2, B3, A2, A3, A4, A5, A6, AB = OBSTRUENT_TARGETS[ph]
    amps = (A2, A3, A4, A5, A6, AB)
    fb = [(F1, B1), (F2, B2), (F3, B3), (F4, B4), (F5, B5)]
    par_peak = max(parallel_power((F2, B2), (F3, B3), amps, f) for f in range(50, 4000, 25))
    cas_peak = max(cascade_power(fb, f) for f in range(50, 4000, 25))
    av, af = 10 ** ((47 - 60) / 10), 10 ** ((50 - 60) / 10)
    def pw(f):
        # cascade part wants the de-emphasis tilt, so divide out the pre-emphasis applied in the fit
        w = 2 * math.pi * f / RATE
        pre = 1 + PRE * PRE - 2 * PRE * math.cos(w)
        return (av * cascade_power(fb, f) / cas_peak * par_peak / pre
                + af * parallel_power((F2, B2), (F3, B3), amps, f))
    return fit_spectrum(pw)


def voicebar_filter(ph):
    F1, F2, F3, B1, B2, B3 = OBSTRUENT_TARGETS[ph][:6]
    a = poly_from_formants([(F1, B1), (F2, B2), (F3, B3), (F4, B4), (F5, B5)])
    return step_down(a), a


def db(x):
    return 10 ** (x / 10)


def make_frames(segs, fl, start, track, f0):
    out = []
    nf = len(fl)
    cache = {}
    for f in range(nf):
        i, u = fl[f]
        s = segs[i]
        prev = next((x for x in reversed(segs[:i]) if x.kind != 'pause'), None)
        nxt = next((x for x in segs[i + 1:] if x.kind != 'pause'), None)
        nxt_adj = segs[i + 1] if i + 1 < len(segs) else None
        P = max(20, min(160, int(round(RATE / f0[f]))))
        j = f - start[i]                      # frame index within the segment
        fr = {'v': 1, 'p': P, 'g': 0.0, 'k': None, 'a': None, 'pw': 0.0, 'seg': s.ph}
        if s.kind == 'pause':
            pass
        elif s.kind in ('vowel', 'sonorant', 'nasal', 'aspirate'):
            v, ks, a = frame_filter(s, track[f], prev, nxt)
            if s.kind == 'vowel':
                pw = POWER[s.ph] * db(UNSTRESSED_DB if s.stress == 0 else 0) * db(VOWEL_DECAY_DB * u)
            elif s.kind == 'sonorant':
                ref = nxt if (nxt_adj is not None and nxt_adj.kind == 'vowel') else prev
                ref = ref if ref is not None and ref.kind == 'vowel' else Seg('AX')
                pw = POWER[ref.ph] * db(SONORANT_DB)
            elif s.kind == 'aspirate':
                ref = nxt if nxt is not None and nxt.kind == 'vowel' else Seg('AX')
                pw = POWER[ref.ph] * db(ASPIRATION_DB)
            else:
                pw = POWER[s.ph]
            fr.update(v=v, k=ks, a=a, pw=pw)
        elif s.kind == 'fric':
            key = ('fric', s.ph)
            if key not in cache:
                cache[key] = voiced_fric_filter(s.ph) if s.ph in VD_FRIC else noise_filter(s.ph, False)
            ks, a = cache[key]
            fr.update(v=1 if s.ph in VD_FRIC else 0, k=ks, a=a, pw=POWER[s.ph])
        elif s.kind in ('stop', 'affricate'):
            n = s.frames
            back = nxt is not None and nxt.ph in BACK_VOWELS
            voiced = s.ph in ('B', 'D', 'G', 'JH')
            if s.kind == 'stop':
                closure = n - 1
                if j < closure:              # closure: silence, or a voice bar for b d g between voiced sounds
                    if voiced and prev is not None and prev.kind in ('vowel', 'sonorant', 'nasal'):
                        ks, a = voicebar_filter(s.ph)
                        fr.update(v=1, k=ks, a=a, pw=VOICEBAR_POWER)
                    else:
                        fr.update(v=1, g=0.0)
                else:                         # burst: one frame of frication noise (Klatt Table III)
                    key = ('burst', s.ph, back)
                    if key not in cache:
                        cache[key] = noise_filter(s.ph, back)
                    ks, a = cache[key]
                    # Sacia-Beck power is a mean over the whole sound; the burst carries it in one frame
                    inh = DUR[s.ph][0]
                    fr.update(v=0, k=ks, a=a, pw=POWER[s.ph] * inh / FRAME_MS)
            else:
                (c_inh, _), (f_inh, _) = DUR[s.ph]
                closure = max(1, int(round(n * c_inh / (c_inh + f_inh))))
                closure = min(closure, n - 1)
                if j < closure:
                    fr.update(v=1, g=0.0)
                else:
                    key = ('affr', s.ph)
                    if key not in cache:
                        cache[key] = voiced_fric_filter(s.ph) if voiced else noise_filter(s.ph, False)
                    ks, a = cache[key]
                    fr.update(v=1 if voiced else 0, k=ks, a=a, pw=POWER[s.ph])
        out.append(fr)
    # aspiration after p t k: the first frame of a following vowel or sonorant becomes aspiration noise
    for f in range(1, nf):
        i, _ = fl[f]
        ip, _ = fl[f - 1]
        if ip != i and segs[ip].ph in VL_STOPS and segs[i].kind in ('vowel', 'sonorant') and segs[i].frames > 1:
            t = track[f]
            if t is None:
                continue
            fb = [(t[0], 300), (t[1], t[4]), (t[2], t[5]), (F4, B4), (F5, B5)]
            a = poly_from_formants(fb)
            ref = segs[i] if segs[i].kind == 'vowel' else next((x for x in segs[i:] if x.kind == 'vowel'), Seg('AX'))
            out[f].update(v=0, k=step_down(a), a=a, pw=POWER[ref.ph] * db(ASPIRATION_DB))
    # silent frames: carry the neighbouring filter; a silence before a voiced onset is unvoiced so the
    # synthesizer does not fade the onset in
    for f in range(nf):
        if out[f]['k'] is None:
            src = next((out[g] for g in range(f - 1, -1, -1) if out[g]['k'] is not None), None) or \
                  next((out[g] for g in range(f + 1, nf) if out[g]['k'] is not None), None)
            out[f]['k'] = list(src['k']) if src else [0.0] * ORDER
            out[f]['a'] = src['a'] if src else [1.0] + [0.0] * ORDER
            out[f]['pw'] = 0.0
            if f + 1 < nf and out[f + 1]['pw'] > 0 and out[f + 1]['v']:
                out[f]['v'] = 0
    for fr in out:
        if not fr['v']:
            fr['p'] = 0
    return out


def set_gains(frames):
    """g so that output power (after de-emphasis) equals the phoneme power: g^2 * E = power."""
    for fr in frames:
        if fr['pw'] <= 0:
            fr['g'] = 0.0
            continue
        E = impulse_energy(fr['a'])
        fr['g'] = math.sqrt(fr['pw'] / E)
    # overall level: the loudest frame's output rms at 0.12 (the float synthesizer is then rescaled by
    # the decimal model's own headroom; this only keeps the float WAV from clipping)
    top = max(math.sqrt(fr['pw']) for fr in frames if fr['pw'] > 0)
    for fr in frames:
        fr['g'] *= 0.12 / top


def phon_to_frames(text, rate=1.0, info=None):
    toks = parse_phon(text)
    segs = build_segments(toks)
    assign_consonant_stress(segs)
    klatt_durations(segs, rate)
    # leading / trailing silence
    a = Seg('_'); a.kind = 'pause'; a.dur = START_PAD_MS
    b = Seg('_'); b.kind = 'pause'; b.dur = END_PAD_MS
    segs = [a] + segs + [b]
    frames_from_ms(segs)
    fl, start, track = build_frames(segs)
    f0 = f0_contour(segs, fl, start)
    frames = make_frames(segs, fl, start, track, f0)
    set_gains(frames)
    for fr in frames:
        assert all(abs(k) < 1 for k in fr['k']), fr
    if info is not None:
        info['segs'] = segs
        info['fl'] = fl
        info['track'] = track
        info['f0'] = f0
    return frames


if __name__ == '__main__':
    args = sys.argv[1:]
    rate = 1.0
    if '--rate' in args:
        k = args.index('--rate')
        rate = float(args[k + 1])
        del args[k:k + 2]
    info = {}
    frames = phon_to_frames(open(args[0]).read(), rate, info)
    write_frames(args[1], frames)
    segs = [s for s in info['segs'] if s.frames]
    print(' '.join('%s%s:%d' % (s.ph, s.stress if s.kind == 'vowel' else '', s.frames) for s in segs))
    nv = sum(f['v'] and f['g'] > 0 for f in frames)
    print('%s: %d frames (%.2f s), %d voiced sounding, max|k| %.3f' % (
        args[1], len(frames), len(frames) * FRAME_MS / 1000, nv, max(abs(k) for f in frames for k in f['k'])))
