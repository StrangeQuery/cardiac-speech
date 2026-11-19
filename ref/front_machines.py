"""The front end machine by machine: each function takes the cards a machine reads and gives the cards it
punches, in the machine's own record layouts, using front_ref's arithmetic.  compose() runs them in order and
must give front_ref.phonemes_to_cards's frame cards exactly."""
import front_ref as fr
import table as tb

FEATURES = [int(v) for v in open(tb.os.path.join(tb.os.path.dirname(tb.os.path.abspath(__file__)), '..', 'front',
                                                 'features.cards')).read().split()]
FILTERS = [int(v) for v in open(tb.os.path.join(tb.os.path.dirname(tb.os.path.abspath(__file__)), '..', 'front',
                                                'filters.cards')).read().split()]


def records(cards, size):
    assert len(cards) % size == 0, (len(cards), size)
    return [cards[i:i + size] for i in range(0, len(cards), size)]


def flat(recs):
    return [c for r in recs for c in r]


def reverse(cards, size):
    """The host's one piece of sorting: a deck of records put in the opposite order."""
    return flat(list(reversed(records(cards, size))))


# feat (P1): pc s wf pms send kind inh mn cls9 liq vls
R1 = 11


def f1(tokens):
    out = []
    for r in fr.p1(tokens):
        pc, kind, s, wf, pms, send, cls9, liq, vls, inh, mn = r
        out += [pc, s, wf, pms, send, kind, inh, mn, cls9, liq, vls]
    return out


def select(recs, fields):
    """The host deals a machine only some cards (columns) of each record."""
    return [[r[i] for i in fields] for r in recs]


# R1 columns
PC, S, WF, PMS, SEND, KIND, INH, MN, CLS9, LIQ, VLS = range(11)
AX = tb.CODE['AX']


def f2a(recs):
    """after.cq: (kind, s, wf) last first -> (after, imm, nvs)."""
    after = imm = nvs = 0
    out = []
    for kind, s, wf in recs:
        out.append([after, imm, nvs])
        if kind == 8:
            after = imm = nvs = 0
            continue
        if kind == 1:
            imm = nvs = s
            after = 1
        else:
            imm = 0
        if wf:
            after = imm = nvs = 0
    return out


def f2b(recs):
    """ahead.cq: (kind, wf, cls9, after, imm) last first -> (nextk, pfw, p1)."""
    nextk = pfw = runc = runo = 0
    out = []
    for kind, wf, cls, after, imm in recs:
        p1 = 0
        if kind == 1:
            c = runo or runc
            p1 = c if c else 120 - 20 * after
        out.append([nextk, pfw, p1])
        if kind == 8:
            nextk, pfw, runc, runo = 0, 1, 0, 0
            continue
        if kind == 1:
            runc = runo = 0
            nextk = 1
        else:
            if kind == 3 and imm:
                cls = 100
            runc = cls
            if 4 <= kind <= 6:
                runo = cls
            nextk = 2
        if wf:
            runc = runo = pfw = 0
    return out


def f2c(recs):
    """next.cq: (pc, kind) last first -> (nxtpc, adjv, nextv, ts, te, nts)."""
    nxtpc = adjv = nts = nxtv = 0
    nextv = AX
    out = []
    for pc, kind in recs:
        if kind == 8:
            out.append([nxtpc, adjv, nextv, 0, 0, nts])
            adjv = nts = 0
            continue
        q = pc
        if kind == 7:
            q = nxtpc if nxtv else AX
        row = FEATURES[q * tb.FEAT:(q + 1) * tb.FEAT]
        ts, te, asp = row[tb.F_TS], row[tb.F_TE], row[tb.F_ASP]
        if kind == 7:
            ts = te = asp
        out.append([nxtpc, adjv, nextv, ts, te, nts])
        nxtpc, nts = pc, ts
        if kind == 1:
            nxtv, adjv, nextv = 1, pc, pc
        else:
            nxtv = adjv = 0
    return out


