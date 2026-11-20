"""Phonemes to frame cards in integer arithmetic: exactly what the CARDIAC programs in front/ do, pass by pass,
so each machine can be checked against its own function here.  It follows prototype/phonemes_to_frames.py rule
by rule; where the float front end needs cos, exp or a division it can't do, this one does the decimal thing
instead, and every such place is marked INTEGER.

The cards between the passes (each pass is one or more machines):

  tokens   a phoneme 10 x code + stress (codes 3-43, table.CODE), a word boundary -1, a pause -2 (,) -3 (.)
           -4 (?) -5 (!), the end -9.
  P1 (feat, forward)   one record of R1 cards a segment, the start pad first and the end pad last
  P2 (ahead, run on the records in reverse order)   adds what lies ahead of each segment
  P3 (dur, forward)    the consonants' stress and Klatt's duration rules, in ms, then frames (25 ms)
  P4 (sum)             one summary a sentence, for the pitch
  P5..P9 (frames)      frame by frame: the filters and glides, the pitch, the level, the silences
"""
import table as tb

FRAME_MS = 25
PAUSE_MS = {-2: 300, -3: 600, -4: 600, -5: 600}
START_PAD, END_PAD = 50, 150
K_VOWEL, K_SON, K_NASAL, K_STOP, K_FRIC, K_AFFR, K_ASP, K_PAUSE = 1, 2, 3, 4, 5, 6, 7, 8


def feat(pc):
    return FEATS[pc]


FEATS = {}
FILTERS = []
GLIDES = []


def load(C):
    """The phoneme table, the filters and the glide table for the scale C (the glide table read from
    front/glides.cards when C is the table's own, since it takes a while to make)."""
    global FEATS, FILTERS, GLIDES
    f, fl = tb.build(C)
    FEATS = {tb.CODE[p]: r for p, r in f.items()}
    FILTERS = fl
    path = tb.os.path.join(tb.os.path.dirname(tb.os.path.abspath(__file__)), '..', 'front', 'glides.cards')
    GLIDES = [int(v) for v in open(path).read().split()] if C == tb.C else tb.glide_table(fl)


def glide_factor(own, nb, w):
    """INTEGER: the level factor for a frame glided from its own filter towards a neighbour's, in percent, from
    the glide table (table.glide_table): the float front end works out every frame's gain from that frame's own
    filter, and blending the Ks of two filters makes one that speaks more quietly than either."""
    rec = 3 * len(FILTERS)
    return GLIDES[own * rec + 3 * nb + tb.GLIDE_W.index(w)]


def trunc_div(a, b):
    """a / b truncated toward zero, as SFT does it (b a power of ten)."""
    q = abs(a) // b
    return -q if a < 0 else q


def mulf(x, f):
    """x * f / 100 by Horner over f's three digits (f = 100a + 10b + c), truncating at each SFT 01: the
    CARDIAC's percent multiply.  x >= 0."""
    a, b, c = f // 100, (f // 10) % 10, f % 10
    t = c * x
    t //= 10
    t += b * x
    t //= 10
    t += a * x
    return t


def mul3(x, y):
    """x * y / 1000 by Horner over y's three digits, truncating at each SFT 01.  x, y >= 0."""
    a, b, c = y // 100, (y // 10) % 10, y % 10
    t = (c * x) // 10
    t = (t + b * x) // 10
    t = (t + a * x) // 10
    return t


def blend(x, y, u):
    """(x (10 - u) + y u) / 10, truncated toward zero: the glide between two coefficients, u in tenths."""
    return trunc_div(x * (10 - u) + y * u, 10)


# ---------------------------------------------------------------------------------------------------- P1
# record: pc kind stress wf pms send cls9 liq vls inh mn
R1 = 11


