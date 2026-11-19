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


def test_sum(texts):
    ok = True
    for t in texts:
        d = decks(t)
        recs = [x + y[:1] + z for x, y, z in zip(fm.select(d['r1'], [fm.KIND, fm.SEND]), d['st'], d['n'])]
        net, st = run('sum', 'sum.cq', {'in': fm.flat(recs)}, {'*': 'in'}, {'*': 'out'})
        want = fm.flat(fm.f4_sum(recs))
        info = {}
        fr.phonemes_to_cards(tokens(t), info)
        ok &= check(t[:20] + ' ref', want, fm.flat(info['sums']))
        ok &= check(t[:20], net.piles['out'], want)
    return ok


def comp(t):
    return fm.compose(tokens(t))[1]


def test_framer(texts):
    ok = True
    for t in texts:
        d = comp(t)
        recs = [n + x for n, x in zip(d['n'], fm.select(d['r1'], [fm.SEND]))]
        net, st = run('framer', 'framer.cq', {'in': fm.flat(recs)}, {'*': 'in'}, {'up': 'up', 'ul': 'ul', '*': 'out'})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['fl']))
        ok &= check(t[:20] + ' u', net.piles['up'], d['us']) and check(t[:20] + ' u2', net.piles['ul'], d['us'])
    return ok


def test_closure(texts):
    ok = True
    for t in texts:
        d = comp(t)
        recs = [x + n for x, n in zip(fm.select(d['r1'], [fm.PC, fm.KIND]), d['n'])]
        net, st = run('closure', 'closure.cq', {'in': fm.flat(recs)}, {'gci': 'ft', 'gct': 'ft', '*': 'in'},
                      {'ask': 'ask', '*': 'out'}, {'ask': (fm.FEATURES, tb.FEAT, tb.F_CINH, 2, 'ft')})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['cl']))
    return ok


def test_main(texts):
    ok = True
    for t in texts:
        d = comp(t)
        recs = [x + c[3:5] + c[0:1] for x, c in zip(fm.select(d['r1'], [fm.PC, fm.KIND]), d['c'])]
        net, st = run('main', 'main.cq', {'in': fm.flat(recs)}, {'gv': 'ft', 'gn': 'ft', 'ga': 'ft', 'gb': 'fb', '*': 'in'},
                      {'ask': 'ask', 'askb': 'askb', '*': 'out'},
                      {'ask': (fm.FEATURES, tb.FEAT, tb.F_VOICED, 3, 'ft'), 'askb': (fm.FEATURES, tb.FEAT, tb.F_BACK, 1, 'fb')})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['mn']))
    return ok


def test_edge(texts):
    ok = True
    for t in texts:
        d = comp(t)
        recs = [x + n + bk[2:4] for x, n, bk in zip(fm.select(d['r1'], [fm.PC, fm.KIND]), d['n'], d['bk'])]
        net, st = run('edge', 'edge.cq', {'in': fm.flat(recs)}, {'g1': 'ft', 'g2': 'ft', 'g3': 'ft', 'g4': 'ft', 'g5': 'ft', '*': 'in'},
                      {'ask': 'ask', '*': 'out'}, {'ask': (fm.FEATURES, tb.FEAT, tb.F_ASP, 5, 'ft')})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['ed']))
    return ok


def test_choose(texts):
    ok = True
    for t in texts:
        d = comp(t)
        seg = [n + c + m + e for n, c, m, e in zip(d['n'], d['cl'], d['mn'], d['ed'])]
        frm = [[f[0], f[1], f[4]] for f in d['fl']]
        net, st = run('choose', 'choose.cq', {'seg': fm.flat(seg), 'frm': fm.flat(frm)},
                      {'fj': 'frm', 'fu': 'frm', 'fe': 'frm', '*': 'seg'}, {'ls': 'lv', 'lv': 'lv', '*': 'out'})
        ko, lv = d['ko'], d['lv']
        want = fm.flat([[k[0], k[1], k[2], s[6] if not (k[0] == 0 and k[1] == 0) else s[6]] for k, s in zip(ko, [[0]*7]*len(ko))])
        ok &= check(t[:20] + ' lv', net.piles['lv'], fm.flat(lv))
        got = fm.records(net.piles['out'], 4)
        ok &= check(t[:20] + ' ab', [g[:3] for g in got], [k[:3] for k in ko])
        d['g'] = [g[3] for g in got]
    return ok


