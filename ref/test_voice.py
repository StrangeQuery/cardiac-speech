"""Step 2: the whole voice box under the dev emulator against voice_ref.voice."""
import sys
import cardiac
import nets
import voice_ref as vr

name = sys.argv[1] if len(sys.argv) > 1 else 'hello'
nf = int(sys.argv[2]) if len(sys.argv) > 2 else 30
frames = vr.sc.read_frames(vr.LPC + '/out/%s.frames' % name)[:nf]
deck = vr.frame_cards(frames)
want, peak = vr.voice(deck)
net = cardiac.Net()
nets.voice_box(net)
net.put('frames', deck)
state = net.run()
got = net.piles['out']
print(name, nf, 'frames:', len(got) // 2, 'samples', 'match' if got == want else 'DIFFER', 'peak |yd|', peak)
if got != want:
    i = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]), min(len(got), len(want)))
    print('first difference at value', i, got[i:i + 6], want[i:i + 6], len(got), len(want))
tot = sum(m.steps for m in net.machines.values())
print('instructions', tot, 'per sample %.0f' % (tot / max(1, len(got) // 2)), {n: m.steps for n, m in net.machines.items()})
print({n: s for n, s in state.items()})
