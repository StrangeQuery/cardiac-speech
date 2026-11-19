"""The networks of machines, wired as the Rust host wires them (src/nets.rs)."""
import cardiac

V = '../voice/'


def voice_box(net, frames_pile='frames', out_pile='out'):
    net.add('interp', V + 'interp.cq', {3: frames_pile, 6: frames_pile, 13: frames_pile, 27: frames_pile, '*': 'iself'},
            {7: 'iself', 35: 'iself', '*': 'tosteps'})
    net.add('steps', V + 'steps.cq', {3: 'tosteps', 7: 'tosteps', '*': 'sself'},
            {18: 'exc', 20: 'exc', 28: 'exc', 38: 'kin', 40: 'kin', '*': 'sself'})
    net.add('reduce', V + 'reduce.cq', {'*': 'kin'}, {'*': 'coef'})
    net.deal['coef'] = (10, ['c1', 'c2', 'c3', 'c4', 'c5'])
    net.add('excite', V + 'excite.cq', {'*': 'exc'}, {'*': 'e'})
    net.add('L1', V + 'lattice_top.cq', {'go': 'e', 'getb': 'b8', '*': 'c1'}, {'*': 'f9'})
    for j, n in enumerate(['L2', 'L3', 'L4']):
        net.add(n, V + 'lattice.cq', {'go': ['f9', 'f7', 'f5'][j], 'getb': ['b6', 'b4', 'b2'][j], '*': 'c%d' % (j + 2)},
                {'loop': ['b8', 'b6', 'b4'][j], '*': ['f7', 'f5', 'f3'][j]})
    net.add('L5', V + 'lattice_bottom.cq', {'go': 'f3', '*': 'c5'}, {'loop': 'b2', '*': 'f0'})
    net.add('output', V + 'output.cq', {'*': 'f0'}, {'*': out_pile})
    for p in ('c1', 'c2', 'c3', 'c4', 'c5', frames_pile, out_pile):
        net.piles.setdefault(p, [])


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