def test_glides(texts):
    ok = True
    for t in texts:
        d = comp(t)
        # choose's output, as the reference makes it: a b uu g
        segs = d['segs']
        abug = []
        fi = 0
        for n, c, ma, mb, uon, vm, gl, cf, af, pte, nts in segs:
            for _ in range(n):
                j = d['fl'][fi][0]
                g = 0 if (j < c or (j == 0 and af)) else gl
                k = d['ko'][fi]
                abug.append(k[:3] + [g]); fi += 1
        frm = [a + [f[2], f[3]] for a, f in zip(abug, d['fl'])]
        seg = [[s[0], s[9], s[10]] for s in segs]
        net, st = run('glides', 'glides.cq', {'seg': fm.flat(seg), 'frm': fm.flat(frm)},
                      {'ca': 'frm', 'cb': 'frm', 'cu': 'frm', 'cg': 'frm', 'fl': 'frm', 'fr': 'frm', '*': 'seg'}, {'*': 'out'})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['ko']))
    return ok


def test_glidea(texts):
    ok = True
    for t in texts:
        d = comp(t)
        recs = [k[:3] for k in d['ko']]
        net, st = run('glidea', 'glidea.cq', {'in': fm.flat(recs)}, {'lp': 'fa', 'gg': 'fa', 'gb': 'fb', 'gb2': 'fb', '*': 'in'},
                      {'aska': 'aska', 'askb': 'askb', 'og': 'g', '*': 'out'},
                      {'aska': (fm.FILTERS, 11, 0, 11, 'fa'), 'askb': (fm.FILTERS, 11, 0, 11, 'fb')})
        want = []
        for a, b, u in recs:
            A, B = fm.frec(a), fm.frec(b)
            want += [fr.blend(x, y, u) for x, y in zip(A[:10], B[:10])]
        ok &= check(t[:20], net.piles['out'], want)
        ok &= check(t[:20] + ' G', net.piles['g'], d['gs'])
        d['kp'] = want
    return ok


def test_glideb(texts):
    ok = True
    for t in texts:
        d = comp(t)
        kp = []
        for a, b, u, gn, go, w in d['ko']:
            A, B = fm.frec(a), fm.frec(b)
            kp += [fr.blend(x, y, u) for x, y in zip(A[:10], B[:10])]
        recs = [k[3:] for k in d['ko']]
        net, st = run('glideb', 'glideb.cq', {'in': fm.flat(recs), 'kp': kp},
                      {'lp': 'fx', 'gg': 'fx', 'gy': 'fy', 'gy2': 'fy', 'gk': 'kp', '*': 'in'},
                      {'askn': 'askn', 'asko': 'asko', '*': 'out'},
                      {'askn': (fm.FILTERS, 11, 0, 11, 'fx'), 'asko': (fm.FILTERS, 11, 0, 11, 'fy')})
        ok &= check(t[:20], net.piles['out'], fm.flat(d['ks']))
    return ok


def lev_inputs(d):
    segs = [x[:1] + y[:1] + n + c[1:2] + bk[1:2] + c[2:3] for x, y, n, c, bk in
            zip(fm.select(d['r1'], [fm.KIND]), d['st'], d['n'], d['c'], d['bk'])]
    return segs


def test_level(texts):
    ok = True
    for t in texts:
        d = comp(t)
        segs = lev_inputs(d)
        ch = fm.f8_chain(segs, d['lv'], d['us'], d['gs'], d['ps'])
        ok &= check(t[:20] + ' chain=lev', fm.flat(ch['m4']), fm.flat(d['lev']))
        # lsel
        sl = [[s[0], s[2], s[3], s[4], s[5]] for s in segs]
        net, st = run('lsel', 'lsel.cq', {'seg': fm.flat(sl), 'sv': fm.flat(d['lv'])}, {'gs': 'sv', 'gv': 'sv', 'gl': 'ft', '*': 'seg'},
                      {'ask': 'ask', '*': 'out'}, {'ask': (fm.FEATURES, tb.FEAT, tb.F_LOUD, 1, 'ft')})
        ok &= check(t[:20] + ' lsel', net.piles['out'], fm.flat(ch['ls']))
        # vsel
        sv3 = [x + [u] for x, u in zip(d['lv'], d['us'])]
        net, st = run('vsel', 'vsel.cq', {'seg': fm.flat([[s[0], s[1], s[2]] for s in segs]), 'sv': fm.flat(sv3)},
                      {'gs': 'sv', 'gv': 'sv', 'gu': 'sv', '*': 'seg'}, {'m3': 'o3', 'oy3': 'o3', '*': 'o2'})
        ok &= check(t[:20] + ' vsel2', net.piles['o2'], fm.flat([v[:2] for v in ch['vs']]))
        ok &= check(t[:20] + ' vsel3', net.piles['o3'], fm.flat([v[2:] for v in ch['vs']]))
        # psel
        net, st = run('psel', 'psel.cq', {'sv': fm.flat([x + [p] for x, p in zip(d['lv'], d['ps'])])}, {'*': 'sv'}, {'*': 'out'})
        ok &= check(t[:20] + ' psel', net.piles['out'], fm.flat(ch['pss']))
        # mulx, each stage
        for a, b, m in (([x + [g] for x, g in zip(d['lv'], d['gs'])], 'ls', 'm1'), (ch['m1'], None, 'm2'), (ch['m2'], None, 'm3'), (ch['m3'], 'pss', 'm4')):
            modes = ch[b] if b else [v[:2] if m == 'm2' else v[2:] for v in ch['vs']]
            net, st = run('mulx', 'mulx.cq', {'in': fm.flat(a), 'md': fm.flat(modes)}, {'gm': 'md', 'gy': 'md', '*': 'in'}, {'*': 'out'})
            ok &= check(t[:20] + ' ' + m, net.piles['out'], fm.flat(ch[m]))
    return ok


