"""The networks of machines, wired as the Rust host wires them (src/nets.rs)."""
import cardiac

V = '../voice/'


def voice_box(net, frames_pile='frames', out_pile='out'):
    net.add('interp', V + 'interp.cq', {3: frames_pile, 6: frames_pile, 13: frames_pile, 27: frames_pile, '*': 'iself'},
            {7: 'iself', 35: 'iself', '*': 'tosteps'})
    net.add('steps', V + 'steps.cq', {3: 'tosteps', 7: 'tosteps', '*': 'sself'},
            {18: 'exc', 20: 'exc', 28: 'exc', 38: 'kin', '*': 'sself'})
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