def front(tokens, steps=None):
    """Phonemes to frame cards on the dev emulator, in three phases as the host runs them."""
    F = fm
    # phase 1: the segments
    net = cardiac.Net()
    net.add('feat', FR + 'feat.cq', {'cp': 'f1t', '*': 'tokens'}, {'rec': 'f1ask', '*': 'r1'})
    net.fetch['f1ask'] = (FEAT_TABLE, tb.FEAT, 0, 6, 'f1t')
    net.piles['f1t'] = []
    net.put('tokens', tokens)
    net.run()
    tot = {'feat': net.machines['feat'].steps}
    r1 = recs(net.piles['r1'], F.R1)
    # phase 2: last first
    rev = list(reversed(r1))
    net = cardiac.Net()
    net.add('after', FR + 'after.cq', {'*': 'pa'}, {'*': 'aout'})
    net.add('ahead', FR + 'ahead.cq', {'*': 'pb'}, {'*': 'bout'})
    net.add('next', FR + 'next.cq', {'gts': 'nt', 'gte': 'nt', 'gasp': 'nt', '*': 'pc'}, {'ask': 'nask', '*': 'cout'})
    net.fetch['nask'] = (FEAT_TABLE, tb.FEAT, tb.F_TS, 3, 'nt')
    net.piles['nt'] = []
    net.fan['aout'] = ['A', 'a2b']
    net.put('pa', flat(cols(rev, [F.KIND, F.S, F.WF])))
    net.put('pb0', flat(cols(rev, [F.KIND, F.WF, F.CLS9])))
    net.collates.append(('pb', [('pb0', 3, [0, 1, 2]), ('a2b', 3, [0, 1])]))
    net.put('pc', flat(cols(rev, [F.PC, F.KIND])))
    net.run()
    for n, m in net.machines.items():
        tot[n] = m.steps
    A = list(reversed(recs(net.piles['A'], 3)))
    B = list(reversed(recs(net.piles['bout'], 3)))
    C = list(reversed(recs(net.piles['cout'], 6)))
    # phase 3: forward, to the frames
    net = cardiac.Net()
    K, S_, WF, PC, INH, MN, PMS, VLS, LIQ, SEND = F.KIND, F.S, F.WF, F.PC, F.INH, F.MN, F.PMS, F.VLS, F.LIQ, F.SEND
    net.add('stress', FR + 'stress.cq', {'*': 'st_in'}, {'*': 'st'})
    net.put('st_in', flat([cols([r], [K, S_, WF])[0] + a + b[1:2] for r, a, b in zip(r1, A, B)]))
    net.fan['st'] = ['st_base', 'st_r2', 'st_r9', 'st_sum', 'st_rise', 'st_vsel']
    net.add('base', FR + 'base.cq', {'*': 'base_in'}, {'*': 'xb'})
    net.put('base_s', flat(cols(r1, [K, INH, MN, PMS, VLS])))
    net.collates.append(('base_in', [('base_s', 5, [0, 1, 2, 3, 4]), ('st_base', 4, [0])]))
    net.add('rules2', FR + 'rules2.cq', {'*': 'r2_in'}, {'*': 'fa'})
    net.put('r2_s', flat([cols([r], [K, WF, LIQ])[0] + a[:1] for r, a in zip(r1, A)]))
    net.put('r2_b', flat(cols(B, [0])))
    net.collates.append(('r2_in', [('r2_s', 4, [0, 1, 2, 3]), ('st_r2', 4, [1, 2, 3, 0]), ('r2_b', 1, [0])]))
    net.add('rules9', FR + 'rules9.cq', {'*': 'r9_in'}, {'*': 'fb'})
    net.put('r9_s', flat([[r[K]] + b[0:1] + b[2:3] for r, b in zip(r1, B)]))
    net.collates.append(('r9_in', [('r9_s', 3, [0, 1, 2]), ('st_r9', 4, [2])]))
    net.add('mul', FR + 'mul.cq', {'la': 'fa', 'lb': 'fb', '*': 'xb'}, {'*': 'dur'})
    net.add('nframes', FR + 'nframes.cq', {'*': 'nf_in'}, {'*': 'n'})
    net.put('nf_s', flat(cols(r1, [K])))
    net.collates.append(('nf_in', [('nf_s', 1, [0]), ('dur', 1, [0])]))
    net.fan['n'] = ['n_sum', 'n_fr', 'n_cl', 'n_ed', 'n_ch', 'n_gl', 'n_decl', 'n_rise', 'n_ty', 'n_ls', 'n_vs']
    net.add('back', FR + 'back.cq', {'*': 'bk_in'}, {'*': 'bk'})
    net.put('bk_in', flat([cols([r], [PC, K, VLS])[0] + c[4:5] for r, c in zip(r1, C)]))
    net.fan['bk'] = ['bk_ed', 'bk_gl', 'bk_ls']
    net.add('sum', FR + 'sum.cq', {'*': 'sum_in'}, {'*': 'sums'})
    net.put('sum_s', flat(cols(r1, [K, SEND])))
    net.collates.append(('sum_in', [('sum_s', 2, [0, 1]), ('st_sum', 4, [0]), ('n_sum', 1, [0])]))
    net.fan['sums'] = ['sum_decl', 'sum_ty']
    net.add('framer', FR + 'framer.cq', {'*': 'fr_in'}, {'up': 'u_rise', 'ul': 'u_vs', '*': 'frm'})
    net.put('fr_s', flat(cols(r1, [SEND])))
    net.collates.append(('fr_in', [('n_fr', 1, [0]), ('fr_s', 1, [0])]))
    net.fan['frm'] = ['frm_ch', 'frm_gl']
    net.add('closure', FR + 'closure.cq', {'gci': 'clt', 'gct': 'clt', '*': 'cl_in'}, {'ask': 'clask', '*': 'cl'})
    net.fetch['clask'] = (FEAT_TABLE, tb.FEAT, tb.F_CINH, 2, 'clt')
    net.put('cl_s', flat(cols(r1, [PC, K])))
    net.collates.append(('cl_in', [('cl_s', 2, [0, 1]), ('n_cl', 1, [0])]))
    net.add('main', FR + 'main.cq', {'gv': 'mnt', 'gn': 'mnt', 'ga': 'mnt', 'gb': 'mnb', '*': 'mn_in'},
            {'ask': 'mnask', 'askb': 'mnaskb', '*': 'mn'})
    net.fetch['mnask'] = (FEAT_TABLE, tb.FEAT, tb.F_VOICED, 3, 'mnt')
    net.fetch['mnaskb'] = (FEAT_TABLE, tb.FEAT, tb.F_BACK, 1, 'mnb')
    net.put('mn_in', flat([cols([r], [PC, K])[0] + [c[3], c[4], c[0]] for r, c in zip(r1, C)]))
    net.add('edge', FR + 'edge.cq', {'g1': 'edt', 'g2': 'edt', 'g3': 'edt', 'g4': 'edt', 'g5': 'edt', '*': 'ed_in'},
            {'ask': 'edask', '*': 'ed'})
    net.fetch['edask'] = (FEAT_TABLE, tb.FEAT, tb.F_ASP, 5, 'edt')
    net.put('ed_s', flat(cols(r1, [PC, K])))
    net.collates.append(('ed_in', [('ed_s', 2, [0, 1]), ('n_ed', 1, [0]), ('bk_ed', 4, [2, 3])]))
    net.add('choose', FR + 'choose.cq', {'fj': 'ch_f', 'fu': 'ch_f', 'fe': 'ch_f', '*': 'ch_s'}, {'ls': 'sv', 'lv': 'sv', '*': 'abug'})
    net.collates.append(('ch_s', [('n_ch', 1, [0]), ('cl', 1, [0]), ('mn', 5, [0, 1, 2, 3, 4]), ('ed', 2, [0, 1])]))
    net.collates.append(('ch_f', [('frm_ch', 5, [0, 1, 4])]))
    net.fan['sv'] = ['sv_ls', 'sv_vs', 'sv_ps', 'sv_m1', 'sv_kc']
    net.add('glides', FR + 'glides.cq', {'ca': 'gl_f', 'cb': 'gl_f', 'cu': 'gl_f', 'cg': 'gl_f', 'fl': 'gl_f', 'fr': 'gl_f', '*': 'gl_s'},
            {'*': 'kplan'})
    net.put('gl_c', flat(cols(C, [5])))
    net.collates.append(('gl_s', [('n_gl', 1, [0]), ('bk_gl', 4, [0]), ('gl_c', 1, [0])]))
    net.collates.append(('gl_f', [('abug', 4, [0, 1, 2, 3]), ('frm_gl', 5, [2, 3])]))
    net.fan['kplan'] = ['kp_a', 'kp_b', 'kp_c']
    net.add('glidea', FR + 'glidea.cq', {'lp': 'ga_x', 'gg': 'ga_x', 'gb': 'ga_y', 'gb2': 'ga_y', '*': 'ga_in'},
            {'aska': 'gaska', 'askb': 'gaskb', 'og': 'gain', '*': 'kp'})
    net.fetch['gaska'] = (FILT_TABLE, 11, 0, 11, 'ga_x')
    net.fetch['gaskb'] = (FILT_TABLE, 11, 0, 11, 'ga_y')
    net.collates.append(('ga_in', [('kp_a', 6, [0, 1, 2])]))
    net.add('glideb', FR + 'glideb.cq', {'lp': 'gb_x', 'gg': 'gb_x', 'gy': 'gb_y', 'gy2': 'gb_y', 'gk': 'kp', '*': 'gb_in'},
            {'askn': 'gbaskn', 'asko': 'gbasko', '*': 'kq'})
    net.fetch['gbaskn'] = (FILT_TABLE, 11, 0, 11, 'gb_x')
    net.fetch['gbasko'] = (FILT_TABLE, 11, 0, 11, 'gb_y')
    net.collates.append(('gb_in', [('kp_b', 6, [3, 4, 5])]))
    net.add('decl', FR + 'decl.cq', {'gl': 'sum_decl', 'g2': 'sum_decl', 'g3': 'sum_decl', 'g4': 'sum_decl', '*': 'dc_s'}, {'*': 'b0'})
    net.put('dc_x', flat(cols(r1, [SEND])))
    net.collates.append(('dc_s', [('n_decl', 1, [0]), ('dc_x', 1, [0])]))
    net.add('rise', FR + 'rise.cq', {'gu': 'u_rise', 'gb': 'b0', '*': 'rs_s'}, {'*': 'b1'})
    net.put('rs_k', flat(cols(r1, [K])))
    net.collates.append(('rs_s', [('rs_k', 1, [0]), ('st_rise', 4, [0]), ('n_rise', 1, [0])]))
    net.add('taily', FR + 'taily.cq', {'gl': 'sum_ty', 'g2': 'sum_ty', 'g3': 'sum_ty', 'g4': 'sum_ty', '*': 'ty_s'}, {'*': 'ty'})
    net.put('ty_x', flat(cols(r1, [SEND])))
    net.collates.append(('ty_s', [('n_ty', 1, [0]), ('ty_x', 1, [0])]))
    net.add('tailf', FR + 'tailf.cq', {'gy': 'ty', 'ge': 'ty', '*': 'b1'}, {'*': 'f0'})
    net.add('period', FR + 'period.cq', {'*': 'f0'}, {'pa': 'p_asm', '*': 'p_ps'})
    net.add('lsel', FR + 'lsel.cq', {'gs': 'ls_f', 'gv': 'ls_f', 'gl': 'lst', '*': 'ls_s'}, {'ask': 'lsask', '*': 'md1'})
    net.fetch['lsask'] = (FEAT_TABLE, tb.FEAT, tb.F_LOUD, 1, 'lst')
    net.put('ls_k', flat(cols(r1, [K])))
    net.put('ls_c', flat(cols(C, [1, 2])))
    net.collates.append(('ls_s', [('ls_k', 1, [0]), ('n_ls', 1, [0]), ('ls_c', 2, [0]), ('bk_ls', 4, [1]), ('ls_c2', 1, [0])]))
    net.put('ls_c2', flat(cols(C, [2])))
    net.collates.append(('ls_f', [('sv_ls', 2, [0, 1])]))
    net.add('vsel', FR + 'vsel.cq', {'gs': 'vs_f', 'gv': 'vs_f', 'gu': 'vs_f', '*': 'vs_s'}, {'m3': 'md3', 'oy3': 'md3', '*': 'md2'})
    net.put('vs_k', flat(cols(r1, [K])))
    net.collates.append(('vs_s', [('vs_k', 1, [0]), ('st_vsel', 4, [0]), ('n_vs', 1, [0])]))
    net.collates.append(('vs_f', [('sv_vs', 2, [0, 1]), ('u_vs', 1, [0])]))
    net.add('psel', FR + 'psel.cq', {'*': 'ps_f'}, {'*': 'md4'})
    net.collates.append(('ps_f', [('sv_ps', 2, [0, 1]), ('p_ps', 1, [0])]))
    net.add('mulx1', FR + 'mulx.cq', {'gm': 'md1', 'gy': 'md1', '*': 'm1_in'}, {'*': 'lv1'})
    net.collates.append(('m1_in', [('sv_m1', 2, [0, 1]), ('gain', 1, [0])]))
    net.add('mulx2', FR + 'mulx.cq', {'gm': 'md2', 'gy': 'md2', '*': 'lv1'}, {'*': 'lv2'})
    net.add('mulx3', FR + 'mulx.cq', {'gm': 'md3', 'gy': 'md3', '*': 'lv2'}, {'*': 'lv3'})
    net.add('mulx4', FR + 'mulx.cq', {'gm': 'md4', 'gy': 'md4', '*': 'lv3'}, {'*': 'lv4'})
    net.add('gnorm', FR + 'gnorm.cq', {'gc': 'gnt', '*': 'gn_in'}, {'ask': 'gnask', '*': 'md5'})
    net.fetch['gnask'] = (GLIDE_TABLE, GLIDE_REC, 0, GLIDE_REC, 'gnt')
    net.collates.append(('gn_in', [('kp_c', 6, [3, 4, 5])]))
    net.add('mulx5', FR + 'mulx.cq', {'gm': 'md5', 'gy': 'md5', '*': 'lv4'}, {'*': 'lv5'})
    net.add('kcarry', FR + 'kcarry.cq', {'frm': 'kc_s', 'gx': 'kq', '*': 'kself'}, {'pz': 'kself', 'wb': 'kself', '*': 'kout'})
    net.collates.append(('kc_s', [('sv_kc', 2, [0])]))
    net.add('asm', FR + 'asm.cq', {'gp': 'p_asm', 'gk': 'kout', '*': 'lv5'}, {'*': 'frames'})
    for p in list(net.piles):
        pass
    for name in ['n_sum', 'u_rise', 'u_vs', 'p_asm', 'p_ps', 'frames', 'kself', 'kp', 'kq', 'kout', 'gain']:
        net.piles.setdefault(name, [])
    net.run()
    for n, m in net.machines.items():
        tot[n] = m.steps
    if steps is not None:
        steps.update(tot)
    left = {p: len(v) for p, v in net.piles.items() if v}
    return net.piles['frames'], left
