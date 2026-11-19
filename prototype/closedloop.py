#!/opt/homebrew/bin/python3
"""Closed-loop choice of the coefficient cards, with the decimal synthesizer in the loop
(the way lubdub's encoder picks each code by what the decoder will really produce).

For each frame in turn, and each K card in that frame, try a few nearby card values and keep
the one whose decimal output (after CARDIAC interpolation, digit-term reduction and decimal
arithmetic) is closest to the float reference on the same schedule.  The error is measured
over the previous frame and this one, since a card is the end point of one interpolation and
the start of the next.

usage: closedloop.py phrase terms [passes]
"""
import sys
from common import read_frames, write_wav, snr_db, STEPS, STEP_LEN, ORDER, PRE
import synth_float as sf
import synth_cardiac as sc


def rmul(sign, digits, x, rnd):
    """Same arithmetic as synth_cardiac.mul, without the counters."""
    if not digits:
        return 0
    terms = digits[::-1]
    acc = 0
    prev = terms[0][0]
    for idx, (p, d) in enumerate(terms):
        if idx:
            sh = prev - p
            acc = -((-acc) // 10 ** sh) if acc < 0 else acc // 10 ** sh
        acc += sign * d * x
        prev = p
    if rnd:
        h = 5 * 10 ** (prev - 1)
        acc += -h if acc < 0 else h
    return -((-acc) // 10 ** prev) if acc < 0 else acc // 10 ** prev


def sto(v):
    return -((-v) % 1000) if v < 0 else v % 1000


def interp_steps(cards, lo, hi):
    """CARDIAC interpolation for frames lo..hi-1 (same as synth_cardiac.schedule_cards)."""
    steps = []
    for i in range(lo, hi):
        v, P, A, K = cards[i]
        nv, nP, nA, nK = cards[i + 1] if i + 1 < len(cards) else cards[i]
        it = v == nv
        d = (lambda a, b: int((b - a) / 10) if it else 0)
        dP, dA, dK = d(P, nP), d(A, nA), [d(K[j], nK[j]) for j in range(ORDER)]
        cP, cA, cK = P, A, list(K)
        for s in range(STEPS):
            if s:
                cP += dP; cA += dA; cK = [cK[j] + dK[j] for j in range(ORDER)]
            steps.append((v, cP, cA, list(cK)))
    return steps


def run_block(state, steps, exc, n0, terms, mode, rnd):
    """Decimal synthesis of `steps` from `state` = (b list, hi, lo). Returns (out, state)."""
    b, hi, lo = list(state[0]), state[1], state[2]
    out = []
    n = n0
    for (v, P, A, K) in steps:
        ks = [sc.reduce_k(k, terms, mode) for k in K]
        for _ in range(STEP_LEN):
            sv = exc[n]; n += 1
            if sv in (1.0, -1.0, 0.0):
                f = int(sv) * A
            else:
                sg2, dg2 = sc.reduce_k(int(round(sv * 1000)), 3, 'float')
                f = sto(rmul(sg2, dg2, A, rnd))
            for i in range(ORDER, 0, -1):
                sg, dg = ks[i - 1]
                p = sto(rmul(sg, dg, b[i - 1], rnd))
                f = sto(f - p)
                q = sto(rmul(sg, dg, f, rnd))
                b[i] = sto(b[i - 1] + q)
            b[0] = f
            yd = 900 * hi + rmul(1, [(1, 9)], lo, rnd) + f
            lo = sto(yd)
            hi = -((-yd) // 1000) if yd < 0 else yd // 1000
            out.append(yd)
    return out, (b, hi, lo)


def err(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def closed_loop(frames, terms, mode='float', headroom=0.9, rnd=True, passes=1):
    sc.ROUND = rnd
    y0, info = sc.run(frames, terms, mode, headroom, 2)
    S = info['S']
    cards = [(v, P, A, list(K)) for (v, P, A, K) in info['cards']]
    steps_all = interp_steps(cards, 0, len(cards))
    exc = sf.excitation([(v, P, A, None) for (v, P, A, K) in steps_all])
    target = [v * S for v in sc.float_from_steps(steps_all, S)]     # float, full K, same schedule
    # check the fast core against the counted model
    chk, _ = run_block(([0] * (ORDER + 1), 0, 0), steps_all, exc, 0, terms, mode, rnd)
    assert all(abs(c / S - y) < 1e-9 for c, y in zip(chk, y0)), 'fast core differs from synth_cardiac'
    F = STEPS * STEP_LEN
    for ps in range(passes):
        state_at = [([0] * (ORDER + 1), 0, 0)]          # state at the start of each frame
        for f in range(len(cards)):
            lo = max(0, f - 1)
            st0 = state_at[lo]
            seg_t = target[lo * F:(f + 1) * F]
            def score():
                out, _ = run_block(st0, interp_steps(cards, lo, f + 1), exc, lo * F, terms, mode, rnd)
                return err(out, seg_t)
            best = score()
            for j in range(ORDER):
                K0 = cards[f][3][j]
                m = abs(K0)
                lead = 1 if (mode == 'fixed' or m >= 100) else 2 if m >= 10 else 3
                q = 10 ** (3 - min(3, lead + terms - 1))     # one reduction step at this size
                for c in (K0 + q, K0 - q, K0 + q // 2, K0 - q // 2):
                    if c == K0 or abs(c) > 999:
                        continue
                    cards[f][3][j] = c
                    s2 = score()
                    if s2 < best:
                        best, K0 = s2, c
                    cards[f][3][j] = K0
            if f >= 1:     # frame f-1 is now final: advance the saved state past it
                _, st = run_block(st0, interp_steps(cards, lo, lo + 1), exc, lo * F, terms, mode, rnd)
                state_at.append(st)
    steps_all = interp_steps(cards, 0, len(cards))
    out, _ = run_block(([0] * (ORDER + 1), 0, 0), steps_all, exc, 0, terms, mode, rnd)
    return [v / S for v in out], [v / S for v in target], y0, S


if __name__ == '__main__':
    ph, terms = sys.argv[1], int(sys.argv[2])
    passes = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    sf.SHAPE = 'chirp'
    frames = read_frames('out/%s.frames' % ph)
    y, target, y0, S = closed_loop(frames, terms, passes=passes)
    write_wav('out/%s_dec_t%d_closedloop.wav' % (ph, terms), y)
    print('%s t%d: open-loop SNR %.1f dB, closed-loop SNR %.1f dB (vs float, same schedule)' % (
        ph, terms, snr_db(target, y0), snr_db(target, y)))
