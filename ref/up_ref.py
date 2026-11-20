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


# ---------------------------------------------------------------------------------------------------- the high band
# The 48 kHz version's high band (upsample/hand/hnoise.cq, hfilt.cq, hmix.cq): frication from 4 kHz up, which the
# 8 kHz speech can't carry. Each frame's level is the record of upsample/tables/hiband.cards (made by hb_table.py)
# that choose's filter for the frame names. hnoise ramps the level across each frame as interp does A (a step of
# (next - this) / 10 every 120 samples, none across a change of V), and puts out 120 samples a step of +L or -L by a
# decimal LCG, x = 21 x + 7 mod 1000, whose place is moved on by a second one, x = x + w, w = 21 w + 7 mod 1000, at
# the start of every step, so that the noise doesn't repeat every 1,000 samples; a step whose level is 0 puts out 0s.
# hfilt shapes it: the zeros (1 - z^-1)^3 (1 + z^-1)^2, e = s - s1 - 2 s2 + 2 s3 + s4 - s5, and a two-pole resonance
# at 5.0 kHz, 0.8 kHz wide, y = e + 1.5 y1 - 0.9 y2, each tenth truncated towards zero; a 0 in clears its state and
# puts out 0. hmix adds 4 y to each 48 kHz sample, 245 samples later, the 48 kHz speech's delay behind the 8 kHz
# speech.
HB_STEP = 120          # 48 kHz samples a step (20 at 8 kHz)
HB_DELAY = 245         # the 48 kHz speech's delay, in 48 kHz samples
HB_UNIT = 4            # a sample of the high band is 4 y


def hb_table():
    return [int(v) for v in open(os.path.join(TABLES, 'hiband.cards')).read().split()]


def hb_records(frame_cards, filters, table=None):
    """(V, level) for each frame, and (-1, 0) for the end, as the host collates them for hnoise."""
    table = hb_table() if table is None else table
    vs = frame_cards[0::13]
    assert vs[len(filters)] == -1 and len(vs) == len(filters) + 1
    return [(v, table[a]) for v, a in zip(vs, filters)] + [(-1, 0)]


def hnoise(recs):
    x, w = 123, 0
    out = []
    for (v, h), (nv, nh) in zip(recs, recs[1:]):
        d = trunc10(nh - h) if nv == v else 0
        for _ in range(10):
            x = (x + w) % 1000
            w = (21 * w + 7) % 1000
            if h == 0:
                out += [0] * HB_STEP
            else:
                for _ in range(HB_STEP):
                    x = (21 * x + 7) % 1000
                    out.append(h if x >= 500 else -h)
            h += d
            assert 0 <= h <= 999
    return out


def hfilt(ss):
    s1 = s2 = s3 = s4 = s5 = y1 = y2 = 0
    out = []
    for s in ss:
        if s == 0:
            s1 = s2 = s3 = s4 = s5 = y1 = y2 = 0
            out.append(0)
            continue
        e = s - s1 - 2 * s2 + 2 * s3 + s4 - s5
        s5, s4, s3, s2, s1 = s4, s3, s2, s1, s
        y = trunc10(5 * y1) + y1 + e - trunc10(9 * y2)
        assert abs(y) <= 999, 'the high band %d does not fit in a cell' % y
        y2, y1 = y1, y
        out.append(y)
    return out


def hiband(frame_cards, filters, table=None):
    """The high band's samples, y, as hfilt puts them out (before the delay)."""
    return hfilt(hnoise(hb_records(frame_cards, filters, table)))


def hmix(values48, ys):
    """The 48 kHz samples' values with the high band added, 4 y each, the y delayed by HB_DELAY samples."""
    ys = [0] * HB_DELAY + ys
    out = []
    for i, (th, u) in enumerate(zip(values48[0::2], values48[1::2])):
        a = 4000 + HB_UNIT * ys[i] + u
        assert 0 <= a <= 9999
        out += [th + a // 1000 - 4, a % 1000]
    return out
