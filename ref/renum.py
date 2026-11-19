"""Renumber a listing's cells after lines are inserted or removed: each cell line takes the address after the one
before it, except where the listing jumps ahead (a new block at a fixed address, such as the data), which keeps
its address.  A new line may be written with address xx.  Block comments of the form NN-MM: are reset to the
cells each block now covers (a block runs to the cell before the next block comment, or the end of its run)."""
import re
import sys

path = sys.argv[1]
pack = '--pack' in sys.argv          # every cell after the one before, no fixed blocks
lines = open(path).read().split('\n')
cells = []          # (line index, old address or None)
for i, l in enumerate(lines):
    m = re.match(r'^  (\d\d|xx) ', l)
    if m:
        cells.append((i, None if m.group(1) == 'xx' else int(m.group(1))))
prev_old = None
prev_new = None
new = {}
for i, old in cells:
    if prev_new is None:
        a = old
    elif not pack and old is not None and prev_old is not None and old > prev_old + 1 and old > prev_new + 1:
        a = old                       # a jump ahead in the original: a fixed block
    else:
        a = prev_new + 1
    new[i] = a
    if old is not None:
        prev_old = old
    else:
        prev_old = (prev_old or 0) + 1
    prev_new = a
for i, a in new.items():
    lines[i] = '  %02d' % a + lines[i][4:]
# block comments
order = [i for i, _ in cells]
for k, i in enumerate(order):
    m = re.search(r' (\d\d)-(\d\d):', lines[i][24:])
    if not m:
        continue
    start = new[i]
    end = start
    for j in order[k + 1:]:
        if re.search(r' \d\d-\d\d:', lines[j][24:]) or new[j] != end + 1:
            break
        end = new[j]
    s = lines[i]
    pos = 24 + m.start() + 1
    lines[i] = s[:pos] + '%02d-%02d:' % (start, end) + s[pos + 6:]
assert max(new.values()) <= 99, 'past cell 99'
open(path, 'w').write('\n'.join(lines))
print(path, 'cells to', max(new.values()))
