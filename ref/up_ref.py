"""The upsampler's arithmetic in Python, for the third version (upsample/), as the CARDIACs do it, so that its
machines can be checked against it sample for sample: yd, then the two stages of fir, with the coefficients of
upsample/tables/fir1.cards and fir2.cards (made by up_table.py).

yd turns each 8 kHz sample, the output stage's thousands and units of 20 yd, back into yd: 50 thousands + 5 units
/ 100. A stage is a polyphase FIR filter. Each tap's product is 10 c x in tenths, for c = 0.d1 d2 d3 (its sign put on
x): Horner from the last digit, d3 v, then a tenth of that (SFT truncates towards zero) plus d2 v, a tenth of that
plus d1 v. Stage 1 puts each sum out divided by 10, rounded half away from zero, as a 16 kHz sample in a cell;
stage 2 puts twice each sum out, which is the 48 kHz sample (the sum is in tenths of yd, and the sample is 20 yd),
as thousands and units. In stage 2 one phase in three is the 16 kHz sample itself, ten times it in tenths.

The asserts are the places where a value would no longer fit: a sample in a cell, a sum in the accumulator."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = os.path.join(HERE, '..', 'upsample', 'tables')

# the phases as the host wires them (upsample/src/lib.rs): for each phase, the age of the sample each tap reads
STAGE1 = [list(range(80)), list(range(79))]
STAGE2 = [list(range(6)), list(range(6)), [2]]


def table(name):
    """A table's phases: for each, its coefficients in thousandths, or None for the sample itself."""
    cards = [int(v) for v in open(os.path.join(TABLES, name + '.cards')).read().split()]
    phases, ph = [], []
    for c, last in zip(cards[1::2], cards[2::2]):
        if last == 2:
            phases.append(None)
            continue
        ph.append(c)
        if last == 1:
            phases.append(ph)
            ph = []
    return cards[0], phases


def trunc10(v):
    """SFT 01: a tenth, truncated towards zero."""
    return v // 10 if v >= 0 else -((-v) // 10)


def product(c, x):
    """10 c x in tenths, as fir's routine works it out."""
    v = x if c >= 0 else -x
    m = abs(c)
    d1, d2, d3 = m // 100, m // 10 % 10, m % 10
    a = trunc10(d3 * v)
    a = trunc10(a + d2 * v)
    return a + d1 * v


def yd(th, u):
    assert 0 <= u <= 999
    y = 50 * th + 5 * u // 100
    assert -999 <= y <= 999, 'yd %d does not fit in a cell' % y
    return y


def stage(xs, phases, ages):
    """One stage on the samples xs: for each sample in, each phase's sum S (in tenths), in turn."""
    out = []
    for n in range(len(xs)):
        for ph, age in zip(phases, ages):
            if ph is None:
                (k,) = age
                out.append(10 * (xs[n - k] if n >= k else 0))
                continue
            assert len(ph) == len(age)
            lo, hi = 0, 0
            for c, k in zip(ph, age):
                a = product(c, xs[n - k] if n >= k else 0) + lo
                assert abs(a) <= 9999, 'P + lo = %d passes the accumulator' % a
                q = int(a / 1000)              # SFT 03, and STO keeping the rest with a's sign
                lo = a - 1000 * q
                hi += q
            S = 1000 * hi + lo
            assert abs(hi) <= 9 and abs(S) <= 9999, 'the sum %d passes the accumulator' % S
            out.append(S)
    return out


def round10(S):
    q = (abs(S) + 5) // 10
    return q if S >= 0 else -q


def upsample(values):
    """The output stage's values (thousands and units of each 8 kHz sample) in; the 48 kHz samples' values out, the
    thousands and units of each, as fir2 puts them out."""
    xs = [yd(th, u) for th, u in zip(values[0::2], values[1::2])]
    s1, p1 = table('fir1')
    s2, p2 = table('fir2')
    assert (s1, s2) == (1, 2)
    y16 = []
    for S in stage(xs, p1, STAGE1):
        y = round10(S)
        assert -999 <= y <= 999, 'a 16 kHz sample %d does not fit in a cell' % y
        y16.append(y)
    out = []
    for S in stage(y16, p2, STAGE2):
        s = 2 * S
        out += [s // 1000, s % 1000]
    return out


def samples(values):
    """Pairs of values joined into samples."""
    return [th * 1000 + u for th, u in zip(values[0::2], values[1::2])]
