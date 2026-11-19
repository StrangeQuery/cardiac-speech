"""The decks the text machines read: transcriptions of the tables in prototype/text_to_phonemes.py (the NRL rules,
the exception list, the function words, the letter names, the number words) and of ASCII, put into the codes the
CARDIAC programs use.  Nothing here is computed: each deck is the same table written as cards.

Letters get their own codes, chosen so that every class of letters the NRL rules name is a range of codes:
  A O U E I Y = 1-6 (vowels, # in the rules; E I Y = 4-6 is +, a front vowel)
  F H K P Q T S C X G J Z D L N R B M V W = 7-26 (consonants, ^; G-W = 16-26 is ., a voiced consonant;
  S C X G J Z = 13-18 is &, a sibilant; T S = 12-13 and J Z D L N R = 17-22 make @)
  ' = 27, and 28 is the edge of a word (27-28: a blank in the rules, not a letter)

The rule deck: for each letter a section, 900 + the letter's code, its rules in the report's order, and 999.  A
rule is 600, the number of letters it says (the bracket), the left context's elements (read leftwards from the
letter before the bracket), 0, the bracket's letters and the right context's elements (read rightwards from the
bracket's first letter), 0, then its phonemes (10 x code), up to the next 600 or 999.  An element is three cards:
how many (1 exactly one; 10 none or more; 11 one or more; 12 two or more) and the range of codes, lo and hi.
The report's %, & and @ match one of a few things; each such rule is written as one rule for each, one after the
other, all saying the same: % as E or ING; & as CH, SH or one of S C X G J Z; @ as TH, CH, SH, T or S, or one of
J Z D L N R.  Since the first rule that matches wins and these say the same, it is the same rule.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'prototype'))
import text_to_phonemes as tp   # noqa: E402
import table as tb               # noqa: E402

ORDER = 'AOUEIYFHKPQTSCXGJZDLNRBMVW'
CODE = {c: i + 1 for i, c in enumerate(ORDER)}
CODE["'"] = 27
EDGE = 28
V = (1, 6)
C = (7, 26)
VOICED = (16, 26)
FRONT = (4, 6)
BLANK = (27, 28)
SIB = (13, 18)
AT1, AT2 = (12, 13), (17, 22)
HERE = os.path.dirname(os.path.abspath(__file__))
TEXT = os.path.join(HERE, '..', 'text')


def ph(p):
    return 10 * tb.CODE[p]


def el(n, r):
    return [[n, r[0], r[1]]]


def lit(ch):
    return [[1, CODE[ch], CODE[ch]]]


def tokens(pat, leftward):
    """A context pattern as alternatives: a list of element lists (each element [n, lo, hi])."""
    s = pat[::-1] if leftward else pat
    alts = [[]]
    i = 0
    while i < len(s):
        c = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ''
        opts = None
        if c == ' ':
            e = el(1, BLANK)
        elif c == '#':
            if nxt == '#':
                e = el(12, V); i += 1
            else:
                e = el(11, V)
        elif c == ':':
            if nxt == '^':
                e = el(11, C); i += 1
            else:
                e = el(10, C)
        elif c == '^':
            e = el(1, C)
        elif c == '.':
            e = el(1, VOICED)
        elif c == '+':
            e = el(1, FRONT)
        elif c == '%':
            assert not leftward and i == len(s) - 1
            opts = [lit('E'), lit('I') + lit('N') + lit('G')]
        elif c == '&':
            assert leftward
            opts = [lit('H') + lit('C'), lit('H') + lit('S'), el(1, SIB)]
        elif c == '@':
            assert leftward
            opts = [lit('H') + lit('T'), lit('H') + lit('C'), lit('H') + lit('S'), el(1, AT1), el(1, AT2)]
        else:
            e = lit(c)
        if opts is None:
            opts = [e]
        alts = [a + o for a in alts for o in opts]
        i += 1
    return alts


def rule_deck():
    deck = []
    for x in ORDER:
        deck.append(900 + CODE[x])
        for left, mid, right, out in tp.RULES[x]:
            for la in tokens(left, True):
                for ra in tokens(right, False):
                    deck += [600, len(mid)]
                    for e in la:
                        deck += e
                    deck.append(0)
                    for e in lit_seq(mid) + ra:
                        deck += e
                    deck.append(0)
                    deck += [ph(p) for p in out]
        deck.append(999)
    return deck


def lit_seq(mid):
    return [[1, CODE[c], CODE[c]] for c in mid]


def ascii_table():
    """For each of the 128 ASCII codes, two cards: its class (0 not part of any word or number, 1 a capital, 2 a
    small letter, 3 an apostrophe, 4 a digit, 5 punctuation) and its value (the letter's code, the digit, or the
    punctuation's card: -2 for , ; and :, -3 for ., -4 for ?, -5 for !)."""
    t = []
    for a in range(128):
        ch = chr(a)
        if 'A' <= ch <= 'Z':
            t += [1, CODE[ch]]
        elif 'a' <= ch <= 'z':
            t += [2, CODE[ch.upper()]]
        elif ch == "'":
            t += [3, 27]
        elif '0' <= ch <= '9':
            t += [4, a - 48]
        elif ch in ',;:.?!':
            t += [5, {',': -2, ';': -2, ':': -2, '.': -3, '?': -4, '!': -5}[ch]]
        else:
            t += [0, 0]
    return t


def word_cards(w):
    return [CODE[c] for c in w]


EXCEPTION_WORDS = list(tp.EXCEPTIONS)
EXPHON_SIZE = 12


def exception_deck():
    """The words to look for: the function words (each its letters, -52), then the exceptions (each its letters,
    then -100 - its number, 1 the first), then -99, the deck's end."""
    deck = []
    for w in sorted(tp.FUNCTION_WORDS):
        deck += word_cards(w) + [-52]
    for k, w in enumerate(EXCEPTION_WORDS, 1):
        deck += word_cards(w) + [-100 - k]
    return deck + [-99]


def exphon_deck():
    """For exception k (1 the first, record 0 unused), its phonemes as 10 x code + stress, padded with 0 to 12."""
    deck = [0] * EXPHON_SIZE
    for w in EXCEPTION_WORDS:
        cards = []
        for t in tp.EXCEPTIONS[w].split():
            s = int(t[-1]) if t[-1].isdigit() else 0
            cards.append(10 * tb.CODE[t.rstrip('012')] + s)
        deck += cards + [0] * (EXPHON_SIZE - len(cards))
    return deck


LETTER_SIZE = 8


def letter_deck():
    """For each letter code (record 0 unused), its name's phonemes (codes), then 0, padded to 8 cards."""
    deck = [0] * LETTER_SIZE
    for x in ORDER:
        p = [tb.CODE[t] for t in tp.LETTERS[x].split()] + [0]
        deck += p + [0] * (LETTER_SIZE - len(p))
    return deck


NUMBER_WORDS = tp.ONES + tp.TENS[2:] + ['HUNDRED', 'THOUSAND', 'OH']
NUMBER_SIZE = 10


def number_deck():
    """The number words: record k (0-19 the ones, 20-27 twenty to ninety, 28 hundred, 29 thousand, 30 oh): its
    letters, -10 (the end of a word), padded with 0 to 10 cards."""
    deck = []
    for w in NUMBER_WORDS:
        r = word_cards(w) + [-10]
        deck += r + [0] * (NUMBER_SIZE - len(r))
    return deck


def write():
    for name, deck in (('rules', rule_deck()), ('ascii', ascii_table()), ('exceptions', exception_deck()),
                       ('exphon', exphon_deck()),
                       ('letters', letter_deck()), ('numbers', number_deck())):
        open(os.path.join(TEXT, name + '.cards'), 'w').write('\n'.join(map(str, deck)) + '\n')
        print(name, len(deck))


if __name__ == '__main__':
    write()