# ------------------------------------------------------------------ forward again: stress, durations, frames
def f3_stress(recs):
    """stress.cq: (kind, s, wf, after, imm, nvs, pfw) -> (s', fs, pf, bef).  A consonant is stressed when a
    stressed vowel of its word comes right after it, or when it is before the word's first vowel and that vowel is
    stressed.  fs: in the word's last syllable; pf: and the word comes right before a pause; bef: a vowel came
    earlier in this word."""
    bef = 0
    out = []
    for kind, s, wf, after, imm, nvs, pfw in recs:
        if kind == 8:
            out.append([0, 0, 0, bef])
            continue
        if wf:
            bef = 0
        syl = kind == 1
        if not syl:
            s = 1 if (imm or (not bef and nvs)) else 0
        fs = 1 if (not after and (syl or bef)) else 0
        pf = 1 if (pfw and fs) else 0
        out.append([s, fs, pf, bef])
        if syl:
            bef = 1
    return out


def f3_base(recs):
    """base.cq: (kind, inh, mn, pms, vls, s') -> (x, base): dur = x pr / 100 + base.  An unstressed segment's
    MINDUR is halved (rule 7); a stressed vowel or sonorant after P T K gets 25 ms more (rule 11); a pause is its
    own length."""
    pvls = 0
    out = []
    for kind, inh, mn, pms, vls, s in recs:
        if kind == 8:
            out.append([0, pms])
            pvls = 0
            continue
        if s == 0:
            mn = fr.trunc_div(5 * mn, 10)
        base = mn + (25 if (s >= 1 and kind <= 2 and pvls) else 0)
        out.append([inh - mn, base])
        pvls = vls
    return out


def f3_rules2(recs):
    """rules2.cq: (kind, wf, liq, after, fs, pf, bef, s', nextk) -> Klatt's rules 2 to 7 as factors, then 0."""
    out = []
    for kind, wf, liq, after, fs, pf, bef, s, nextk in recs:
        if kind != 8:
            syl = kind == 1
            if pf: out.append(140)
            if syl and not pf: out.append(60)
            if pf and not syl and liq: out.append(140)
            if syl and not fs: out.append(85)
            if syl and (bef or after): out.append(80)
            if not syl and not wf: out.append(85)
            if s != 1:
                if syl:
                    out.append(50 if (bef and after) else 70)
                elif kind == 2 and nextk == 1:
                    out.append(10)
                else:
                    out.append(70)
        out.append(0)
    return out


