#!/usr/bin/env python3
"""The Rust version's rule decks, data/left.cards, data/right.cards and data/phonemes.cards: text/rules.cards (the
NRL rules as text/ holds them for the hand-written version, made by ref/text_tables.py) laid out again as three
tables of one record a letter, so that the host can fetch a letter's rules by its code, one table for each of the
three machines that match them. Nothing is computed: the same rules, in the same order, with the same cards.

Record k (k the letter's code, 1 to 26; record 0 is for a card that isn't a letter) of each table holds the letter's
rules in order:

  left.cards      each rule's left context, its elements, then -2; then -2 for each rule a letter has fewer than
                  the most any letter has, so that every letter gives left as many verdicts
  right.cards     each rule's right context (from the letter on), its elements, then -2; and the same -2s
  phonemes.cards  each rule's n (the letters it says) and its phonemes, then -2

An element is four cards: the most letters it matches and the fewest (text/rules.cards has 1 for exactly one, 10 for
none or more, 11 for one or more and 12 for two or more, which are 1 and 1, 99 and 0, 99 and 1, 99 and 2), and the
range of codes they can be. Each record is filled out with 0s to the size of the table's longest and ends with -1;
the machines pass over the 0s.

The exceptions deck, text/exceptions.cards, is split in two the same way: data/function.cards, the function words
(each its letters and -52), and data/exceptions.cards, the exceptions (each its letters and -100 - its number), each
ended by -99, so that one machine looks a word up in each.

  python3 rust/tables.py      writes the five decks and prints their sizes
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def sections(deck):
    """{letter code: [rule, ...]}, each rule (n, left elements, right elements, phonemes), from text/rules.cards."""
    out = {}
    i = 0
    while i < len(deck):
        assert 901 <= deck[i] <= 926, deck[i]
        letter = deck[i] - 900
        i += 1
        rules = []
        while deck[i] != 999:
            assert deck[i] == 600
            n = deck[i + 1]
            i += 2
            ctx = []
            for _ in range(2):
                els = []
                while deck[i] != 0:
                    els.append(deck[i:i + 3])
                    i += 3
                i += 1
                ctx.append(els)
            phs = []
            while deck[i] < 600:
                phs.append(deck[i])
                i += 1
            rules.append((n, ctx[0], ctx[1], phs))
        i += 1
        out[letter] = rules
    return out


def element(e):
    """An element as the most and fewest letters it matches, and its range."""
    q, lo, hi = e
    return ([1, 1] if q == 1 else [99, q - 10]) + [lo, hi]


def tables(deck):
    """{name: (records, size)} for the three tables, and the most rules a letter has."""
    secs = sections(deck)
    most = max(len(r) for r in secs.values())
    bodies = {'left': {0: [-2] * most}, 'right': {0: [-2] * most}, 'phonemes': {0: []}}
    for letter, rules in secs.items():
        pad = [-2] * (most - len(rules))
        bodies['left'][letter] = [c for n, l, r, p in rules for c in [x for e in l for x in element(e)] + [-2]] + pad
        bodies['right'][letter] = [c for n, l, r, p in rules for c in [x for e in r for x in element(e)] + [-2]] + pad
        bodies['phonemes'][letter] = [c for n, l, r, p in rules for c in [n] + p + [-2]]
    out = {}
    for name, body in bodies.items():
        size = max(len(b) for b in body.values()) + 1
        out[name] = ([body[k] + [0] * (size - 1 - len(body[k])) + [-1] for k in range(27)], size)
    return out, most


if __name__ == '__main__':
    deck = [int(v) for v in open(os.path.join(HERE, '..', 'text', 'rules.cards')).read().split()]
    out, most = tables(deck)
    os.makedirs(os.path.join(HERE, 'data'), exist_ok=True)
    for name, (recs, size) in out.items():
        open(os.path.join(HERE, 'data', name + '.cards'), 'w').write('\n'.join(str(c) for r in recs for c in r) + '\n')
        print('%s.cards: %d records of %d cards' % (name, len(recs), size))
    print('the most rules a letter has:', most)
    exc = [int(v) for v in open(os.path.join(HERE, '..', 'text', 'exceptions.cards')).read().split()]
    cut = max(i for i, c in enumerate(exc) if c == -52) + 1
    for name, deck in (('function', exc[:cut] + [-99]), ('exceptions', exc[cut:])):
        assert deck[-1] == -99 and all(c >= 0 or c == -52 for c in deck[:-1]) == (name == 'function')
        open(os.path.join(HERE, 'data', name + '.cards'), 'w').write('\n'.join(map(str, deck)) + '\n')
        print('%s.cards: %d cards' % (name, len(deck)))