def p1(tokens):
    out = [[0, K_PAUSE, 0, 0, START_PAD, 0, 0, 0, 0, 0, 0]]
    wf = 1
    for t in tokens:
        if t == -9:
            break
        if t == -1:
            wf = 1
            continue
        if t < -1:
            send = 2 if t == -4 else 1 if t in (-3, -5) else 0
            out.append([0, K_PAUSE, 0, wf, PAUSE_MS[t], send, 0, 0, 0, 0, 0])
            wf = 1
            continue
        pc, s = t // 10, t % 10            # WH keeps its code; its row is W's
        r = feat(pc)
        out.append([pc, r[tb.F_KIND], s, wf, 0, 0, r[tb.F_CLS9], r[tb.F_LIQ], r[tb.F_VLS], r[tb.F_INH], r[tb.F_MN]])
        wf = 0
    out.append([0, K_PAUSE, 0, wf, END_PAD, 3, 0, 0, 0, 0, 0])     # the end pad ends the last span, as '.' does
    return out


# ---------------------------------------------------------------------------------------------------- P2
# run on the records last first.  Adds: after nextk imm nvs pfw p1 nxtpc adjv nextv ts te nts
R2 = R1 + 12


def p2(recs):
    out = []
    # what lies ahead, seen so far going backwards
    after = 0          # a vowel later in this word
    imm = 0            # the segment after is a stressed vowel of this word
    nvs = 0            # the next vowel in this word is stressed
    pfw = 0            # this word is followed by a pause
    nextk = 0          # the segment after: 0 pause/none, 1 vowel, 2 consonant
    run_cons = 0       # the consonant run after this point up to the next vowel of the word: first consonant
    run_obs = 0        # ... and its first obstruent's class
    nxtpc = 0          # the next segment that isn't a pause
    adjv = 0           # the segment after, if it is a vowel
    nextv = tb.CODE['AX']   # the next vowel anywhere ahead (AX if none)
    nts = 0            # the start filter of the segment after (0 for a pause)
    for r in reversed(recs):
        pc, kind, s, wf = r[0], r[1], r[2], r[3]
        if kind == K_PAUSE:
            out.append(r + [0, 0, 0, 0, 0, 0, nxtpc, adjv, nextv, 0, 0, nts])
            after = imm = nvs = 0
            pfw = 1
            nextk = 0
            run_cons = run_obs = 0
            adjv = 0
            nts = 0
            continue
        p1v = 0
        if kind == K_VOWEL:
            c = run_obs or run_cons
            p1v = c if c else (120 if not after else 100)
        # INTEGER: HH's filter is the aspirated form of the vowel after it (else AX's)
        f = feat(pc)
        if kind == K_ASP:
            v = nxtpc if nxtpc and feat(nxtpc)[tb.F_KIND] == K_VOWEL else tb.CODE['AX']
            ts = te = feat(v)[tb.F_ASP]
        else:
            ts, te = f[tb.F_TS], f[tb.F_TE]
        out.append(r + [after, nextk, imm, nvs, pfw, p1v, nxtpc, adjv, nextv, ts, te, nts])
        # now this segment is the one ahead
        if kind == K_VOWEL:
            imm = 1 if s else 0
            nvs = 1 if s else 0
            after = 1
            run_cons = run_obs = 0
            nextk = 1
            adjv = pc
            nextv = pc
        else:
            # consonant: its rule-9 class (a nasal counts as 85 only if it is unstressed: stressed when it is
            # right before a stressed vowel of the word, which imm says)
            cls = r[6]
            if kind == K_NASAL and imm:
                cls = 100
            run_cons = cls
            if kind in (K_STOP, K_FRIC, K_AFFR):
                run_obs = cls
            imm = 0
            nextk = 2
            adjv = 0
        nxtpc = pc
        nts = ts
        if wf:
            # the word starts here: what lies ahead of the segment before is in another word
            after = imm = nvs = 0
            run_cons = run_obs = 0
            pfw = 0
    out.reverse()
    return out


# ---------------------------------------------------------------------------------------------------- P3
# record out: pc kind s n send pte nts ts te nxtpc adjv prevv nextv pvls pnpk
R3 = 15


