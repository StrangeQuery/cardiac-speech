"""The networks of machines, wired as the Rust host wires them (src/nets.rs)."""
import os
import cardiac

V = '../voice/'


FRAME = 13


def lattice(net, name, listing, coef, above, below):
    pattern = [(coef, 10)] + ([(above, 1)] + ([(below, 1)] if below else [])) * 20
    net.merge(name + '<', pattern)
    net.add(name, V + listing, name + '<', name)


def voice_box(net, frames_pile='frames', out_pile='out'):
    """The voice box as src/voice.rs wires it: frames_pile gets the frame cards (deal_frames), out_pile the
    output values."""
    net.merge('pairs', [(frames_pile, 1), (frames_pile + '2', 1)])
    net.add('interp', V + 'interp.cq', 'pairs', 'int')
    net.fan['int'] = ['int_p', 'int_k']
    net.collate('tosteps', [('int_p', 25, list(range(5)))])
    net.collate('toksteps', [('int_k', 25, list(range(3, 25)))])
    net.add('steps', V + 'steps.cq', 'tosteps', 'exc')
    net.add('ksteps', V + 'ksteps.cq', 'toksteps', 'kin')
    net.add('reduce', V + 'reduce.cq', 'kin', 'coef')
    net.deal['coef'] = (10, ['c1', 'c2', 'c3', 'c4', 'c5'])
    net.add('excite', V + 'excite.cq', 'exc', 'e')
    lattice(net, 'L1', 'lattice_top.cq', 'c1', 'e', 'b8')
    net.fan['L1'] = ['f9']
    for j, n in enumerate(['L2', 'L3', 'L4']):
        lattice(net, n, 'lattice.cq', 'c%d' % (j + 2), ['f9', 'f7', 'f5'][j], ['b6', 'b4', 'b2'][j])
        net.deal[n] = (1, [['b8', 'b6', 'b4'][j], ['f7', 'f5', 'f3'][j]])
    lattice(net, 'L5', 'lattice_bottom.cq', 'c5', 'f3', None)
    net.deal['L5'] = (1, ['b2', 'f0'])
    net.add('output', V + 'output.cq', 'f0', out_pile)


def deal_frames(net, deck, frames_pile='frames'):
    """The frame cards to the voice box: the deck with twelve blank cards after its end card, and the same from the
    second frame on."""
    whole = list(deck) + [0] * (FRAME - 1)
    net.put(frames_pile, whole)
    net.put(frames_pile + '2', whole[FRAME:])


FR = '../front/'
import table as tb                      # noqa: E402
import front_machines as fm             # noqa: E402

FEAT_TABLE = fm.FEATURES
FILT_TABLE = fm.FILTERS
GLIDE_TABLE, GLIDE_REC = fm.GLIDES, fm.GLIDE_REC


def recs(cards, size):
    return [cards[i:i + size] for i in range(0, len(cards), size)]


def flat(rs):
    return [c for r in rs for c in r]


def cols(rs, cs):
    return [[r[c] for c in cs] for r in rs]


AX = tb.CODE['AX']


def row(code, frm, count):
    return FEAT_TABLE[code * tb.FEAT + frm:code * tb.FEAT + frm + count]


def machine(net, name, listing, folder=FR):
    net.add(name, folder + listing, name + '<', name)


def fan(net, pile, readers):
    net.fan[pile] = ['%s>%s' % (pile, r) for r in readers]


def fetch(net, src, size, col, table, rec, frm, count, to):
    """Each card of column col of src's records names a record of table; its cards frm..frm+count go onto to."""
    net.collate(to + '?', [(src, size, [col])])
    net.fetch[to + '?'] = (table, rec, frm, count, to)


def rev(cards, size):
    return flat(list(reversed(recs(cards, size))))


