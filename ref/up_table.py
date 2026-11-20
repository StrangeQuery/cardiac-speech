"""The upsampler's two filters, designed once in floating point and written as cards, in thousandths, for the third
version (upsample/). They are worked out ahead of time, as the phoneme table is (ref/table.py): designing a filter
needs cosines and the solution of a set of linear equations, and none of it depends on the text.

Stage 1 takes 8 kHz to 16 kHz. Its filter is the one that has to be sharp: 159 taps at 16 kHz, a least-squares
low-pass with gain 2 that passes 0 to 3,820 Hz and stops 4,000 to 8,000 Hz (the stopband weighted 100 times the
passband), with each of its two phases made to sum to exactly 1. It is cut into two phases, of 80 taps (the even
ones) and 79 (the odd ones, among them the centre). The stopband starts at 4 kHz itself because the speech has much
of its energy just below it (its fricatives), and an image of what is at f lands at 8 kHz - f.

Stage 2 takes 16 kHz to 48 kHz. What it has to remove are the images of 0 to 4 kHz around 16 kHz, so it can be
short: 19 taps at 48 kHz, a sinc with its cutoff at 8 kHz under a Kaiser window, with gain 3. A sinc cut at a third
of the band is zero at every third tap from its centre, so of its three phases one is the centre tap alone, 1, and
the 48 kHz sample there is the 16 kHz sample itself; the other two phases have six taps each.

In thousandths, each phase of each stage sums to exactly 1000 (`thousandths`), so that a constant or slowly
changing signal comes out of every phase the same, and leaves no image at the multiples of the rate the stage
takes in (8 kHz for stage 1, 16 and 32 kHz for stage 2).

Each table is a deck of cards: the stage (1 or 2), then two cards a tap, phase by phase and in each phase the tap
for the newest sample first: the coefficient in thousandths, and 1 if it is the phase's last tap, else 0. The phase
that is the sample itself is the two cards 0 and 2.

    python3 up_table.py          # writes upsample/tables/fir1.cards and fir2.cards, and prints the responses"""
import cmath
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = os.path.join(HERE, '..', 'upsample', 'tables')

N1, FP1, FS1, W1 = 159, 3820.0, 4000.0, 100.0    # stage 1, at 16 kHz
N2, FC2, A2 = 19, 8000.0, 55.0                     # stage 2, at 48 kHz


def solve(A, b):
    """A x = b by Gaussian elimination with partial pivoting."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def least_squares(N, fp, fs, rate, gain, w, R, grid=4000):
    """An odd-length symmetric low-pass, least squares on a grid: `gain` from 0 to fp, 0 from fs to rate / 2 with
    weight w, the band between left free; and each of its R polyphase phases summing to gain / R (by Lagrange
    multipliers, R more equations)."""
    K = (N - 1) // 2
    A = [[0.0] * (K + 1 + R) for _ in range(K + 1 + R)]
    b = [0.0] * (K + 1 + R)
    for g in range(grid + 1):
        f = g / grid * rate / 2
        if f <= fp:
            d, wt = gain, 1.0
        elif f >= fs:
            d, wt = 0.0, w
        else:
            continue
        basis = [1.0] + [2 * math.cos(2 * math.pi * f / rate * k) for k in range(1, K + 1)]
        for i in range(K + 1):
            wb = wt * basis[i]
            b[i] += wb * d
            row = A[i]
            for j in range(K + 1):
                row[j] += wb * basis[j]
    for p in range(R):                  # phase p's sum, in the half-filter a[0..K]
        for i in range(p, N, R):
            A[K + 1 + p][abs(i - K)] += 1.0
            A[abs(i - K)][K + 1 + p] += 1.0
        b[K + 1 + p] = gain / R
    a = solve(A, b)
    return [a[abs(i - K)] for i in range(N)]


def i0(x):
    s, t, k = 1.0, 1.0, 1
    while t > 1e-15 * s:
        t *= (x / 2 / k) ** 2
        s += t
        k += 1
    return s


def kaiser_sinc(N, fc, rate, A, gain):
    """A sinc cut at fc under a Kaiser window for A dB, with gain `gain`."""
    beta = 0.1102 * (A - 8.7) if A > 50 else 0.5842 * (A - 21) ** 0.4 + 0.07886 * (A - 21)
    c = (N - 1) / 2
    h = []
    for i in range(N):
        t = i - c
        x = 2 * math.pi * fc / rate * t
        s = 2 * fc / rate * (1 if t == 0 else math.sin(x) / x)
        h.append(gain * s * i0(beta * math.sqrt(max(0.0, 1 - (t / c) ** 2))) / i0(beta))
    return h


def thousandths(h, R, fixed=()):
    """h in thousandths, rounded half away from zero, and then each of its R phases made to sum to exactly 1000.
    While a phase's sum is off, the move that adds least to the rounding error is made: the centre tap by 1, or a
    symmetric pair of taps by 1 each, so that the filter stays symmetric. (In stage 1 a pair lies in one phase; in
    stage 2 its two taps lie in the two mirrored phases, which so stay equal.) Taps in `fixed` aren't moved."""
    N = len(h)
    q = [int(math.copysign(math.floor(abs(v) * 1000 + 0.5), v)) for v in h]
    for p in range(R):
        while True:
            diff = 1000 - sum(q[p::R])
            if diff == 0:
                break
            step = 1 if diff > 0 else -1
            best = None
            for i in range(p, N, R):
                j = N - 1 - i
                moves = 1 + (j != i and j % R == p)        # what the move adds to this phase's sum
                if i in fixed or moves > abs(diff):
                    continue
                cost = (abs(q[i] + step - h[i] * 1000) - abs(q[i] - h[i] * 1000)) * (1 + (j != i))
                if best is None or cost < best[0]:
                    best = (cost, i, j)
            assert best, 'phase %d cannot be made to sum to 1000' % p
            _, i, j = best
            q[i] += step
            if j != i:
                q[j] += step
    for p in range(R):
        assert sum(q[p::R]) == 1000
    assert q == q[::-1]
    return q