def p3(recs):
    out = []
    before = 0               # a vowel earlier in this word
    pkind, ppc, pvls, pte = 0, 0, 0, 0        # the segment before (kind 0: a pause or none)
    pnpk, pnpc = 0, 0        # the segment before that isn't a pause
    F, rem, done = 0, 0, 0   # time so far: whole frames and ms over; frames handed out
    for r in recs:
        pc, kind, s, wf, pms, send, cls9, liq, vls, inh, mn = r[:R1]
        after, nextk, imm, nvs, pfw, p1v, nxtpc, adjv, nextv, ts, te, nts = r[R1:]
        if kind == K_PAUSE:
            dur = pms
        else:
            if wf:
                before = 0
            syl = kind == K_VOWEL
            if not syl:
                s = 1 if (imm or (not before and nvs)) else 0
            fs = (not after) and (syl or before)
            pf_ = pfw and fs
            pr = 100
            if pf_:
                pr = mulf(pr, 140)                                    # rule 2
            if syl and not pf_:
                pr = mulf(pr, 60)                                     # rule 3
            if pf_ and not syl and liq:
                pr = mulf(pr, 140)
            if syl and not fs:
                pr = mulf(pr, 85)                                     # rule 4
            if syl and (before or after):
                pr = mulf(pr, 80)                                     # rule 5
            if not syl and not wf:
                pr = mulf(pr, 85)                                     # rule 6
            if s != 1:                                                # rule 7
                if s == 0:
                    mn = mn // 2
                if syl:
                    pr = mulf(pr, 50 if (before and after) else 70)
                elif kind == K_SON and nextk == 1:
                    pr = mulf(pr, 10)
                else:
                    pr = mulf(pr, 70)
            if syl:                                                   # rule 9
                p = p1v
                if not pf_:
                    p = 70 + (3 * p) // 10
                pr = mulf(pr, p)
            if syl:                                                   # rule 10
                if nextk == 1:
                    pr = mulf(pr, 120)
                if pkind == K_VOWEL:
                    pr = mulf(pr, 70)
            else:
                pc_ = pkind not in (0, K_VOWEL)
                nc_ = nextk == 2
                if pc_ and nc_:
                    pr = mulf(pr, 50)
                elif pc_ or nc_:
                    pr = mulf(pr, 70)
            assert 0 < pr <= 999, pr
            dur = mulf(inh - mn, pr) + mn
            if s >= 1 and kind in (K_VOWEL, K_SON) and pvls:          # rule 11
                dur += 25
        # frames: the running time rounded to frames, less those handed out (at least one for a sound, two for a
        # stop or an affricate)
        rem += dur
        while rem >= FRAME_MS:
            rem -= FRAME_MS
            F += 1
        rounded = F + (1 if rem >= 13 else 0)
        n = rounded - done
        least = 0 if kind == K_PAUSE else 2 if kind in (K_STOP, K_AFFR) else 1
        n = max(least, n)
        done += n
        prevv = pnpc if pnpk == K_VOWEL else 0
        out.append([pc, kind, s, n, send, pte, nts, ts, te, nxtpc, adjv, prevv, nextv, pvls, pnpk])
        if kind == K_PAUSE:
            pkind, ppc, pvls, pte = 0, 0, 0, 0
        else:
            if kind == K_VOWEL:
                before = 1
            pkind, ppc, pvls, pte = kind, pc, vls, te
            pnpk, pnpc = kind, pc
    return out


# ---------------------------------------------------------------------------------------------------- P4
# one summary a sentence: L, the tail's start (frames from the sentence's start, -1 for none), M, the end (1, 2)


def p4(recs):
    out = []
    f = 0
    fa = 0
    last_sound = None
    tail = None          # start frame of the last primary-stressed vowel
    first = True         # the next segment is the first of a sentence
    first_vowel = None
    for r in recs:
        pc, kind, s, n, send = r[:5]
        if first:
            first_vowel = f if kind == K_VOWEL else None
            first = False
        if kind == K_VOWEL and s == 1:
            tail = f
        if kind != K_PAUSE:
            last_sound = f + n
        f += n
        if send:
            out.append(summary(fa, f, last_sound, tail, first_vowel, 2 if send == 2 else 1))
            fa, last_sound, tail, first = f, None, None, True
    if not first:
        out.append(summary(fa, f, last_sound, tail, first_vowel, 1))
    return out


def summary(fa, fb, last_sound, tail, first_vowel, end):
    if last_sound is None:
        last_sound = fb
    L = max(1, last_sound - fa)
    if tail is None:
        tail = first_vowel
    if tail is None:
        return [L, -1, 1, end]
    return [L, tail - fa, max(1, last_sound - tail), end]