def front(tokens, steps=None, taps=None):
    """Phonemes to frame cards on the dev emulator, in five phases as the host runs them (src/front.rs). Returns the
    frame cards and what is left on the piles; steps gets each machine's instruction count, taps what each
    machine punched."""
    F = fm
    R1 = F.R1
    K, S_, WF, PC, INH, MN, PMS, VLS, LIQ, SEND, CLS9 = (F.KIND, F.S, F.WF, F.PC, F.INH, F.MN, F.PMS, F.VLS, F.LIQ,
                                                          F.SEND, F.CLS9)
    steps = {} if steps is None else steps
    taps = {} if taps is None else taps

    def done(net):
        net.run()
        for n, m in net.machines.items():
            steps[n] = m.steps
        taps.update(net.punched)
    # phase 1: the segments
    net = cardiac.Net()
    net.add('feat', FR + 'feat.cq', 'tokens', 'feat')
    fan(net, 'feat', ['rec', 'row'])
    fetch(net, 'feat>row', 5, PC, FEAT_TABLE, tb.FEAT, 0, 6, 'feat_row')
    net.collate('r1', [('feat>rec', 5, list(range(5))), ('feat_row', 6, list(range(6)))])
    net.put('tokens', tokens)
    done(net)
    r1 = net.piles['r1']
    # phase 2: last first
    rv = rev(r1, R1)
    net = cardiac.Net()
    for r in ('after', 'ahead', 'next', 'next_row'):
        net.put('r>' + r, rv)
    machine(net, 'after', 'after.cq')
    net.collate('after<', [('r>after', R1, [K, S_, WF])])
    fan(net, 'after', ['out', 'ahead'])
    net.fan['after>out'] = ['A']
    machine(net, 'ahead', 'ahead.cq')
    net.collate('ahead<', [('r>ahead', R1, [K, WF, CLS9]), ('after>ahead', 3, [0, 1])])
    net.fan['ahead'] = ['B']
    machine(net, 'next', 'next.cq')
    net.put('next<', row(AX, tb.F_ASP, 1))
    fetch(net, 'r>next_row', R1, PC, FEAT_TABLE, tb.FEAT, tb.F_TS, 3, 'next_row')
    net.collate('next<', [('r>next', R1, [PC, K]), ('next_row', 3, [0, 1, 2])])
    net.fan['next'] = ['C']
    done(net)
    A, B, C = rev(net.piles['A'], 3), rev(net.piles['B'], 3), rev(net.piles['C'], 6)
    # phase 3: forward, a record a segment
    net = cardiac.Net()
    for name, deck, readers in (
            ('r1', r1, ['stress', 'base', 'rules2', 'rules5', 'rules9', 'nframes', 'back', 'sum', 'closure',
                        'closure_row', 'main', 'main_row', 'edge', 'edge_row']),
            ('A', A, ['stress', 'rules5']), ('B', B, ['stress', 'rules5', 'rules9']),
            ('C', C, ['back', 'main', 'main_row', 'loud', 'loud_adjv', 'loud_nextv'])):
        for r in readers:
            net.put('%s>%s' % (name, r), deck)
    machine(net, 'stress', 'stress.cq')
    net.collate('stress<', [('r1>stress', R1, [K, S_, WF]), ('A>stress', 3, [0, 1, 2]), ('B>stress', 3, [1])])
    fan(net, 'stress', ['base', 'rules2', 'rules5', 'rules9', 'sum', 'out'])
    machine(net, 'base', 'base.cq')
    net.collate('base<', [('r1>base', R1, [K, INH, MN, PMS, VLS]), ('stress>base', 4, [0])])
    machine(net, 'rules2', 'rules2.cq')
    net.collate('rules2<', [('r1>rules2', R1, [K, LIQ]), ('stress>rules2', 4, [1, 2])])
    machine(net, 'rules5', 'rules5.cq')
    net.collate('rules5<', [('r1>rules5', R1, [K, WF]), ('A>rules5', 3, [0]), ('stress>rules5', 4, [3, 0]),
                            ('B>rules5', 3, [0])])
    machine(net, 'rules9', 'rules9.cq')
    net.collate('rules9<', [('r1>rules9', R1, [K]), ('B>rules9', 3, [0, 2]), ('stress>rules9', 4, [2])])
    machine(net, 'mul', 'mul.cq')
    net.put('mul<', [fm.fr.RATE])
    net.collate('mul<', [('base', 2, [0, 1]), ('rules2', 4, list(range(4))), ('rules5', 4, list(range(4))),
                         ('rules9', 4, list(range(4)))])
    machine(net, 'nframes', 'nframes.cq')
    net.collate('nframes<', [('r1>nframes', R1, [K]), ('mul', 1, [0])])
    fan(net, 'nframes', ['sum', 'closure', 'edge', 'out'])
    machine(net, 'back', 'back.cq')
    net.collate('back<', [('r1>back', R1, [PC, K, VLS]), ('C>back', 6, [4])])
    fan(net, 'back', ['edge', 'loud', 'loud_prevv', 'out'])
    machine(net, 'sum', 'sum.cq')
    net.collate('sum<', [('r1>sum', R1, [K, SEND]), ('stress>sum', 4, [0]), ('nframes>sum', 1, [0])])
    machine(net, 'closure', 'closure.cq')
    fetch(net, 'r1>closure_row', R1, PC, FEAT_TABLE, tb.FEAT, tb.F_CINH, 2, 'closure_row')
    net.collate('closure<', [('r1>closure', R1, [PC, K]), ('nframes>closure', 1, [0]), ('closure_row', 2, [0, 1])])
    machine(net, 'main', 'main.cq')
    fetch(net, 'r1>main_row', R1, PC, FEAT_TABLE, tb.FEAT, tb.F_VOICED, 3, 'main_row')
    fetch(net, 'C>main_row', 6, 0, FEAT_TABLE, tb.FEAT, tb.F_BACK, 1, 'main_next')
    net.collate('main<', [('r1>main', R1, [PC, K]), ('C>main', 6, [3, 4, 0]), ('main_row', 3, [0, 1, 2]),
                          ('main_next', 1, [0])])
    machine(net, 'edge', 'edge.cq')
    fetch(net, 'r1>edge_row', R1, PC, FEAT_TABLE, tb.FEAT, tb.F_ASP, 5, 'edge_row')
    net.collate('edge<', [('r1>edge', R1, [PC, K]), ('nframes>edge', 1, [0]), ('back>edge', 4, [2, 3]),
                          ('edge_row', 5, list(range(5)))])
    machine(net, 'loud', 'loud.cq')
    net.put('loud<', row(AX, tb.F_LOUD, 1))
    fetch(net, 'C>loud_adjv', 6, 1, FEAT_TABLE, tb.FEAT, tb.F_LOUD, 1, 'loud_adjv')
    fetch(net, 'back>loud_prevv', 4, 1, FEAT_TABLE, tb.FEAT, tb.F_LOUD, 1, 'loud_prevv')
    fetch(net, 'C>loud_nextv', 6, 2, FEAT_TABLE, tb.FEAT, tb.F_LOUD, 1, 'loud_nextv')
    net.collate('loud<', [('C>loud', 6, [1]), ('back>loud', 4, [1]), ('loud_adjv', 1, [0]), ('loud_prevv', 1, [0]),
                          ('loud_nextv', 1, [0])])
    for name, frm in (('n', 'nframes>out'), ('st', 'stress>out'), ('bk', 'back>out'), ('sm', 'sum'), ('cl', 'closure'),
                      ('mn', 'main'), ('ed', 'edge'), ('ld', 'loud')):
        net.fan[frm] = ['out:' + name]
    done(net)
    d = {k: net.piles.get('out:' + k, []) for k in ('n', 'st', 'bk', 'sm', 'cl', 'mn', 'ed', 'ld')}
    # phase 4: the sentences' summaries, last first
    net = cardiac.Net()
    net.put('fill<', rev(d['sm'], 5))
    machine(net, 'fill', 'fill.cq')
    done(net)
    fl = rev(net.piles['fill'], 4)
    # phase 5: frame by frame
    net = cardiac.Net()
    for name, deck, readers in (
            ('r1', r1, ['framer', 'sents', 'spreadb']), ('C', C, ['spreadb']),
            ('n', d['n'], ['framer', 'sents', 'spreada', 'spreadb', 'spreadc']), ('st', d['st'], ['spreadb']),
            ('bk', d['bk'], ['spreadb']), ('cl', d['cl'], ['spreada']), ('mn', d['mn'], ['spreada']),
            ('ed', d['ed'], ['spreada']), ('ld', d['ld'], ['spreadc']), ('fl', fl, ['spreadc'])):
        for r in readers:
            net.put('%s>%s' % (name, r), deck)
    FRW, CH = 7, 6
    machine(net, 'framer', 'framer.cq')
    net.collate('framer<', [('n>framer', 1, [0]), ('r1>framer', R1, [SEND])])
    fan(net, 'framer', ['choose', 'glides', 'rise', 'vsel'])
    machine(net, 'sents', 'sents.cq')
    net.collate('sents<', [('n>sents', 1, [0]), ('r1>sents', R1, [SEND])])
    fan(net, 'sents', ['decl', 'taily'])
    net.add('spreada', FR + 'spread.cq', 'spreada<', 'spreada')
    net.put('spreada<', [8])
    net.collate('spreada<', [('n>spreada', 1, [0]), ('cl>spreada', 1, [0]), ('mn>spreada', 5, list(range(5))),
                             ('ed>spreada', 2, [0, 1])])
    net.add('spreadb', FR + 'spread.cq', 'spreadb<', 'spreadb')
    net.put('spreadb<', [4])
    net.collate('spreadb<', [('n>spreadb', 1, [0]), ('bk>spreadb', 4, [0]), ('C>spreadb', 6, [5]),
                             ('r1>spreadb', R1, [K]), ('st>spreadb', 4, [0])])
    fan(net, 'spreadb', ['glides', 'rise', 'lsel', 'vsel'])
    net.add('spreadc', FR + 'spread.cq', 'spreadc<', 'spreadc')
    net.put('spreadc<', [6])
    net.collate('spreadc<', [('n>spreadc', 1, [0]), ('fl>spreadc', 4, list(range(4))), ('ld>spreadc', 2, [0, 1])])
    fan(net, 'spreadc', ['decl', 'taily', 'lsel'])
    machine(net, 'choose', 'choose.cq')
    net.collate('choose<', [('framer>choose', FRW, [0, 1, 4]), ('spreada', 8, list(range(8)))])
    fan(net, 'choose', ['glides', 'lsel', 'vsel', 'psel', 'mulx1', 'kcarry', 'next'])
    machine(net, 'glides', 'glides.cq')
    net.collate('glides<', [('choose>glides', CH, [0, 1, 2, 3]), ('framer>glides', FRW, [2, 3]),
                            ('spreadb>glides', 4, [0, 1])])
    fan(net, 'glides', ['glidea', 'glideb', 'gnorm'])
    machine(net, 'glidea', 'glidea.cq')
    net.collate('glidea_abu', [('glides>glidea', 6, [0, 1, 2])])
    net.merge('glidea<', [('glidea_abu', 3)] + [('rowa', 1), ('rowb', 1)] * 11)
    net.split['glidea'] = [('glidea?a', 1), ('glidea?b', 1), ('glidea>kg', 11)]
    net.fetch['glidea?a'] = (FILT_TABLE, 11, 0, 11, 'rowa')
    net.fetch['glidea?b'] = (FILT_TABLE, 11, 0, 11, 'rowb')
    fan(net, 'glidea>kg', ['k', 'g'])
    machine(net, 'glideb', 'glideb.cq')
    net.collate('glideb_w', [('glides>glideb', 6, [3, 4, 5])])
    net.collate('glideb_k', [('glidea>kg>k', 11, list(range(10)))])
    net.merge('glideb<', [('glideb_w', 3)] + [('rown', 1), ('rowo', 1), ('glideb_k', 1)] * 10 + [('rown', 1), ('rowo', 1)])
    net.split['glideb'] = [('glideb?n', 1), ('glideb?o', 1), ('glideb>k', 10)]
    net.fetch['glideb?n'] = (FILT_TABLE, 11, 0, 11, 'rown')
    net.fetch['glideb?o'] = (FILT_TABLE, 11, 0, 11, 'rowo')
    machine(net, 'decl', 'decl.cq')
    net.collate('decl<', [('sents>decl', 1, [0]), ('spreadc>decl', 6, [0])])
    machine(net, 'rise', 'rise.cq')
    net.collate('rise<', [('framer>rise', FRW, [5]), ('spreadb>rise', 4, [2, 3]), ('decl', 1, [0])])
    machine(net, 'taily', 'taily.cq')
    net.collate('taily<', [('sents>taily', 1, [0]), ('spreadc>taily', 6, [1, 2, 3])])
    machine(net, 'tailf', 'tailf.cq')
    net.collate('tailf<', [('rise', 1, [0]), ('taily', 2, [0, 1])])
    machine(net, 'period', 'period.cq')
    net.fan['tailf'] = ['period<']
    net.deal['period'] = (1, ['period>psel', 'period>asm'])
    machine(net, 'lsel', 'lsel.cq')
    net.collate('lsel<', [('choose>lsel', CH, [4, 5]), ('spreadb>lsel', 4, [2]), ('spreadc>lsel', 6, [4, 5])])
    machine(net, 'vsel', 'vsel.cq')
    net.collate('vsel<', [('choose>vsel', CH, [4, 5]), ('framer>vsel', FRW, [6]), ('spreadb>vsel', 4, [2, 3])])
    fan(net, 'vsel', ['mulx2', 'mulx3'])
    machine(net, 'psel', 'psel.cq')
    net.collate('psel<', [('choose>psel', CH, [4, 5]), ('period>psel', 1, [0])])
    machine(net, 'gnorm', 'gnorm.cq')
    net.collate('gnorm_f', [('glides>gnorm', 6, [3, 4, 5])])
    net.merge('gnorm<', [('gnorm_f', 3), ('grec', GLIDE_REC)])
    net.split['gnorm'] = [('gnorm?', 1), ('gnorm>mulx5', 2)]
    net.fetch['gnorm?'] = (GLIDE_TABLE, GLIDE_REC, 0, GLIDE_REC, 'grec')
    for k, src in ((1, None), (2, ('vsel>mulx2', 4, [0, 1])), (3, ('vsel>mulx3', 4, [2, 3])), (4, ('psel', 2, [0, 1])),
                   (5, ('gnorm>mulx5', 2, [0, 1]))):
        net.add('mulx%d' % k, FR + 'mulx.cq', 'mulx%d<' % k, 'mulx%d' % k)
        if k == 1:
            net.collate('mulx1<', [('choose>mulx1', CH, [4, 5]), ('glidea>kg>g', 11, [10]), ('lsel', 2, [0, 1])])
        else:
            net.collate('mulx%d<' % k, [('mulx%d' % (k - 1), 3, [0, 1, 2]), src])
    machine(net, 'kcarry', 'kcarry.cq')
    net.collate('kcarry<', [('choose>kcarry', CH, [4]), ('glideb>k', 10, list(range(10)))])
    machine(net, 'asm', 'asm.cq')
    net.collate('asm_next', [('choose>next', CH, [4, 5])])
    net.after['asm_next'] = (2, 'asm_next2')
    net.merge('asm<', [('mulx5', 3), ('period>asm', 1), ('kcarry', 10), ('asm_next2', 2)])
    done(net)
    left = {p: len(q) for p, q in net.piles.items() if q and p != 'asm'}
    return net.piles['asm'], left


