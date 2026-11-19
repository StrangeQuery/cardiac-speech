"""Each front-end machine under the dev emulator against its function in front_machines, on the test sentences."""
import sys
import cardiac
import front_machines as fm
import front_ref as fr
import table as tb
import voice_ref as vr
import sentences
sys.path.insert(0, vr.LPC)
import text_to_phonemes as tp   # noqa: E402

F = '../front/'


def tokens(text):
    return fr.tokens_of(' '.join(tp.text_to_phonemes(text)))


def run(name, listing, piles, inp, out, fetch=None):
    net = cardiac.Net()
    net.add(name, F + listing, inp, out)
    for p, (table, size, off, count, to) in (fetch or {}).items():
        net.fetch[p] = (table, size, off, count, to)
        net.piles.setdefault(to, [])
    for p, cards in piles.items():
        net.put(p, cards)
    st = net.run()
    return net, st


def check(label, got, want):
    ok = got == want
    if not ok:
        i = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]), min(len(got), len(want)))
        print('  %s DIFFER at %d: got %s want %s (lengths %d %d)' % (label, i, got[max(0, i - 3):i + 8], want[max(0, i - 3):i + 8], len(got), len(want)))
    return ok


def test_f1(texts):
    ok = True
    for t in texts:
        toks = tokens(t)
        net, st = run('feat', 'feat.cq', {'tokens': toks}, {'*': 'tokens', 'cp': 'feat'}, {'rec': 'ask', '*': 'out'},
                      {'ask': (fm.FEATURES, tb.FEAT, 0, 6, 'feat')})
        ok &= check(t[:20], net.piles['out'], fm.f1(toks))
    return ok


def r1_of(t):
    return fm.records(fm.f1(tokens(t)), fm.R1)


def test_f2a(texts):
    ok = True
    for t in texts:
        rev = list(reversed(r1_of(t)))
        inp = fm.flat(fm.select(rev, [fm.KIND, fm.S, fm.WF]))
        net, st = run('after', 'after.cq', {'in': inp}, {'*': 'in'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], fm.flat(fm.f2a(fm.select(rev, [fm.KIND, fm.S, fm.WF]))))
    return ok


def test_f2b(texts):
    ok = True
    for t in texts:
        rev = list(reversed(r1_of(t)))
        a = fm.f2a(fm.select(rev, [fm.KIND, fm.S, fm.WF]))
        recs = [x + y[:2] for x, y in zip(fm.select(rev, [fm.KIND, fm.WF, fm.CLS9]), a)]
        net, st = run('ahead', 'ahead.cq', {'in': fm.flat(recs)}, {'*': 'in'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], fm.flat(fm.f2b(recs)))
    return ok


def test_f2c(texts):
    ok = True
    for t in texts:
        rev = list(reversed(r1_of(t)))
        recs = fm.select(rev, [fm.PC, fm.KIND])
        net, st = run('next', 'next.cq', {'in': fm.flat(recs)}, {'*': 'in', 'gts': 'ft', 'gte': 'ft', 'gasp': 'ft'},
                      {'ask': 'ask', '*': 'out'}, {'ask': (fm.FEATURES, tb.FEAT, tb.F_TS, 3, 'ft')})
        ok &= check(t[:20], net.piles['out'], fm.flat(fm.f2c(recs)))
    return ok


def decks(t):
    return fm.front_decks(tokens(t))


def test_stress(texts):
    ok = True
    for t in texts:
        d = decks(t)
        recs = [x + y + z[1:2] for x, y, z in zip(fm.select(d['r1'], [fm.KIND, fm.S, fm.WF]), d['a'], d['b'])]
        net, st = run('stress', 'stress.cq', {'in': fm.flat(recs)}, {'*': 'in'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['st']))
    return ok


def test_base(texts):
    ok = True
    for t in texts:
        d = decks(t)
        recs = [x + y[:1] for x, y in zip(fm.select(d['r1'], [fm.KIND, fm.INH, fm.MN, fm.PMS, fm.VLS]), d['st'])]
        net, st = run('base', 'base.cq', {'in': fm.flat(recs)}, {'*': 'in'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['bs']))
    return ok


def test_rules2(texts):
    ok = True
    for t in texts:
        d = decks(t)
        recs = [x + y[:1] + z[1:] + z[:1] + w[:1] for x, y, z, w in zip(fm.select(d['r1'], [fm.KIND, fm.WF, fm.LIQ]), d['a'], d['st'], d['b'])]
        net, st = run('rules2', 'rules2.cq', {'in': fm.flat(recs)}, {'*': 'in'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], d['fa'])
    return ok


def test_rules9(texts):
    ok = True
    for t in texts:
        d = decks(t)
        recs = [x + y[:1] + y[2:3] + z[2:3] for x, y, z in zip(fm.select(d['r1'], [fm.KIND]), d['b'], d['st'])]
        net, st = run('rules9', 'rules9.cq', {'in': fm.flat(recs)}, {'*': 'in'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], d['fb'])
    return ok


def test_mul(texts):
    ok = True
    for t in texts:
        d = decks(t)
        net, st = run('mul', 'mul.cq', {'xb': fm.flat(d['bs']), 'fa': d['fa'], 'fb': d['fb']},
                      {'la': 'fa', 'lb': 'fb', '*': 'xb'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['du']))
    return ok


def test_nframes(texts):
    ok = True
    for t in texts:
        d = decks(t)
        recs = [x + y for x, y in zip(fm.select(d['r1'], [fm.KIND]), d['du'])]
        net, st = run('nframes', 'nframes.cq', {'in': fm.flat(recs)}, {'*': 'in'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['n']))
    return ok


def test_back(texts):
    ok = True
    for t in texts:
        d = decks(t)
        recs = [x + y[4:5] for x, y in zip(fm.select(d['r1'], [fm.PC, fm.KIND, fm.VLS]), d['c'])]
        net, st = run('back', 'back.cq', {'in': fm.flat(recs)}, {'*': 'in'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['bk']))
    return ok