def stage1():
    """Stage 1's taps in thousandths, the whole filter, h[0] to h[158]."""
    return thousandths(least_squares(N1, FP1, FS1, 16000, 2, W1, 2), 2)


def stage2():
    """Stage 2's taps in thousandths, h[0] to h[18]; the centre is 1 (1000) and every third tap from it 0."""
    h = kaiser_sinc(N2, FC2, 48000, A2, 3)
    c = (N2 - 1) // 2
    centre = [i for i in range(N2) if (i - c) % 3 == 0]
    for i in centre:
        h[i] = 1 if i == c else 0
    return thousandths(h, 3, centre)


def phases(h, R):
    """The polyphase split: phase p has h[R j + p], j = 0, 1, ..., the tap for the newest sample first."""
    return [h[p::R] for p in range(R)]


def deck(stage, h, R):
    """The table as cards: the stage, then for each tap of each phase in turn its coefficient and 0, or 1 for the
    phase's last tap; the phase that is the sample itself is one card of 0 and a 2. Stage 2's phases go 1, 2, 0: a
    16 kHz sample makes the 48 kHz samples 3 m + 1, 3 m + 2 and 3 m + 3, so that each round of fir's deck starts with
    the newest sample (the 48 kHz sample 0, which would be the 16 kHz sample three before the first, is left out)."""
    cards = [stage]
    order = phases(h, R)
    if stage == 2:
        order = order[1:] + order[:1]
    for ph in order:
        if 1000 in ph:
            assert ph.count(1000) == 1 and all(v == 0 for v in ph if v != 1000)
            cards += [0, 2]
        else:
            for j, c in enumerate(ph):
                cards += [c, 1 if j == len(ph) - 1 else 0]
    assert all(-999 <= v <= 999 for v in cards)
    return cards


def response(h, f, rate):
    return abs(sum(v / 1000 * cmath.exp(-2j * math.pi * f / rate * i) for i, v in enumerate(h)))


if __name__ == '__main__':
    os.makedirs(TABLES, exist_ok=True)
    h1, h2 = stage1(), stage2()
    for name, cards in (('fir1', deck(1, h1, 2)), ('fir2', deck(2, h2, 3))):
        with open(os.path.join(TABLES, name + '.cards'), 'w') as f:
            f.write('\n'.join(map(str, cards)) + '\n')
        print('%s: %d cards' % (name, len(cards)))
    print('stage 1 phases', [len(p) for p in phases(h1, 2)], 'largest tap %.3f' % (max(map(abs, h1)) / 1000))
    print('phase sums', [sum(p) for p in phases(h1, 2)], [sum(p) for p in phases(h2, 3)])
    for f in (1000, 3000, 3300, 3500, 3700, 3800, 3900, 4000, 4200, 4500, 5000, 6000, 8000):
        print('  stage 1 at %5d Hz: %6.1f dB' % (f, 20 * math.log10(response(h1, f, 16000) / 2 + 1e-12)))
    for f in (1000, 4000, 8000, 12000, 16000, 20000):
        print('  stage 2 at %5d Hz: %6.1f dB' % (f, 20 * math.log10(response(h2, f, 48000) / 3 + 1e-12)))