def test_asm(texts):
    ok = True
    for t in texts:
        d = comp(t)
        kc = fm.f9_kcarry(d['lv'], d['ks'])
        net, st = run('kcarry', 'kcarry.cq', {'sv': [x[0] for x in d['lv']], 'k': fm.flat(d['ks'])},
                      {'frm': 'sv', 'gx': 'k', '*': 'self'}, {'pz': 'self', 'wb': 'self', '*': 'out'})
        ok &= check(t[:20] + ' kcarry', net.piles['out'], fm.flat(kc))
        cards, _ = fm.compose(tokens(t))
        net, st = run('asm', 'asm.cq', {'lev': fm.flat(d['lev']), 'p': d['ps'], 'k': fm.flat(kc)},
                      {'gp': 'p', 'gk': 'k', '*': 'lev'}, {'*': 'out'})
        ok &= check(t[:20] + ' asm', net.piles['out'], cards)
    return ok


def test_pitch(texts):
    ok = True
    for t in texts:
        d = comp(t)
        r1 = d['r1']
        segs_d = [n + x for n, x in zip(d['n'], fm.select(r1, [fm.SEND]))]
        net, st = run('decl', 'decl.cq', {'seg': fm.flat(segs_d), 'sum': fm.flat(d['sums'])},
                      {'gl': 'sum', 'g2': 'sum', 'g3': 'sum', 'g4': 'sum', '*': 'seg'}, {'*': 'out'})
        # decl alone: 130 - q
        decl = []
        fi = si = 0; ns = True
        for n, send in segs_d:
            for _ in range(n):
                if ns:
                    L = d['sums'][si][0]; si += 1; q = qr = 0; ns = False
                decl.append(130 - q)
                if q < 30:
                    qr += 30
                    while qr >= L:
                        qr -= L; q += 1
                    q = min(q, 30)
            if send: ns = True
        ok &= check(t[:20] + ' decl', net.piles['out'], decl)
        segs_r = [x[:1] + y[:1] + n for x, y, n in zip(fm.select(r1, [fm.KIND]), d['st'], d['n'])]
        net, st = run('rise', 'rise.cq', {'seg': fm.flat(segs_r), 'u': d['us'], 'b': decl},
                      {'gu': 'u', 'gb': 'b', '*': 'seg'}, {'*': 'out'})
        ok &= check(t[:20] + ' rise', net.piles['out'], d['bases'])
        net, st = run('taily', 'taily.cq', {'seg': fm.flat(segs_d), 'sum': fm.flat(d['sums'])},
                      {'gl': 'sum', 'g2': 'sum', 'g3': 'sum', 'g4': 'sum', '*': 'seg'}, {'*': 'out'})
        ty = []
        fi = si = 0; ns = True
        for n, send in segs_d:
            for _ in range(n):
                if ns:
                    L, to, M, end = d['sums'][si]; si += 1; f = y = yr = 0; ns = False
                ty.append([y if (to >= 0 and f >= to) else -1, end])
                f += 1
                if to >= 0 and f > to and y < 100:
                    yr += 100
                    while yr >= M:
                        yr -= M; y += 1
                    y = min(y, 100)
            if send: ns = True
        ok &= check(t[:20] + ' taily', net.piles['out'], fm.flat(ty))
        net, st = run('tailf', 'tailf.cq', {'b': d['bases'], 'ty': fm.flat(ty)}, {'gy': 'ty', 'ge': 'ty', '*': 'b'}, {'*': 'out'})
        ok &= check(t[:20] + ' tailf', net.piles['out'], d['f0s'])
        net, st = run('period', 'period.cq', {'f': d['f0s']}, {'*': 'f'}, {'pa': 'pa', '*': 'out'})
        ok &= check(t[:20] + ' period', net.piles['out'], d['ps']) and check(t[:20] + ' period2', net.piles['pa'], d['ps'])
    return ok
