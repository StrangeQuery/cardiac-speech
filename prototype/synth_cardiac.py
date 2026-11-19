#!/opt/homebrew/bin/python3
"""Decimal model of the LPC synthesizer using only CARDIAC arithmetic.

usage: synth_cardiac.py in.frames out.wav [--terms N] [--mode float|fixed] [--headroom H]
                        [--outcells 1|2]

Every stored value is checked to be in -999..999 and the accumulator in -9999..9999.
Multiplies are Horner sums of digit terms: for each term, d ADDs (or SUBs, for a negative
coefficient) from a shared row of nine, then one SFT 0g.  Truncation is toward zero, as SFT
does it; STO keeps the last three digits with the sign (wraps are counted, never hidden).

Tracks (host, ahead of time): each frame becomes integer cards: V, P, A (excitation
amplitude at sample scale S) and K1..K10 = round(k * 1000).  Everything after that is
CARDIAC arithmetic: interpolation (cur += trunc((next - cur) / 10) each 20-sample step),
reduction of each K to N digit terms, excitation, lattice, de-emphasis, output.
"""
import math
import sys
from common import (read_frames, write_wav, Noise, STEPS, STEP_LEN, ORDER, PRE)
import synth_float as sf


class Overflow(Exception):
    pass


class Cardiac:
    """Arithmetic + instruction counters.  Only the operations a CARDIAC has."""
    def __init__(self):
        self.acc = 0
        self.count = {}
        self.wraps = 0
        self.wrap_where = {}
        self.section = 'filter'

    def tick(self, op, n=1):
        key = (self.section, op)
        self.count[key] = self.count.get(key, 0) + n

    def check(self):
        if not -9999 <= self.acc <= 9999:
            raise Overflow('accumulator %d' % self.acc)

    def cla(self, v):
        assert -999 <= v <= 999, v
        self.acc = v
        self.tick('CLA')

    def add(self, v, n=1):
        assert -999 <= v <= 999, v
        self.acc += v * n          # n consecutive ADDs of the same cell (the ADD row)
        self.tick('ADD', n)
        self.check()

    def sub(self, v, n=1):
        assert -999 <= v <= 999, v
        self.acc -= v * n
        self.tick('SUB', n)
        self.check()

    def sft(self, left, right):
        s = -1 if self.acc < 0 else 1
        m = abs(self.acc)
        m = (m * 10 ** left) % 10000
        m = m // 10 ** right
        self.acc = s * m
        self.tick('SFT')

    def sto(self, split=False):
        """split=True marks a deliberate wrap: keeping the units of a two-cell value."""
        s = -1 if self.acc < 0 else 1
        m = abs(self.acc)
        if m > 999 and not split:
            self.wraps += 1
            self.wrap_where[self.section] = self.wrap_where.get(self.section, 0) + 1
        self.tick('STO')
        return s * (m % 1000)

    def jmp(self, n=1):
        self.tick('JMP', n)

    def other(self, op, n=1):
        self.tick(op, n)


