"""The whole front end on the dev emulator, phases and all, against front_machines.compose."""
import sys
import front_ref as fr
import front_machines as fm
import nets
import table as tb
import sentences
import test_front as T

fr.load(tb.C)
texts = sentences.MAIN + sentences.MORE
ok = True
for t in texts[:int(sys.argv[1]) if len(sys.argv) > 1 else None]:
    toks = T.tokens(t)
    want, _ = fm.compose(toks)
    st = {}
    got, left = nets.front(toks, st)
    same = got == want
    ok &= same
    print('%-30s %s frames %d, %d instructions, left %s' % (t[:30], 'exact' if same else 'DIFFERENT', (len(want) - 1) // 13, sum(st.values()), left))
    if not same:
        i = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]), min(len(got), len(want)))
        print('  at', i, got[i:i+6], want[i:i+6], len(got), len(want))