# ---------------------------------------------------------------------------------------------------- frames
RISE = {1: 15, 2: 7}         # percent rise at a stressed vowel's onset
GOAL = {1: 85, 2: 160}       # the end of a statement, of a question


def isqrt(x):
    """The CARDIAC's square root: count the odd numbers that can be taken away."""
    r, odd = 0, 1
    while x >= odd:
        x -= odd
        odd += 2
        r += 1
    return r


def period(f0):
    """round(8000 / f0) by taking f0 away from 8000 + f0 / 2 as often as it goes."""
    acc = 8000 + f0 // 2
    p = 0
    while acc >= f0:
        acc -= f0
        p += 1
    return p


def kvec(idx):
    return FILTERS[idx][:10]


def gain(idx):
    return FILTERS[idx][10]


def u10_of(j, n):
    return (10 * j + 5) // n


def glide_weight(j, n, side):
    """INTEGER: the share of a segment's own target in its first and last frames (the float front end's 40 ms
    linear glides from the halfway point, sampled at frame centres), in tenths; None for no glide."""
    k = j if side == 'left' else n - 1 - j
    if n >= 4:
        return {0: 3, 1: 9}.get(k)
    if n == 3:
        return 3 if k == 0 else None
    if n == 2:
        return 5 if k == 0 else None
    return None


