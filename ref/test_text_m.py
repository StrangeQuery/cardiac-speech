"""Each text machine under the dev emulator against its reference, on the 929 test texts: the text machines run as
the host wires them (nets.text), and each machine's punched cards are checked against what text_ref says it
punches, in its own layout. `python3 test_text_m.py` checks every machine; `test_text_m.py scan numd ...` the
ones named (match is left, right, first and pick together)."""
import sys
import nets
import text_ref as tr
import test_text as T


def numd_cards(cards):
    """numd's cards: as text_ref.numd, but the six digits held as two numbers of three digits (-15, count, hi, lo),
    and a number of seven digits or more as -17, hi and lo (its first six) and then 700 + each digit after."""
    out = []
    for c in tr.numd(cards):
        out.append(c)
    # rebuild from text_ref.numd's cards: -15, n, six digits -> -15, n, hi, lo; a run of 700 + d of seven or more
    res, i = [], 0
    while i < len(out):
        c = out[i]
        if c == -15:
            n, ds = out[i + 1], out[i + 2:i + 8]
            res += [-15, n, 100 * ds[0] + 10 * ds[1] + ds[2], 100 * ds[3] + 10 * ds[4] + ds[5]]
            i += 8
        elif 700 <= c <= 709:
            j = i
            while j < len(out) and 700 <= out[j] <= 709:
                j += 1
            ds = [x - 700 for x in out[i:i + 6]]
            res += [-17, 100 * ds[0] + 10 * ds[1] + ds[2], 100 * ds[3] + 10 * ds[4] + ds[5]] + out[i + 6:j]
            i = j
        else:
            res.append(c)
            i += 1
    return res


def items(cards):
    """items's records: each run of cards 0 or more and the card below 0 after it: that card, n, and the run (13
    cards at most) with an edge on each side, padded to 15."""
    out, run = [], []
    for c in cards:
        if c >= 0:
            if len(run) < 13:
                run.append(c)
        else:
            w = [28] + run + [28]
            out += [c, len(run)] + w + [0] * (15 - len(w))
            run = []
    return out


RULES = {-13: -21, -14: -22}


def expected(t):
    s = tr.scan(t)
    e = {'scan': s, 'numd': numd_cards(s)}
    a = tr.numd(s)
    e['unpack'] = a
    b = tr.numg(a)
    e['numw'] = b
    c = tr.say3(b)
    e['say3'] = c
    e['ask1'] = [x for v in c for x in ((v % 100 if v >= 700 else 0), v)]
    d = tr.numf(c)
    e['numf'] = d
    sp = tr.spdec(d)
    e['spcls'] = sp
    sm = tr.spmark(sp)
    e['spell'] = sm
    e['ask2'] = [x for v in sm for x in ((v % 100 if v >= 100 else 0), v)]
    f = tr.spell(sm)
    e['names'] = f
    it = items(f)
    e['items'] = it
    recs = [it[i:i + 17] for i in range(0, len(it), 17)]
    g1 = tr.excl(f)
    fl, ks, i = [], [], 0
    while i < len(g1):
        if g1[i] == -99:
            fl.append(g1[i + 1])
            ks.append(-g1[i + 2] - 100 if g1[i + 2] else 0)
            i += 3
        else:
            if g1[i] < 0:
                fl.append(0)
                ks.append(0)
            i += 1
    e['excl'], e['excx'] = fl, ks
    g = tr.exc(f)
    e['match'] = [RULES.get(x, x) for x in tr.rules(g)]
    h = tr.posta(tr.rules(g))
    e['posta'] = [RULES.get(x, x) for x in h]
    i2 = tr.postb(h)
    e['posth'] = i2
    e['postc'] = tr.postc(i2)
    e['join'] = tr.join(tr.postc(i2))
    return e


MACHINES = ['scan', 'numd', 'unpack', 'numw', 'say3', 'ask1', 'numf', 'spcls', 'spell', 'ask2', 'names', 'items',
            'excl', 'excx', 'match', 'posta', 'posth', 'postc', 'join']


def check(name, got, want, label):
    if got != want:
        i = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]), min(len(got), len(want)))
        print('  %s %s DIFFER at %d: got %s want %s (%d %d)' % (name, label, i, got[max(0, i - 3):i + 8],
                                                              want[max(0, i - 3):i + 8], len(got), len(want)))
        return False
    return True


if __name__ == '__main__':
    names = sys.argv[1:] or MACHINES
    ok = {n: True for n in names}
    decks = nets.text_decks()
    for t in T.texts:
        taps = {}
        nets.text([ord(c) if ord(c) < 128 else 32 for c in t], taps=taps, decks=decks)
        want = expected(t)
        for n in names:
            ok[n] &= check(n, taps.get('pick' if n == 'match' else n, []), want[n], repr(t[:20]))
    for n in names:
        print(n, 'exact' if ok[n] else 'DIFFERENT')
