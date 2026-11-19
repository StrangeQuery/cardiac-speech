"""Each front-end machine under the dev emulator against its function in front_machines, on the test sentences:
the whole front end runs as the host wires it (nets.front), and each machine's punched cards are checked against
what the references say it punches, in its own record layout. `python3 run_tests.py` checks every machine;
`run_tests.py feat glidea ...` the ones named."""
import sys
import front_machines as fm
import front_ref as fr
import nets
import table as tb
import voice_ref as vr
sys.path.insert(0, vr.LPC)
import text_to_phonemes as tp   # noqa: E402


def tokens(text):
    return fr.tokens_of(' '.join(tp.text_to_phonemes(text)))


def flat(r):
    return [c for x in r for c in x]


def lists(fs):
    """A deck of factor lists, each ended by 0, as lists without their 100s (multiplying by 100 changes nothing)."""
    out, cur = [], []
    for f in fs:
        if f:
            cur.append(f)
        else:
            out.append([x for x in cur if x != 100])
            cur = []
    return out


def expected(toks):
    """{machine: the cards it should punch} for a sentence's tokens, from front_machines."""
    cards, d = fm.compose(toks)
    r1, ko, lv = d['r1'], d['ko'], d['lv']
    F = fm.FEATURES
    AX = tb.CODE['AX']
    e = {'feat': flat([r[:5] for r in r1])}
    e['after'] = flat(reversed(d['a']))
    e['ahead'] = flat(reversed(d['b']))
    e['next'] = flat(reversed(d['c']))
    e['stress'] = flat(d['st'])
    e['base'] = flat(d['bs'])
    e['mul'] = flat(d['du'])
    e['nframes'] = flat(d['n'])
    e['back'] = flat(d['bk'])
    e['closure'] = flat(d['cl'])
    e['main'] = flat(d['mn'])
    e['edge'] = flat(d['ed'])
    sums = d['sums']
    sm, si = [], 0
    for r in r1:
        if r[fm.SEND]:
            sm += [r[fm.SEND]] + sums[si]
            si += 1
        else:
            sm += [0] * 5
    e['sum'] = sm
    fl, si, cur = [], len(sums), None
    for r in reversed(r1):
        if r[fm.SEND]:
            si -= 1
            cur = sums[si]
        fl += cur
    e['fill'] = fl
    e['loud'] = flat([[F[(c[1] or bk[1] or AX) * tb.FEAT + tb.F_LOUD], F[c[2] * tb.FEAT + tb.F_LOUD]]
                      for c, bk in zip(d['c'], d['bk'])])
    # frame by frame
    segs = list(zip(r1, d['n'], d['c'], d['st'], d['bk'], d['cl'], d['mn'], d['ed']))
    fr_, ns_, sa, sb, sc = [], [], [], [], []
    ns = 1
    flr = [fl[i:i + 4] for i in range(0, len(fl), 4)][::-1]
    ldr = [e['loud'][i:i + 2] for i in range(0, len(e['loud']), 2)]
    for (r, (n,), c, st, bk, cl, mn, ed), f4, l2 in zip(segs, flr, ldr):
        for j in range(n):
            u = (10 * j + 5) // n
            fr_ += [j, u, fm.weight(j, n), fm.weight(n - 1 - j, n), 1 if (r[fm.SEND] == 3 and j == n - 1) else 0, u, u]
            ns_.append(ns)
            ns = 0
            sa += cl + mn + ed
            sb += [bk[0], c[5], r[fm.KIND], st[0]]
            sc += f4 + l2
        if r[fm.SEND]:
            ns = 1
    e.update(framer=fr_, sents=ns_, spreada=sa, spreadb=sb, spreadc=sc)
    ch = []
    fi = 0
    for (r, (n,), c, st, bk, cl, mn, ed) in segs:
        for j in range(n):
            a, b, uu = ko[fi][:3]
            g = mn[4] if not (j < cl[0] or (j == 0 and ed[1])) else 0
            ch += [a, b, uu, g] + lv[fi]
            fi += 1
    e['choose'] = ch
    e['glides'] = flat(ko)
    e['glidea'] = flat([k[:2] + [fr.blend(x, y, k[2]) for x, y in zip(fm.frec(k[0]), fm.frec(k[1]))] for k in ko])
    e['glideb'] = flat([k[3:5] + ks for k, ks in zip(ko, d['ks'])])
    # the pitch: decl the fall alone, rise with the rise, taily y and the end
    dc, ty = [], []
    si, fi = 0, 0
    for (r, (n,), *_rest) in segs:
        for j in range(n):
            if ns_[fi]:
                L, tailo, M, end = sums[si]
                si += 1
                q = qr = 0
                f = y = yr = 0
            dc.append(130 - q)
            if q < 30:
                qr += 30
                while qr >= L:
                    qr -= L
                    q += 1
                q = min(q, 30)
            ty += [y if (tailo >= 0 and f >= tailo) else -1, end]
            f += 1
            if tailo >= 0 and f > tailo and y < 100:
                yr += 100
                while yr >= M:
                    yr -= M
                    y += 1
                y = min(y, 100)
            fi += 1
    e.update(decl=dc, rise=d['bases'], taily=ty, tailf=d['f0s'], period=flat([[p, p] for p in d['ps']]))
    chain = fm.f8_chain([x[:1] + y[:1] + n + c[1:2] + bk[1:2] + c[2:3] for x, y, n, c, bk in
                         zip(fm.select(r1, [fm.KIND]), d['st'], d['n'], d['c'], d['bk'])], lv, d['us'], d['gs'], d['ps'], ko)
    e['lsel'] = flat(chain['ls'])
    e['vsel'] = flat(chain['vs'])
    e['psel'] = flat(chain['pss'])
    e['gnorm'] = flat([[k[4] if k[5] != 10 else 0] + g for k, g in zip(ko, chain['gm'])])
    for k in range(1, 6):
        e['mulx%d' % k] = flat(chain['m%d' % k])
    e['kcarry'] = flat(fm.f9_kcarry(lv, d['ks']))
    e['asm'] = cards
    return e, d