def frames(recs, sums, info=None):
    """Frame cards (V, P, A, K10..K1 a frame, then -1) from P3's records and P4's summaries."""
    out = []                  # (sounding, V, P, A, K10..K1)
    f = 0
    si = 0
    fa = 0
    L = tailo = M = end = None
    q = qrem = 0               # Bresenham: drop = floor(30 (f - fa) / L)
    y = yrem = 0               # floor(100 (f - tail) / M)
    newsent = True
    pitch = []
    noise = []                 # each frame's noise filter (a fricative's, a burst's), else 0: for the high band
    for r in recs:
        pc, kind, s, n, send, pte, nts, ts, te, nxtpc, adjv, prevv, nextv, pvls, pnpk = r
        for j in range(n):
            if newsent:
                L, tailo, M, end = sums[si]
                si += 1
                fa = f
                q = qrem = 0
                y = yrem = 0
                newsent = False
            # ---- pitch
            base = 130 - q
            u = u10_of(j, n)
            if kind == K_VOWEL and s:
                r0 = mulf(base, RISE[s])
                base = base + r0 - (r0 * 6 * u) // 100
            if tailo >= 0 and f - fa >= tailo:
                delta = GOAL[end] - base
                t = delta * y
                if end == 1:
                    t = trunc_div(trunc_div(t, 10) * 8, 100)
                else:
                    t = trunc_div(t, 100)
                base += t
            P = period(base)
            assert 20 <= P <= 160, P
            pitch.append(base)
            # ---- filter and level
            sounding, V, K, G = 1, 1, None, 0
            nz = 0
            ft = feat(pc) if pc else None
            son_ref = None
            vowel_factors = False
            glides = False
            if kind == K_PAUSE:
                sounding = 0
            elif kind == K_VOWEL:
                if j == 0 and pvls and n > 1:
                    K, G, V = kvec(ft[tb.F_ASP]), gain(ft[tb.F_ASP]), 0
                else:
                    K = [blend(a, b, u) for a, b in zip(kvec(ts), kvec(te))]
                    G = blend(gain(ts), gain(te), u)
                    vowel_factors = glides = True
            elif kind == K_SON:
                if j == 0 and pvls and n > 1:
                    K, G, V = kvec(ft[tb.F_ASP]), gain(ft[tb.F_ASP]), 0
                    son_ref = nextv
                else:
                    K, G = kvec(ts), gain(ts)
                    son_ref = adjv or prevv or tb.CODE['AX']
                    glides = True
            elif kind == K_NASAL:
                K, G = kvec(ts), gain(ts)
                glides = True
            elif kind == K_ASP:
                K, G, V = kvec(ts), gain(ts), 0
                glides = True
            elif kind == K_FRIC:
                K, G, V = kvec(ft[tb.F_NOISE]), gain(ft[tb.F_NOISE]), ft[tb.F_VOICED]
                nz = ft[tb.F_NOISE]
            elif kind == K_STOP:
                if j < n - 1:
                    if ft[tb.F_VOICED] and pnpk in (K_VOWEL, K_SON, K_NASAL):
                        K, G = kvec(ft[tb.F_VBAR]), gain(ft[tb.F_VBAR])
                    else:
                        sounding = 0
                else:
                    idx = ft[tb.F_NOISE]
                    if ft[tb.F_ALT] and nxtpc and feat(nxtpc)[tb.F_BACK]:
                        idx = ft[tb.F_ALT]
                    K, G, V = kvec(idx), gain(idx), 0
                    nz = idx
            elif kind == K_AFFR:
                c = (n * ft[tb.F_CINH] + ft[tb.F_CTOT] // 2) // ft[tb.F_CTOT]
                c = min(max(1, c), n - 1)
                if j < c:
                    sounding = 0
                else:
                    K, G, V = kvec(ft[tb.F_NOISE]), gain(ft[tb.F_NOISE]), ft[tb.F_VOICED]
                    nz = ft[tb.F_NOISE]
            gl = None
            if glides:
                w = glide_weight(j, n, 'left')
                if w is not None and pte:
                    K = [blend(blend(a, b, 5), v, w) for a, b, v in zip(kvec(pte), kvec(ts), K)]
                    gl = (ts, pte, w)
                w = glide_weight(j, n, 'right')
                if w is not None and nts:
                    K = [blend(blend(a, b, 5), v, w) for a, b, v in zip(kvec(te), kvec(nts), K)]
                    gl = (te, nts, w)
            A = 0
            if sounding:
                A = G
                if son_ref is not None:
                    A = mul3(A, feat(son_ref)[tb.F_LOUD])
                if vowel_factors:
                    if s == 0:
                        A = mul3(A, 708)
                    A = A - mul3(A, 30 * u)
                if V:
                    A = mul3(A, 10 * isqrt(60 * P))
                if gl is not None:
                    A = min(999, mulf(A, glide_factor(*gl)))
                assert A <= 999, A
            out.append([sounding, V, P, A] + (K if K else [0] * 10))
            noise.append(nz)
            f += 1
            # move the declination and the tail on a frame (INTEGER: Bresenham, no division)
            if q < 30:
                qrem += 30
                while qrem >= L:
                    qrem -= L
                    q += 1
                q = min(q, 30)
            if tailo >= 0 and f - fa > tailo and y < 100:
                yrem += 100
                while yrem >= M:
                    yrem -= M
                    y += 1
                y = min(y, 100)
        if send:
            newsent = True
    # the silences: carry the frame before's filter; unvoiced (so not faded in) before a voiced sound
    cards = []
    prevK = [0] * 10
    for i, fr in enumerate(out):
        sounding, V, P, A = fr[:4]
        K = fr[4:]
        if not sounding:
            K = prevK
            nxt = out[i + 1] if i + 1 < len(out) else None
            V = 0 if (nxt is not None and nxt[0] and nxt[1]) else 1
            A = 0
        if not V:
            P = 0
        cards += [V, P, A] + K
        prevK = K
    if info is not None:
        info['pitch'] = pitch
        info['frames'] = out
        info['noise'] = noise
    return cards + [-1]


def phonemes_to_cards(tokens, info=None):
    r1 = p1(tokens)
    r2 = p2(r1)
    r3 = p3(r2)
    sums = p4(r3)
    if info is not None:
        info.update(r1=r1, r2=r2, r3=r3, sums=sums)
    return frames(r3, sums, info)


def tokens_of(phon):
    """text_to_phonemes.py's tokens as cards."""
    out = []
    for t in phon.split():
        t = t.lstrip('~')
        if t == '#':
            out.append(-1)
        elif t in (',', '.', '?', '!'):
            out.append({',': -2, '.': -3, '?': -4, '!': -5}[t])
        else:
            s = int(t[-1]) if t[-1].isdigit() else 0
            p = t[:-1] if t[-1].isdigit() else t
            out.append(10 * tb.CODE[p] + s)
    return out + [-9]