def reduce_k(K, terms, mode):
    """Reduce a 3-digit coefficient K (k = K/1000) to `terms` digit terms.
    Returns (sign, [(position, digit), ...]) with position 1 = tenths, 2 = hundredths,
    3 = thousandths.  'float' keeps the leading nonzero digits wherever they are;
    'fixed' keeps the first `terms` decimal places."""
    s = -1 if K < 0 else 1
    m = abs(K)
    if m == 0:
        return s, []
    if mode == 'fixed':
        lead = 1
    else:
        lead = 1 if m >= 100 else 2 if m >= 10 else 3
    last = min(3, lead + terms - 1)
    q = 10 ** (3 - last)
    r = (m + q // 2) // q * q          # round to the kept places
    if r > 999:
        r = 1000 - q                    # stay below 1 (0.9, 0.99, 0.999)
    digits = []
    for p in range(1, 4):
        d = (r // 10 ** (3 - p)) % 10
        if d:
            digits.append((p, d))
    return s, digits


def k_value(sign, digits):
    return sign * sum(d * 10 ** -p for p, d in digits)


ROUND = False


def mul(cpu, sign, digits, x, x_in_acc=False):
    """k * x by Horner over the digit terms, as CARDIAC would run it with a shared ADD/SUB row.
    Code: [CLA x] STO c; CLA zero; per term: JMP row+9-d; d x ADD/SUB c; JMP 99; (8xx in 99);
    SFT 0g.  Returns the product left in the accumulator."""
    if not x_in_acc:
        cpu.cla(x)
    cpu.other('STO')                     # STO c
    cpu.cla(0)                           # CLA zero
    if not digits:
        return 0
    terms = list(reversed(digits))       # least significant first
    prev = terms[0][0]
    for idx, (p, d) in enumerate(terms):
        if idx:
            cpu.sft(0, prev - p)
        cpu.jmp()                        # JMP into the row (self-modified target)
        if sign > 0:
            cpu.add(x, d)
        else:
            cpu.sub(x, d)
        cpu.jmp(2)                       # JMP 99, then the 8xx return in cell 99
        prev = p
    if ROUND:
        # round half away from zero: TAC on the sign, then ADD or SUB 5 x 10^(prev-1), JMP
        h = 5 * 10 ** (prev - 1)
        cpu.other('TAC')
        if cpu.acc < 0:
            cpu.sub(h)
        else:
            cpu.add(h)
        cpu.jmp()
    cpu.sft(0, prev)                     # final shift by the leading term's place
    return cpu.acc


def schedule_cards(frames, S):
    """Integer cards per frame, then CARDIAC-style interpolation into per-step integers."""
    cards = []
    for fr in frames:
        A = int(round(sf.amplitude(fr) * S))
        assert A <= 999, 'amplitude %d too big for a cell; lower the scale' % A
        cards.append((fr['v'], fr['p'], A, [max(-999, min(999, int(round(k * 1000)))) for k in fr['k']]))
    steps = []
    for i, (v, P, A, K) in enumerate(cards):
        nv, nP, nA, nK = cards[i + 1] if i + 1 < len(cards) else cards[i]
        interp = (v == nv)
        def delta(a, b):
            if not interp:
                return 0
            d = b - a
            return int(d / 10)           # SFT 01: truncation toward zero
        dP, dA = delta(P, nP), delta(A, nA)
        dK = [delta(K[j], nK[j]) for j in range(ORDER)]
        cP, cA, cK = P, A, list(K)
        for s in range(STEPS):
            if s:
                cP += dP; cA += dA
                cK = [cK[j] + dK[j] for j in range(ORDER)]
            steps.append((v, cP, cA, list(cK)))
    return cards, steps


def run(frames, terms=2, mode='float', headroom=1.0, outcells=2, S=None, steps_override=None):
    """Returns (output floats at full scale, info dict)."""
    if S is None:
        info = {}
        sf.synth(sf.schedule_float(frames), internal=info)
        S = headroom * 999 / info['lattice_max']
        if outcells == 2:
            S = min(S, headroom * 9999 / info['out_max'])
    cards, steps = schedule_cards(frames, S)
    if steps_override is not None:
        steps = steps_override
    red = [[reduce_k(K, terms, mode) for K in st[3]] for st in steps]
    # output scaling for one-cell output: yd = trunc(m * y) + 0.9 yd, m one digit term
    m_digits = None
    if outcells == 1:
        info = {}
        sf.synth(sf.schedule_float(frames), internal=info)
        mval = 999 / (info['out_max'] * S) * headroom
        m_digits = reduce_k(min(999, int(mval * 1000)), 1, 'float')
        m_digits = (1, [(p, d) for p, d in m_digits[1]])
        if mval >= 1:
            m_digits = None              # no scaling needed
    exc = sf.excitation([(v, P, A, None) for (v, P, A, K) in steps])
    cpu = Cardiac()
    b = [0] * (ORDER + 1)
    hi, lo, yd1 = 0, 0, 0
    out = []
    n = 0
    noise_cost = {'v': 9, 'u': 13}
    for si, (v, P, A, K) in enumerate(steps):
        ks = red[si]
        for _ in range(STEP_LEN):
            # excitation (counted, arithmetic trivial): pulse counter or LCG + sign test
            cpu.section = 'excite'
            cpu.other('misc', noise_cost['v' if v else 'u'])
            sv = exc[n]
            n += 1
            if sv in (1.0, -1.0, 0.0):
                e = int(sv) * A
            else:                         # chirp value x A: a two-term multiply
                cv = int(round(sv * 1000))
                sg2, dg2 = reduce_k(cv, 3, 'float')
                mul(cpu, sg2, dg2, A)
                e = cpu.sto()
            cpu.section = 'filter'
            f = e
            for i in range(ORDER, 0, -1):
                sg, dg = ks[i - 1]
                mul(cpu, sg, dg, b[i - 1])
                p = cpu.sto()                       # STO p
                cpu.cla(f); cpu.sub(p); f = cpu.sto()     # f = f - p
                mul(cpu, sg, dg, f, x_in_acc=True)
                q = cpu.sto()                       # STO q
                cpu.cla(b[i - 1]); cpu.add(q); b[i] = cpu.sto()
            b[0] = f
            cpu.section = 'output'
            if outcells == 2:
                # yd = y + 0.9 yd, yd kept as thousands (hi) and units (lo), same sign
                mul(cpu, 1, [(1, 9)], lo); t = cpu.sto()          # 0.9 lo
                cpu.cla(hi); cpu.other('STO'); cpu.cla(0)         # 9 hi via the row ...
                cpu.jmp(); cpu.add(hi, 9); cpu.jmp(2)
                cpu.sft(2, 0)                                     # ... times 100 = 900 hi
                cpu.add(t); cpu.add(f)
                yd = cpu.acc
                lo = cpu.sto(split=True)
                cpu.sft(0, 3); hi = cpu.sto()
                cpu.other('OUT', 2)
                out.append(yd)
            else:
                if m_digits:
                    mul(cpu, 1, m_digits[1], f); ym = cpu.sto()
                else:
                    ym = f
                mul(cpu, 1, [(1, 9)], yd1); t = cpu.sto()
                cpu.cla(ym); cpu.add(t); yd1 = cpu.sto()
                cpu.other('OUT')
                out.append(yd1 / (k_value(*m_digits) if m_digits else 1))
            cpu.section = 'loop'
            cpu.other('misc', 6)        # 2 INP + 2 OUT between machines is per machine; loop/JMP here
    nsamp = len(out)
    info = {'S': S, 'wraps': cpu.wraps, 'wrap_where': cpu.wrap_where, 'count': cpu.count, 'samples': nsamp,
            'steps': steps, 'red': red, 'cards': cards}
    return [v / S for v in out], info


def float_from_steps(steps, S, red=None):
    """Float synthesis on the decimal schedule (same integer pitch/amp/K), optionally with
    the reduced coefficients: isolates the decimal arithmetic from coefficient quantization."""
    sched = []
    for si, (v, P, A, K) in enumerate(steps):
        if red is None:
            ks = [k / 1000 for k in K]
        else:
            ks = [k_value(*r) for r in red[si]]
        sched.append((v, P, A / S, ks))
    return sf.synth(sched)


if __name__ == '__main__':
    args = sys.argv[1:]
    opts = {'--terms': 2, '--mode': 'float', '--headroom': 1.0, '--outcells': 2}
    pos = []
    i = 0
    while i < len(args):
        if args[i] in opts:
            opts[args[i]] = type(opts[args[i]])(args[i + 1]); i += 2
        else:
            pos.append(args[i]); i += 1
    fr = read_frames(pos[0])
    y, info = run(fr, opts['--terms'], opts['--mode'], opts['--headroom'], opts['--outcells'])
    write_wav(pos[1], y)
    print('wrote %s  S=%.1f wraps=%d %s' % (pos[1], info['S'], info['wraps'], info['wrap_where']))
