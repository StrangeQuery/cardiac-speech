"""Each text machine under the dev emulator against its reference."""
import sys
import cardiac
import text_ref as tr
import test_text as T

TX = '../text/'


def run(listing, piles, inp, out, fetch=None, cycle=None):
    net = cardiac.Net()
    net.add('m', TX + listing, inp, out)
    for p, f in (fetch or {}).items():
        net.fetch[p] = f
        net.piles.setdefault(f[4], [])
    for p, cards in piles.items():
        net.put(p, cards)
    net.run()
    return net


def check(label, got, want):
    if got != want:
        i = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]), min(len(got), len(want)))
        print('  %s DIFFER at %d: got %s want %s (%d %d)' % (label, i, got[max(0, i - 3):i + 8], want[max(0, i - 3):i + 8], len(got), len(want)))
        return False
    return True


def stage(name, t):
    s = tr.scan(t)
    if name == 'scan': return None, s
    a = tr.numd(s)
    if name == 'numd': return s, a
    b = tr.numg(a)
    if name == 'numw': return a, b
    c = tr.say3(b)
    if name == 'say3': return b, c
    d = tr.numf(c)
    if name == 'numf': return c, d
    e = tr.spdec(d)
    if name == 'spcls': return d, e
    e2 = tr.spmark(e)
    if name == 'spell': return e, e2
    f = tr.spell(e2)
    if name == 'names': return e2, f
    g1 = tr.excl(f)
    if name == 'excl': return f, g1
    g = tr.excp(g1)
    assert g == tr.exc(f)
    if name == 'excp': return g1, g
    h = tr.rules(g)
    if name == 'match': return g, h
    i1 = tr.posta(h)
    if name == 'posta': return h, i1
    i2 = tr.postb(i1)
    if name == 'postb': return i1, i2
    i = tr.postc(i2)
    if name == 'postc': return i2, i
    return i, tr.join(i)


def chars(t):
    return [ord(c) for c in t] + [-1]


def match_net(cards):
    net = cardiac.Net()
    net.add('loader', TX + 'loader.cq', {'ga': 'adv', '*': 'in'},
            {'let': 'wl', 'lend': 'wl', 'el': 'pl', 'pl1': 'pl', 'pl2': 'pl', 'er': 'pr', 'pr1': 'pr', 'pr2': 'pr', '*': 'flt'})
    net.fan['wl'] = ['wl_l', 'wl_r']
    net.add('filter', TX + 'filter.cq', {'gd': 'deck', 'fwd': 'deck', '*': 'flt'}, {'*': 'rin'})
    net.cycle['deck'] = tr.RULES
    net.add('rule', TX + 'rule.cq', {'vd': 'vl', 'gr': 'vr', '*': 'rin'},
            {'ol': 'cl', 'dl': 'cl', 'or': 'cr', 'dr': 'cr', 'al': 'adv', 'no': 'adv', '*': 'out'})
    net.add('ctxl', TX + 'ctx.cq', {'gw': 'wl_l', 'lett': 'pl', 'gdir': 'pl', '*': 'cl'}, {'*': 'vl'})
    net.add('ctxr', TX + 'ctx.cq', {'gw': 'wl_r', 'lett': 'pr', 'gdir': 'pr', '*': 'cr'}, {'*': 'vr'})
    for p in ('adv', 'in', 'out', 'pl', 'pr', 'cl', 'cr', 'vl', 'vr', 'rin', 'flt'):
        net.piles.setdefault(p, [])
    net.put('in', cards)
    net.run()
    return net


SETUP = {
    'scan': lambda t, i: run('scan.cq', {'in': chars(t) + chars(t)}, {'gc': 'ft', 'gv': 'ft', '*': 'in'}, {'ask': 'ask', '*': 'out'},
                             {'ask': (tr.ASCII, 2, 0, 2, 'ft')}),
    'numd': lambda t, i: run('numd.cq', {'in': i}, {'gb': 'self', 'gs': 'self', '*': 'in'}, {'keep': 'self', '*': 'out'}),
    'numw': lambda t, i: run('numw.cq', {'in': i}, {'*': 'in'}, {'*': 'out'}),
    'say3': lambda t, i: run('say3.cq', {'in': i}, {'*': 'in'}, {'*': 'out'}),
    'spcls': lambda t, i: run('spcls.cq', {'in': i}, {'*': 'in'}, {'*': 'out'}),
    'spell': lambda t, i: run('spell.cq', {'in': i}, {'gp': 'self', 'gp2': 'self', '*': 'in'}, {'keep': 'self', '*': 'out'}),
    'names': lambda t, i: run('names.cq', {'in': i}, {'gn': 'ft', '*': 'in'}, {'ask': 'ask', '*': 'out'},
                              {'ask': (tr.LETTERS, 8, 0, 8, 'ft')}),
    'excl': lambda t, i: run('excl.cq', {'in': i, 'deck': tr.EXC * 400}, {'gw': 'self', 'gy': 'self', 'gz': 'self', 'gd': 'deck', '*': 'in'},
                             {'keep': 'self', 'kw': 'self', 'ky': 'self', '*': 'out'}),
    'excp': lambda t, i: run('excp.cq', {'in': i}, {'gw': 'self', 'gp': 'ft', '*': 'in'}, {'keep': 'self', 'ask': 'ask', '*': 'out'},
                             {'ask': (tr.EXPHON, 12, 0, 12, 'ft')}),
    'match': lambda t, i: match_net(i),
    'posta': lambda t, i: run('posta.cq', {'in': i}, {'*': 'in'}, {'*': 'out'}),
    'postb': lambda t, i: run('postb.cq', {'in': i}, {'gy': 'self', 'gw': 'self', '*': 'in'}, {'keep': 'self', '*': 'out'}),
    'postc': lambda t, i: run('postc.cq', {'in': i}, {'*': 'in'}, {'*': 'out'}),
    'join': lambda t, i: run('join.cq', {'in': i}, {'*': 'in'}, {'*': 'out'}),
    'numf': lambda t, i: run('numf.cq', {'in': i}, {'gf': 'ft', '*': 'in'}, {'ask': 'ask', '*': 'out'},
                             {'ask': (tr.NUMBERS, 10, 0, 10, 'ft')}),
}

if __name__ == '__main__':
    for name in sys.argv[1:]:
        ok = True
        for t in T.texts:
            i, want = stage(name, t)
            net = SETUP[name](t, i)
            ok &= check(repr(t[:20]), net.piles.get('out', []), want)
        print(name, 'exact' if ok else 'DIFFERENT')
