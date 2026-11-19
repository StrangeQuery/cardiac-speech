"""A CARDIAC for development: the same machine as heartburn (cells -999..999, accumulator -9999..9999, cell 00
wired to 001, JMP leaves 8xx in 99, negative words skipped, STO 00 ignored), and a network of machines, each
reading one pile of cards and punching onto one, as the Rust host (src/net.rs) wires them.  Only for trying
programs quickly; every result reported is checked under heartburn."""
import os
import shutil
import subprocess

CARC = shutil.which('carc') or 'carc'   # heartburn's assembler, on the PATH


def assemble(path):
    """carc's deck for a listing, and its labels (read from the listing's label column)."""
    out = subprocess.run([CARC, '-o', '-', path], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(out.stderr)
    deck = [int(l) for l in out.stdout.split('\n') if l.strip() and not l.startswith('#')]
    labels = {}
    for line in open(path):
        w = line.split()
        if len(w) < 2 or not w[0].isdigit():
            continue
        i = 2 if w[1].lstrip('-').isdigit() else 1
        if i < len(w) and w[i] not in OPS:
            labels[w[i]] = int(w[0])
    return deck, labels


OPS = {'INP', 'CLA', 'ADD', 'TAC', 'SFT', 'OUT', 'STO', 'SUB', 'JMP', 'HRS', 'DATA', 'DAT'}


class Machine:
    def __init__(self, deck, name=''):
        self.m = [0] * 100
        self.m[0] = 1
        self.acc = 0
        self.pc = 0
        self.steps = 0
        self.cards = list(deck)
        self.ci = 0
        self.name = name
        self.halted = False

    def push(self, cards):
        self.cards.extend(cards)

    def run(self, out, budget=10 ** 12):
        """Run until an INP finds no card (returns 'input'), HRS ('halt') or the budget.  out(cell, value)."""
        m = self.m
        acc, pc, steps = self.acc, self.pc, self.steps
        cards, ci = self.cards, self.ci
        limit = steps + budget
        why = 'budget'
        while steps < limit:
            w = m[pc]
            here = pc
            pc += 1
            if w < 0:
                steps += 1
                if pc == 100:
                    pc = 0
                continue
            op, a = divmod(w, 100)
            if op == 0:
                if ci >= len(cards):
                    pc = here
                    why = 'input'
                    break
                if a:
                    m[a] = cards[ci]
                ci += 1
            elif op == 1:
                acc = m[a]
            elif op == 2:
                acc += m[a]
                if acc > 9999: acc -= 10000
                elif acc < -9999: acc += 10000
            elif op == 3:
                if acc < 0:
                    pc = a
            elif op == 4:
                l, r = divmod(a, 10)
                x = (abs(acc) * 10 ** l) % 10000 // 10 ** r
                acc = -x if acc < 0 else x
            elif op == 5:
                out(here, m[a])
            elif op == 6:
                if a:
                    m[a] = acc % 1000 if acc >= 0 else -((-acc) % 1000)
            elif op == 7:
                acc -= m[a]
                if acc > 9999: acc -= 10000
                elif acc < -9999: acc += 10000
            elif op == 8:
                m[99] = 800 + (pc % 100)
                pc = a
            else:
                steps += 1
                why = 'halt'
                self.halted = True
                pc = a
                break
            steps += 1
            if pc == 100:
                pc = 0
        self.acc, self.pc, self.steps, self.ci = acc, pc, steps, ci
        if ci > 4096:
            del cards[:ci]
            self.ci = 0
        return why


def run_alone(path, cards, budget=10 ** 9):
    """One machine, all its cards in the reader: (outputs, steps, why)."""
    deck, _ = assemble(path)
    mc = Machine(deck + list(cards))
    out = []
    why = mc.run(lambda c, v: out.append(v), budget)
    return out, mc.steps, why


class Net:
    """Machines wired as the host wires them (src/net.rs): each machine reads one pile and punches onto one pile.
    Cards put on a pile are kept, or dealt (deal[pile] = (n, [piles]): n at a time to the piles in turn; split[pile]
    = [(pile, n), ...]: so many to each pile in turn), copied
    (fan[pile] = [piles]), fetched (fetch[pile] = (table, size, off, count, to): each card names a record of the
    table, whose cards off to off + count go onto `to`), or passed on after the first few (after[pile] = (n, to)).
    collate(out, [(pile, size, columns)]) puts whole records together; merge(out, [(pile, n)], decks) takes n cards
    from each pile in turn, over and over (n 0: all from then on; a pile 'deck:NAME' is decks[NAME], dealt again
    each time its turn comes). punched[name] is everything a machine has punched."""
    def __init__(self):
        self.machines = {}
        self.wires = {}
        self.piles = {}
        self.deal = {}
        self.dealt = {}
        self.fetch = {}
        self.fan = {}
        self.after = {}
        self.seen = {}
        self.collates = []
        self.merges = []
        self.split = {}        # pile -> [(pile, n)]: dealt by that pattern, round and round
        self.splat = {}
        self.punched = {}      # name -> every card the machine has punched

    def add(self, name, path, inp, out):
        deck, labels = assemble(path)
        self.machines[name] = Machine(deck, name)
        self.wires[name] = (inp, out)
        for p in (inp, out):
            self.piles.setdefault(p, [])
        return labels

    def put(self, pile, cards):
        for c in cards:
            self.put1(pile, c)

    def put1(self, pile, c):
        if pile in self.fan:
            for p in self.fan[pile]:
                self.put1(p, c)
        elif pile in self.fetch:
            table, size, off, count, to = self.fetch[pile]
            assert c >= 0 and c * size + off + count <= len(table), (pile, c)
            self.put(to, table[c * size + off:c * size + off + count])
        elif pile in self.split:
            pat = self.split[pile]
            at, taken = self.splat.get(pile, (0, 0))
            to, n = pat[at]
            taken += 1
            if taken == n:
                at, taken = (at + 1) % len(pat), 0
            self.splat[pile] = (at, taken)
            self.put1(to, c)
        elif pile in self.deal:
            n, to = self.deal[pile]
            k = self.dealt.get(pile, 0)
            self.dealt[pile] = k + 1
            self.put1(to[(k // n) % len(to)], c)
        elif pile in self.after:
            n, to = self.after[pile]
            k = self.seen.get(pile, 0)
            self.seen[pile] = k + 1
            if k >= n:
                self.put1(to, c)
        else:
            self.piles.setdefault(pile, []).append(c)

    def collate(self, out, srcs):
        self.collates.append((out, srcs))

    def merge(self, out, pattern, decks=None):
        self.merges.append([out, pattern, decks or {}, 0, 0, {}])

    def move(self):
        moved = False
        for out, srcs in self.collates:
            while all(len(self.piles.get(p, [])) >= n for p, n, _ in srcs):
                rec = []
                for p, n, cols in srcs:
                    r = self.piles[p][:n]
                    del self.piles[p][:n]
                    rec += [r[c] for c in cols]
                self.put(out, rec)
                moved = True
        for m in self.merges:
            out, pattern, decks, at, taken, pos = m
            while True:
                p, n = pattern[at]
                if p.startswith('deck:'):
                    d = decks[p[5:]]
                    k = pos.get(p, 0)
                    c = d[k]
                    pos[p] = (k + 1) % len(d)
                else:
                    q = self.piles.get(p)
                    if not q:
                        break
                    c = q.pop(0)
                self.put1(out, c)
                moved = True
                taken += 1
                if taken == n and n > 0:
                    taken = 0
                    at = (at + 1) % len(pattern)
            m[3], m[4] = at, taken
        return moved

    def run(self):
        """Run every machine until none can go on.  Returns {name: why} for each machine's stop."""
        state = {n: None for n in self.machines}
        moved = True
        while moved:
            moved = self.move()
            for n, mc in self.machines.items():
                if mc.halted:
                    continue
                inp, outp = self.wires[n]
                if state[n] == 'input':
                    q = self.piles.get(inp)
                    if not q:
                        continue
                    mc.push([q.pop(0)])
                tap = self.punched.setdefault(n, [])
                state[n] = mc.run(lambda cell, v, o=outp, t=tap: (t.append(v), self.put1(o, v)))
                moved = True
        return state
