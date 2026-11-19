"""A CARDIAC for development: the same machine as heartburn (cells -999..999, accumulator -9999..9999, cell 00
wired to 001, JMP leaves 8xx in 99, negative words skipped, STO 00 ignored), and a network of machines whose
INP and OUT instructions are wired to piles of cards, as the Rust host (src/net.rs) wires them.  Only for trying
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
    """Machines wired by pile.  inp[name] = {cell: pile}, out[name] = {cell: pile} ('*' for the rest).
    A machine waiting at an INP gets the next card of the pile wired to that INP's cell.  deal[pile] = (n, [piles])
    deals a pile's cards n at a time to the piles in turn."""
    def __init__(self):
        self.machines = {}
        self.inp = {}
        self.outw = {}
        self.piles = {}
        self.deal = {}
        self.dealt = {}
        self.log = None
        self.fetch = {}
        self.fan = {}          # pile -> piles that each get a copy of every card put on it
        self.collates = []
        self.cycle = {}        # pile -> a deck dealt onto it again whenever a machine waits on it empty     # (out pile, [(source pile, record size, columns)]): whole records, columns picked

    def add(self, name, path, inp, out):
        deck, labels = assemble(path)
        self.machines[name] = Machine(deck, name)
        self.inp[name] = {labels.get(k, k) if isinstance(k, str) and k != '*' else k: v for k, v in inp.items()}
        self.outw[name] = {labels.get(k, k) if isinstance(k, str) and k != '*' else k: v for k, v in out.items()}
        for p in list(inp.values()) + list(out.values()):
            self.piles.setdefault(p, [])
        return labels

    def put(self, pile, cards):
        if self.log is not None:
            self.log.setdefault(pile, []).extend(cards)
        if pile in self.fan:
            for p in self.fan[pile]:
                self.put(p, cards)
            return
        if pile in self.fetch:
            table, size, off, count, to = self.fetch[pile]
            for c in cards:
                self.piles[to].extend(table[c * size + off:c * size + off + count])
            return
        if pile in self.deal:
            n, to = self.deal[pile]
            for c in cards:
                k = self.dealt.get(pile, 0)
                self.piles[to[(k // n) % len(to)]].append(c)
                self.dealt[pile] = k + 1
        else:
            self.piles.setdefault(pile, []).extend(cards)

    def collate(self):
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
        return moved

    def run(self):
        """Run every machine until none can go on.  Returns {name: why} for each machine's stop."""
        state = {n: None for n in self.machines}
        moved = True
        while moved:
            moved = self.collate()
            for n, mc in self.machines.items():
                if mc.halted:
                    continue
                if state[n] == 'input':
                    p = self.inp[n].get(mc.pc, self.inp[n].get('*'))
                    q = self.piles.get(p)
                    if not q and p in self.cycle:
                        self.piles[p] = q = list(self.cycle[p])
                    if not q:
                        continue
                    mc.push([q.pop(0)])
                ow = self.outw[n]
                def out(cell, v, ow=ow):
                    self.put(ow.get(cell, ow.get('*')), [v])
                state[n] = mc.run(out)
                moved = True
        return state