TX = '../text/'


def text_decks():
    import text_tables as tt
    rd = lambda n: [int(v) for v in open(os.path.join(tt.TEXT, n + '.cards')).read().split()]
    return {n: rd(n) for n in ('ascii', 'numbers', 'letters', 'exphon', 'function', 'exception_words', 'rules_left',
                               'rules_right', 'rules_phonemes')}


def text(chars, steps=None, taps=None, decks=None):
    """Text (its characters' codes) to phoneme cards on the dev emulator, as the host wires it (src/text.rs).
    Returns the phoneme cards; steps gets each machine's instruction count, taps what each machine punched."""
    D = decks or text_decks()
    steps = {} if steps is None else steps
    taps = {} if taps is None else taps
    net = cardiac.Net()
    machine(net, 'scan', 'scan.cq', TX)
    net.fan['chars2'] = ['t_raw', 't_asc?']
    net.fetch['t_asc?'] = (D['ascii'], 2, 0, 2, 't_asc')
    net.merge('scan<', [('t_raw', 1), ('t_asc', 2)])
    for frm, to in (('scan', 'numd'), ('numd', 'unpack'), ('unpack', 'numw'), ('numw', 'say3')):
        net.fan[frm] = [to + '<']
        machine(net, to, to + '.cq', TX)
    for k, (frm, t, table, size, to) in enumerate((('say3', 700, 'numbers', 10, 'numf'),
                                                   ('spell', 100, 'letters', 8, 'names')), 1):
        a = 'ask%d' % k
        net.put(a + '<', [t])
        net.fan[frm] = [a + '<']
        net.add(a, TX + 'ask.cq', a + '<', a)
        net.split[a] = [(a + '?', 1), (a + 'c', 1)]
        net.fetch[a + '?'] = (D[table], size, 0, size, a + 'r')
        machine(net, to, to + '.cq', TX)
        net.merge(to + '<', [(a + 'c', 1), (a + 'r', size)])
        if k == 1:
            net.fan['numf'] = ['spcls<']
            machine(net, 'spcls', 'spcls.cq', TX)
            net.fan['spcls'] = ['spell<']
            machine(net, 'spell', 'spell.cq', TX)
    net.fan['names'] = ['items<']
    machine(net, 'items', 'items.cq', TX)
    fan(net, 'items', ['excl', 'excx', 'excp'])
    machine(net, 'excl', 'excl.cq', TX)
    net.merge('excl<', [('items>excl', 17), ('deck:f', len(D['function']))], {'f': D['function']})
    machine(net, 'excx', 'excx.cq', TX)
    net.merge('excx<', [('items>excx', 17), ('deck:x', len(D['exception_words']))], {'x': D['exception_words']})
    fan(net, 'excx', ['excp', 'ask'])
    net.fetch['excx>ask'] = (D['exphon'], 12, 0, 12, 't_xph')
    machine(net, 'excp', 'excp.cq', TX)
    net.collate('excp<', [('excl', 1, [0]), ('excx>excp', 1, [0]), ('items>excp', 17, list(range(17))),
                          ('t_xph', 12, list(range(12)))])
    net.fan['excp'] = ['letters<']
    machine(net, 'letters', 'letters.cq', TX)
    fan(net, 'letters', ['left', 'left?', 'right', 'right?', 'pick', 'pick?'])
    word = [1] + list(range(4, 19))
    for name, table in (('left', 'rules_left'), ('right', 'rules_right')):
        size = len(D[table]) // 27
        net.collate('t_%sw' % name, [('letters>' + name, 19, word)])
        net.collate('t_%s?' % name, [('letters>%s?' % name, 19, [0])])
        net.fetch['t_%s?' % name] = (D[table], size, 0, size, 't_%sr' % name)
        machine(net, name, name + '.cq', TX)
        net.merge(name + '<', [('t_%sw' % name, len(word)), ('t_%sr' % name, size)])
    machine(net, 'first', 'first.cq', TX)
    net.put('first<', [D['rules_left'].count(-2) // 27])
    net.merge('first<', [('left', 1), ('right', 1)])
    size = len(D['rules_phonemes']) // 27
    net.collate('t_pickw', [('letters>pick', 19, [1, 2, 3, 0] + list(range(4, 19)))])
    net.collate('t_pick?', [('letters>pick?', 19, [0])])
    net.fetch['t_pick?'] = (D['rules_phonemes'], size, 0, size, 't_pickr')
    machine(net, 'pick', 'pick.cq', TX)
    net.merge('pick<', [('t_pickw', 19), ('first', 1), ('t_pickr', size)])
    for frm, to in (('pick', 'posta'), ('posta', 'postb'), ('postb', 'posth'), ('posth', 'postc'), ('postc', 'join')):
        net.fan[frm] = [to + '<']
        machine(net, to, to + '.cq', TX)
    net.put('scan<', list(chars) + [-1])
    net.put('chars2', list(chars))
    net.put('t_raw', [-1])
    net.run()
    for n, m in net.machines.items():
        steps[n] = m.steps
    taps.update(net.punched)
    return net.piles['join']
