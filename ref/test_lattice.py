"""Step 1: the five lattice machines under the dev emulator against voice_ref.lattice."""
import random
import os
import sys
import cardiac
import voice_ref as vr

random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
nsteps = 40
fr = vr.sc.read_frames(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'hello_tts.frames'))
Ks = []
for i in range(nsteps):
    k = fr[i % len(fr)]['k']
    Ks.append([max(-999, min(999, int(round(v * 1000)))) for v in k])
# a few awkward ones: zeros, tiny, extremes
Ks[3] = [0, 5, -7, 999, -999, 100, -100, 10, -10, 995]
exc = [random.choice([0, 0, 0, random.randint(-999, 999)]) for _ in range(nsteps * 20)]
amps = [0 if i % 4 == 2 else 1 for i in range(nsteps)]    # every fourth step a pause: truncation
want = vr.lattice(exc, Ks, amps)

net = cardiac.Net()
V = '../voice/'
net.add('L1', V + 'lattice_top.cq', {'go': 'e', 'getb': 'b8', '*': 'c1'}, {'*': 'f9'})
names = ['L2', 'L3', 'L4']
for j, n in enumerate(names):
    up_f = ['f9', 'f7', 'f5'][j]
    down_f = ['f7', 'f5', 'f3'][j]
    up_b = ['b8', 'b6', 'b4'][j]
    low_b = ['b6', 'b4', 'b2'][j]
    cp = 'c%d' % (j + 2)
    net.add(n, V + 'lattice.cq', {'go': up_f, 'getb': low_b, '*': cp}, {'loop': up_b, '*': down_f})
net.add('L5', V + 'lattice_bottom.cq', {'go': 'f3', '*': 'c5'}, {'loop': 'b2', '*': 'out'})
for s, K in enumerate(Ks):
    ws = []
    for k in reversed(K):
        ws += vr.words(k, amps[s])
    for m in range(5):
        net.put('c%d' % (m + 1), ws[10 * m:10 * m + 10])
net.put('e', exc)
net.run()
got = net.piles['out']
print(len(got), len(want), 'match' if got == want else 'DIFFER')
if got != want:
    i = next(i for i in range(min(len(got), len(want))) if got[i] != want[i])
    print('first difference at sample', i, got[i:i + 5], want[i:i + 5])
print('steps', {n: m.steps for n, m in net.machines.items()})
