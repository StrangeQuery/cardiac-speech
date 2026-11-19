"""The voice box's arithmetic in Python, built from the prototype's own functions (prototype/: closedloop.rmul,
closedloop.sto, synth_cardiac.reduce_k, closedloop.interp_steps, synth_float.excitation), so that the CARDIAC
programs in voice/ can be checked against the model they were written from, sample for sample.

It differs from the prototype's run_block in three places. A voiced pulse goes through the one-pole low-pass
e = pulse + 0.5 e (truncated), to soften the buzz. In a step whose A is 0 the lattice's products are truncated toward
zero instead of rounded, so that in a pause the lattice dies away instead of holding a small limit cycle. And in the
output stage 0.9 L is truncated instead of rounded whenever f is 0, so that yd dies away to 0 as well."""
import os
import sys
LPC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'prototype')
sys.path.insert(0, LPC)
import closedloop as cl          # noqa: E402
import synth_cardiac as sc       # noqa: E402
import synth_float as sf         # noqa: E402
from common import STEPS, STEP_LEN, ORDER   # noqa: E402

T_CELL = 86                      # the cell t in every lattice machine (voice/lattice*.cq)


def words(K, A=1):
    """The five coefficient cards for one K (k = K/1000) in a step whose amplitude is A, as REDUCE punches them: the
    sign word (ADD t or SUB t), the jumps into the row for the second and first digits, SFT 0L and the rounding half
    5 x 10^(L-1), or 0 when A is 0."""
    sign, digits = sc.reduce_k(K, 2, 'float')
    if not digits:
        lead, d1, d2 = 3, 0, 0
    else:
        lead = digits[0][0]
        d1 = digits[0][1]
        d2 = digits[1][1] if len(digits) > 1 else 0
        if len(digits) > 1:
            assert digits[1][0] == lead + 1
    return [(200 if sign > 0 else 700) + T_CELL, 899 - d2, 899 - d1, 400 + lead, 5 * 10 ** (lead - 1) if A else 0]


def lattice(exc, ks_per_step, amps=None):
    """The lattice alone: excitation values and a K vector (K1..K10) per 20-sample step in, f out (the prototype's
    run_block lattice, two digit terms), the products rounded, or truncated in a step whose amplitude in `amps` is 0."""
    b = [0] * (ORDER + 1)
    out = []
    n = 0
    for s, K in enumerate(ks_per_step):
        ks = [sc.reduce_k(k, 2, 'float') for k in K]
        rnd = amps is None or amps[s] != 0
        for _ in range(STEP_LEN):
            f = exc[n]; n += 1
            for i in range(ORDER, 0, -1):
                sg, dg = ks[i - 1]
                p = cl.sto(cl.rmul(sg, dg, b[i - 1], rnd))
                f = cl.sto(f - p)
                q = cl.sto(cl.rmul(sg, dg, f, rnd))
                b[i] = cl.sto(b[i - 1] + q)
            b[0] = f
            out.append(f)
    return out


def excitation(steps):
    """EXCITE's values, one a sample: the prototype's pulses and noise times the step's A, a voiced pulse then
    through e = pulse + 0.5 e (5 e, SFT 01: truncated; e is kept across steps and through unvoiced stretches)."""
    base = sf.excitation([(v, P, A, None) for (v, P, A, K) in steps], shape='pulse')
    out = []
    e = 0
    n = 0
    for (v, P, A, K) in steps:
        for _ in range(STEP_LEN):
            x = int(base[n]) * A; n += 1
            if v:
                e = x + 5 * e // 10
                x = e
            out.append(x)
    return out


def run(steps):
    """The lattice and the output stage on the interpolated steps: yd for each sample, the largest |value| the
    lattice holds (f and every b it keeps), and how many of its values wrapped past 999 (STO keeps three digits)."""
    exc = excitation(steps)
    b = [0] * (ORDER + 1)
    hi, lo, n, peak, wraps = 0, 0, 0, 0, 0
    out = []
    for (v, P, A, K) in steps:
        ks = [sc.reduce_k(k, 2, 'float') for k in K]
        rnd = A != 0
        for _ in range(STEP_LEN):
            f = exc[n]; n += 1
            for i in range(ORDER, 0, -1):
                sg, dg = ks[i - 1]
                p = cl.sto(cl.rmul(sg, dg, b[i - 1], rnd))
                wraps += abs(f - p) > 999
                f = cl.sto(f - p)
                q = cl.sto(cl.rmul(sg, dg, f, rnd))
                wraps += abs(b[i - 1] + q) > 999 and i < ORDER
                b[i] = cl.sto(b[i - 1] + q)
                peak = max(peak, abs(f), abs(b[i]) if i < ORDER else 0)
            b[0] = f
            yd = 900 * hi + cl.rmul(1, [(1, 9)], lo, f != 0) + f
            lo = cl.sto(yd)
            hi = -((-yd) // 1000) if yd < 0 else yd // 1000
            out.append(yd)
    return out, peak, wraps


def frame_cards(frames, headroom=0.4):
    """The prototype's integer frame cards for a .frames file (synth_cardiac.schedule_cards, pulse excitation, the
    scale S set as synth_cardiac.run sets it), as the voice box reads them: V, P, A, K10..K1 a frame, then -1."""
    sf.SHAPE = 'pulse'
    info = {}
    sf.synth(sf.schedule_float(frames), internal=info)
    S = min(headroom * 999 / info['lattice_max'], headroom * 9999 / info['out_max'])
    cards, _ = sc.schedule_cards(frames, S)
    deck = []
    for v, P, A, K in cards:
        deck += [v, P, A] + list(reversed(K))
    return deck + [-1]


def parse_cards(deck):
    """Frame cards back into (v, P, A, [K1..K10]) tuples."""
    out = []
    i = 0
    while deck[i] >= 0:
        v, P, A = deck[i:i + 3]
        out.append((v, P, A, list(reversed(deck[i + 3:i + 13]))))
        i += 13
    return out


def voice(deck):
    """The whole voice box: frame cards in, the output values out (thousands and units of 20 yd for each sample),
    and the largest |yd|, which must stay within the accumulator."""
    cards = parse_cards(deck)
    steps = cl.interp_steps(cards, 0, len(cards))
    yd, _, _ = run(steps)
    out = []
    for y in yd:
        assert -1638 <= y <= 1638, y
        Y = 20 * y
        out += [Y // 1000, Y % 1000]
    return out, max(abs(y) for y in yd)


def lattice_peak(deck):
    """The largest |value| the lattice holds (f and every b), the largest |yd| and the number of wraps, for the
    frame cards: what the scale has to keep within a cell and the accumulator."""
    cards = parse_cards(deck)
    yd, peak, wraps = run(cl.interp_steps(cards, 0, len(cards)))
    return peak, max(abs(y) for y in yd), wraps