def check(name, got, want, label):
    if got != want:
        i = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]), min(len(got), len(want)))
        print('  %s %s DIFFER at %d: got %s want %s (lengths %d %d)' % (name, label, i, got[max(0, i - 3):i + 8],
                                                                      want[max(0, i - 3):i + 8], len(got), len(want)))
        return False
    return True


def factors(taps, d, label):
    """rules2, rules5 and rules9 against front_machines' lists of factors (their 100s aside)."""
    r2, r5, r9 = taps['rules2'], taps['rules5'], taps['rules9']
    n = len(r2) // 4
    fa = [[x for x in r2[4 * i:4 * i + 4] + r5[4 * i:4 * i + 3] if x != 100] for i in range(n)]
    fb = [[x for x in r9[4 * i:4 * i + 3] if x != 100] for i in range(n)]
    ok = all(r5[4 * i + 3] == 0 and r9[4 * i + 3] == 0 for i in range(n))
    return check('rules', [fa, fb, ok], [lists(d['fa']), lists(d['fb']), True], label)


MACHINES = ['feat', 'after', 'ahead', 'next', 'stress', 'base', 'rules', 'mul', 'nframes', 'back', 'sum', 'closure',
            'main', 'edge', 'loud', 'fill', 'framer', 'sents', 'spreada', 'spreadb', 'spreadc', 'choose', 'glides',
            'glidea', 'glideb', 'decl', 'rise', 'taily', 'tailf', 'period', 'lsel', 'vsel', 'psel', 'gnorm', 'mulx1',
            'mulx2', 'mulx3', 'mulx4', 'mulx5', 'kcarry', 'asm']


def test(texts, names):
    """{machine: exact on every text}."""
    ok = {n: True for n in names}
    for t in texts:
        toks = tokens(t)
        want, d = expected(toks)
        taps = {}
        nets.front(toks, taps=taps)
        for n in names:
            if n == 'rules':
                ok[n] &= factors(taps, d, t[:20])
            else:
                ok[n] &= check(n, taps.get(n, []), want[n], t[:20])
    return ok