def f3_rules9(recs):
    """rules9.cq: (kind, nextk, p1, pf) -> Klatt's rules 9 and 10 as factors, then 0."""
    out = []
    pkind = 0
    for kind, nextk, p1, pf in recs:
        if kind == 8:
            out.append(0)
            pkind = 0
            continue
        if kind == 1:
            out.append(p1 if pf else 70 + (3 * p1) // 10)
            if nextk == 1: out.append(120)
            if pkind == 1: out.append(70)
        else:
            pc_ = pkind not in (0, 1)
            nc_ = nextk == 2
            if pc_ and nc_: out.append(50)
            elif pc_ or nc_: out.append(70)
        out.append(0)
        pkind = kind
    return out


def f3_mul(xb, fa, fb):
    """mul.cq: (x, base) and two lists of factors -> dur = x pr / 100 + base, pr = 100 times the factors."""
    out = []
    ia = ib = 0
    for x, base in xb:
        pr = 100
        while fa[ia]:
            pr = fr.mulf(pr, fa[ia]); ia += 1
        ia += 1
        while fb[ib]:
            pr = fr.mulf(pr, fb[ib]); ib += 1
        ib += 1
        assert 0 <= pr <= 999
        out.append([fr.mulf(x, pr) + base])
    return out


def f3_frames(recs):
    """frames.cq: (kind, dur) -> n: the running time in 25 ms frames, rounded, less the frames handed out; at
    least one for a sound, two for a stop or affricate."""
    F = rem = done = 0
    out = []
    for kind, dur in recs:
        rem += dur
        while rem >= 25:
            rem -= 25
            F += 1
        n = F + (1 if rem >= 13 else 0) - done
        least = 0 if kind == 8 else 2 if kind in (4, 6) else 1
        n = max(least, n)
        done += n
        out.append([n])
    return out


def f3_back(recs):
    """back.cq: (pc, kind, vls, te) -> (pte, prevv, pvls, pnpk): the segment before (its end filter, whether it is
    P T K), the segment before that isn't a pause (its kind, and its pc if a vowel)."""
    pte = pvls = pnpk = pnpc = 0
    out = []
    for pc, kind, vls, te in recs:
        out.append([pte, pnpc if pnpk == 1 else 0, pvls, pnpk])
        if kind == 8:
            pte = pvls = 0
        else:
            pte, pvls, pnpk, pnpc = te, vls, kind, pc
    return out


def front_decks(tokens):
    """Every deck of the front end up to the frames, by machine, as the host deals them."""
    r1 = records(f1(tokens), R1)
    rev = list(reversed(r1))
    a = list(reversed(f2a(select(rev, [KIND, S, WF]))))
    b = list(reversed(f2b([x + y[:2] for x, y in zip(select(rev, [KIND, WF, CLS9]), list(reversed(a)))])))
    c = list(reversed(f2c(select(rev, [PC, KIND]))))
    st = f3_stress([x + y + z[1:2] for x, y, z in zip(select(r1, [KIND, S, WF]), a, b)])
    bs = f3_base([x + y[:1] for x, y in zip(select(r1, [KIND, INH, MN, PMS, VLS]), st)])
    fa = f3_rules2([x + y[:1] + z[1:] + z[:1] + w[:1] for x, y, z, w in zip(select(r1, [KIND, WF, LIQ]), a, st, b)])
    fb = f3_rules9([x + y[:1] + y[2:3] + z[2:3] for x, y, z in zip(select(r1, [KIND]), b, st)])
    du = f3_mul(bs, fa, fb)
    n = f3_frames([x + y for x, y in zip(select(r1, [KIND]), du)])
    bk = f3_back([x + y[4:5] for x, y in zip(select(r1, [PC, KIND, VLS]), c)])
    return dict(r1=r1, a=a, b=b, c=c, st=st, bs=bs, fa=fa, fb=fb, du=du, n=n, bk=bk)


def r3_of(d):
    """front_ref's P3 records from the decks: pc kind s n send pte nts ts te nxtpc adjv prevv nextv pvls pnpk."""
    out = []
    for r, c, st, n, bk in zip(d['r1'], d['c'], d['st'], d['n'], d['bk']):
        nxtpc, adjv, nextv, ts, te, nts = c
        pte, prevv, pvls, pnpk = bk
        out.append([r[PC], r[KIND], st[0], n[0], r[SEND], pte, nts, ts, te, nxtpc, adjv, prevv, nextv, pvls, pnpk])
    return out


def f4_sum(recs):
    """sum.cq: (kind, send, s, n) -> a summary for each sentence: L, the tail's start, M, the end (1, 2)."""
    out = []
    f, fv, tail, ls = 0, -1, -1, -1
    for kind, send, s, n in recs:
        if f == 0:
            fv = 0 if kind == 1 else -1
        if kind == 1 and s == 1:
            tail = f
        if kind != 8:
            ls = f + n
        f += n
        if send:
            if ls < 0:
                ls = f
            if tail < 0:
                tail = fv
            out.append([ls, tail, ls - tail if tail >= 0 else 1, 2 if send == 2 else 1])
            f, ls, tail = 0, -1, -1
    return out


# ------------------------------------------------------------------ the frames
def weight(k, n):
    if n >= 4:
        return {0: 3, 1: 9}.get(k, 0)
    if n == 3:
        return 3 if k == 0 else 0
    if n == 2:
        return 5 if k == 0 else 0
    return 0


def f5_framer(segs):
    """framer.cq: a segment's (n, send) -> for each frame (j, u, wl, wr, end) to the chooser, and u to the pitch
    and the level.  u = (10 j + 5) / n, the frame's place in the segment in tenths; wl and wr the glide weights at
    the segment's two ends (0 for none); end 1 for the very last frame (of the pause that ends everything)."""
    out, us = [], []
    for n, send in segs:
        for j in range(n):
            u = (10 * j + 5) // n
            out.append([j, u, weight(j, n), weight(n - 1 - j, n), 1 if (send == 3 and j == n - 1) else 0])
            us.append(u)
    return out, us


def row(pc):
    return FEATURES[pc * tb.FEAT:(pc + 1) * tb.FEAT]


def f5_closure(recs):
    """closure.cq: (pc, kind, n) and the table's CINH CTOT -> c, the frames of the segment that are its closure:
    all of a pause, all but the last of a stop, and of an affricate (n CINH + CTOT / 2) / CTOT of them, at least one
    and not all; none otherwise."""
    out = []
    for pc, kind, n in recs:
        c = 0
        if kind == 8:
            c = n
        elif kind == 4:
            c = n - 1
        elif kind == 6:
            r = row(pc)
            cinh, ctot = r[tb.F_CINH], r[tb.F_CTOT]
            rem, c = (5 * ctot) // 10, 0
            for _ in range(n):
                rem += cinh
                while rem >= ctot:
                    rem -= ctot
                    c += 1
            c = min(max(1, c), n - 1)
        out.append([c])
    return out


def f5_main(recs):
    """main.cq: (pc, kind, ts, te, nxtpc) and the table's VOICED NOISE ALT (and a stop's next vowel's BACK) -> the
    filters of the segment's sounding frames: ma mb (gliding from ma to mb by u if uon), vm (voiced), gl (glides
    at the ends)."""
    out = []
    for pc, kind, ts, te, nxtpc in recs:
        r = row(pc)
        ma = mb = uon = gl = 0
        vm = 1
        if kind in (1, 2, 3, 7):
            ma, mb, gl = ts, te, 1
            uon = 1 if kind == 1 else 0
            vm = 0 if kind == 7 else 1
        elif kind in (4, 5, 6):
            ma = mb = r[tb.F_NOISE]
            vm = r[tb.F_VOICED] if kind != 4 else 0
            if kind == 4 and r[tb.F_ALT] and row(nxtpc)[tb.F_BACK]:
                ma = mb = r[tb.F_ALT]
        out.append([ma, mb, uon, vm, gl])
    return out


def f5_edge(recs):
    """edge.cq: (pc, kind, n, pvls, pnpk) and the table's ASP VOICED VBAR -> cf (a stop's closure: its voice bar
    when it is voiced and a vowel, sonorant or nasal came before, else 0 for silence) and af (the aspirated filter for
    a vowel's or sonorant's first frame right after P T K, when it has more than one frame; else 0)."""
    out = []
    for pc, kind, n, pvls, pnpk in recs:
        r = row(pc)
        cf = af = 0
        if kind == 4 and r[tb.F_VOICED] and pnpk in (1, 2, 3):
            cf = r[tb.F_VBAR]
        if kind in (1, 2) and pvls and n > 1:
            af = r[tb.F_ASP]
        out.append([cf, af])
    return out


def f5_cframe(segs, frames):
    """cframe.cq: per segment (n, c, ma, mb, uon, vm, gl, cf, af, pte, nts), per frame (j, u, wl, wr, end) ->
    to the glide machine (a, b, u, gn, go, w) and to the level (snd, V): snd 1 sounding, 0 silent, 9 the very last
    frame."""
    ko, lo = [], []
    fi = 0
    for n, c, ma, mb, uon, vm, gl, cf, af, pte, nts in segs:
        for _ in range(n):
            j, u, wl, wr, end = frames[fi]; fi += 1
            g = 0
            if j < c:
                a = b = cf
                uu, V = 0, 1
                snd = 1 if cf else (9 if end else 0)
            elif j == 0 and af:
                a = b = af
                uu, V, snd = 0, 0, 1
            else:
                a, b = ma, mb
                uu = u if uon else 0
                V, snd, g = vm, 1, gl
            gn, go, w = a, a, 10
            if g:
                if wl and pte:
                    gn, go, w = pte, a, wl
                elif wr and nts:
                    gn, go, w = nts, b, wr
            ko.append([a, b, uu, gn, go, w])
            lo.append([snd, V])
    return ko, lo


def frec(i):
    return FILTERS[i * 11:(i + 1) * 11]


def f6_glide(ks):
    """glide.cq: (a, b, u, gn, go, w) -> K10..K1 to the assembler and G to the level.  K = (Ka (10-u) + Kb u) / 10,
    then K = (m (10-w) + K w) / 10 with m = (Kgn + Kgo) / 2; G = (Ga (10-u) + Gb u) / 10."""
    ko, go_ = [], []
    for a, b, u, gn, go, w in ks:
        A, B, N, O = frec(a), frec(b), frec(gn), frec(go)
        K = [fr.blend(x, y, u) for x, y in zip(A[:10], B[:10])]
        G = fr.blend(A[10], B[10], u)
        K = [fr.blend(fr.blend(x, y, 5), k, w) for x, y, k in zip(N[:10], O[:10], K)]
        ko.append(K)
        go_.append(G)
    return ko, go_


def f7_base(segs, us, sums):
    """pitch1.cq: per segment (kind, s, n, send), per frame u, per sentence its summary -> per frame the pitch
    before the fall to the end: 130 Hz less the declination (30 Hz over the sentence, Bresenham: q = 30 f / L), and
    a stressed vowel's rise (15 or 7 percent of that at its onset, falling to 40 percent of it at its end)."""
    out = []
    fi = si = 0
    ns = True
    for kind, s, n, send in segs:
        for _ in range(n):
            if ns:
                L = sums[si][0]; si += 1
                q = qrem = 0
                ns = False
            u = us[fi]; fi += 1
            base = 130 - q
            if kind == 1 and s:
                r0 = fr.mulf(base, fr.RISE[s])
                base = base + r0 - (r0 * u * 6) // 100
            out.append(base)
            if q < 30:
                qrem += 30
                while qrem >= L:
                    qrem -= L
                    q += 1
                q = min(q, 30)
        if send:
            ns = True
    return out


def f7_tail(segs, bases, sums):
    """pitch2.cq: per segment (n, send), per frame the pitch so far, per sentence its summary -> per frame f0: from
    the tail's start on, the pitch moves toward 85 Hz (a statement, by 0.8 of the way) or 160 Hz (a question):
    y = 100 (f - tail) / M by Bresenham, f0 = base + (goal - base) y / 100."""
    out = []
    fi = si = 0
    ns = True
    for n, send in segs:
        for _ in range(n):
            if ns:
                L, tailo, M, end = sums[si]; si += 1
                f = y = yrem = 0
                ns = False
            base = bases[fi]; fi += 1
            if tailo >= 0 and f >= tailo:
                delta = fr.GOAL[end] - base
                t = delta * y
                t = fr.trunc_div(fr.trunc_div(t, 10) * 8, 100) if end == 1 else fr.trunc_div(t, 100)
                base += t
            out.append(base)
            f += 1
            if tailo >= 0 and f > tailo and y < 100:
                yrem += 100
                while yrem >= M:
                    yrem -= M
                    y += 1
                y = min(y, 100)
        if send:
            ns = True
    return out


def f7_period(f0s):
    """period.cq: f0 in Hz -> the pitch period P = (8000 + f0 / 2) / f0 samples."""
    return [fr.period(f) for f in f0s]


def f8_level(segs, sv, us, gs, ps):
    """level.cq: per segment (kind, s, n, adjv, prevv, nextv), per frame (snd, V), u, G and P, and the table's LOUD
    card of a sonorant's reference vowel -> per frame (snd, V, A)."""
    out = []
    fi = 0
    for kind, s, n, adjv, prevv, nextv in segs:
        for _ in range(n):
            snd, V = sv[fi]; u = us[fi]; G = gs[fi]; P = ps[fi]; fi += 1
            A = 0
            if snd == 1:
                A = G
                if kind == 2:
                    ref = (adjv or prevv or AX) if V else nextv
                    A = fr.mul3(A, FEATURES[ref * tb.FEAT + tb.F_LOUD])
                if kind == 1 and V:
                    if s == 0:
                        A = fr.mul3(A, 708)
                    A = A - fr.mul3(A, 30 * u)
                if V:
                    A = fr.mul3(A, 10 * fr.isqrt(60 * P))
            out.append([snd, V, A])
    return out


def f9_asm(lv, ps, ks):
    """asm.cq: per frame (snd, V, A), P and K10..K1 -> the frame cards for the voice box, then -1.  A silent frame
    keeps the filter of the frame before (zeros at the start), and is unvoiced when a voiced sound comes right after
    it (so the sound isn't faded in), else voiced; an unvoiced frame's P is 0."""
    cards = []
    pend = None
    prevK = [0] * 10
    for (snd, V, A), P, K in zip(lv, ps, ks):
        if snd != 1:
            K = prevK
        if pend is not None:
            ps_, pv, pp, pa, pk = pend
            if ps_ != 1:
                pv = 0 if (snd == 1 and V == 1) else 1
            cards += [pv, pp if pv else 0, pa] + pk
        pend = (snd, V, P, A, K)
        prevK = K
        if snd == 9:
            ps_, pv, pp, pa, pk = pend
            cards += [1, pp, 0] + pk
            break
    return cards + [-1]


def compose(tokens):
    """The front end machine by machine: the frame cards."""
    d = front_decks(tokens)
    r1 = d['r1']
    fl, us = f5_framer([n + x for n, x in zip(d['n'], select(r1, [SEND]))])
    cl = f5_closure([x + n for x, n in zip(select(r1, [PC, KIND]), d['n'])])
    mn = f5_main([x + c[3:5] + c[0:1] for x, c in zip(select(r1, [PC, KIND]), d['c'])])
    ed = f5_edge([x + n + bk[2:4] for x, n, bk in zip(select(r1, [PC, KIND]), d['n'], d['bk'])])
    segs = [n + c + m + e + bk[:1] + cc[5:6] for n, c, m, e, bk, cc in zip(d['n'], cl, mn, ed, d['bk'], d['c'])]
    ko, lv = f5_cframe(segs, fl)
    ks, gs = f6_glide(ko)
    sums = f4_sum([x + y[:1] + z for x, y, z in zip(select(r1, [KIND, SEND]), d['st'], d['n'])])
    bases = f7_base([x[:1] + y[:1] + n + x[1:2] for x, y, n in zip(select(r1, [KIND, SEND]), d['st'], d['n'])], us, sums)
    f0s = f7_tail([n + x for x, n in zip(select(r1, [SEND]), d['n'])], bases, sums)
    ps = f7_period(f0s)
    lev = f8_level([x[:1] + y[:1] + n + c[1:2] + bk[1:2] + c[2:3] for x, y, n, c, bk in
                    zip(select(r1, [KIND]), d['st'], d['n'], d['c'], d['bk'])], lv, us, gs, ps)
    cards = f9_asm(lev, ps, ks)
    d.update(fl=fl, us=us, cl=cl, mn=mn, ed=ed, segs=segs, ko=ko, lv=lv, ks=ks, gs=gs, sums=sums, bases=bases, f0s=f0s, ps=ps, lev=lev)
    return cards, d


def f8_chain(segs, sv, us, gs, ps):
    """The level as machines: lsel, mulx, vsel, mulx, mulx, psel, mulx.  Returns each stage's cards."""
    ls, vs, pss = [], [], []
    fi = 0
    for kind, s, n, adjv, prevv, nextv in segs:
        for _ in range(n):
            snd, V = sv[fi]; u = us[fi]; P = ps[fi]; fi += 1
            if snd != 1:
                ls.append([3, 0])
            elif kind == 2:
                ref = (adjv or prevv or AX) if V else nextv
                ls.append([1, FEATURES[ref * tb.FEAT + tb.F_LOUD]])
            else:
                ls.append([0, 0])
            if kind == 1 and snd == 1 and V:
                vs.append([1 if s == 0 else 0, 708, 2, 30 * u])
            else:
                vs.append([0, 708, 0, 0])
            pss.append([1, 10 * fr.isqrt(60 * P)] if (snd == 1 and V) else [0, 0])

    def mulx(frames, modes):
        out = []
        for (snd, V, A), (m, y) in zip(frames, modes):
            if m == 1: A = fr.mul3(A, y)
            elif m == 2: A = A - fr.mul3(A, y)
            elif m == 3: A = 0
            out.append([snd, V, A])
        return out
    m1 = mulx([x + [g] for x, g in zip(sv, gs)], ls)
    m2 = mulx(m1, [v[:2] for v in vs])
    m3 = mulx(m2, [v[2:] for v in vs])
    m4 = mulx(m3, pss)
    return dict(ls=ls, vs=vs, pss=pss, m1=m1, m2=m2, m3=m3, m4=m4)


def f9_kcarry(sv, ks):
    out = []
    prev = [0] * 10
    for (snd, V), K in zip(sv, ks):
        if snd != 1:
            K = prev
        out.append(K)
        prev = K
    return out
