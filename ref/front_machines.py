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
