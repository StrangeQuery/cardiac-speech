"""The text machines' work in Python, on the decks in text/ (text_tables.py), each function what one machine (or
the rule machines together) does, card for card.  compose() must give prototype/text_to_phonemes.py's tokens."""
import os
import text_tables as tt
import table as tb

D = tt.TEXT


def deck(name):
    return [int(v) for v in open(os.path.join(D, name + '.cards')).read().split()]


RULES = deck('rules')
ASCII = deck('ascii')
EXC = deck('exceptions')
EXPHON = deck('exphon')
LETTERS = deck('letters')
NUMBERS = deck('numbers')
SECTION = {}
_i = 0
while _i < len(RULES):
    if RULES[_i] >= 900 and RULES[_i] != 999:
        SECTION[RULES[_i] - 900] = _i + 1
    _i += 1


def match_word(w):
    """The NRL rules on a word's letter codes, as the rule machines run them: phoneme cards (10 x code)."""
    W = [tt.EDGE] + list(w) + [tt.EDGE]
    out = []
    i = 1
    while W[i] != tt.EDGE:
        if W[i] == 27:
            i += 1
            continue
        k = SECTION[W[i]]
        while True:
            assert RULES[k] == 600
            n = RULES[k + 1]
            k += 2

            def elements(k, pos, d):
                ok = True
                while RULES[k] != 0:
                    q, lo, hi = RULES[k:k + 3]
                    k += 3
                    if not ok:
                        continue
                    if q == 1:
                        if lo <= W[pos] <= hi:
                            pos += d
                        else:
                            ok = False
                    else:
                        c = 0
                        while lo <= W[pos] <= hi:
                            pos += d
                            c += 1
                        if c < q - 10:
                            ok = False
                return ok, k + 1
            okl, k = elements(k, i - 1, -1)
            okr, k = elements(k, i, 1)
            phs = []
            while RULES[k] < 600:
                phs.append(RULES[k]); k += 1
            if okl and okr:
                out += phs
                i += n
                break
            assert RULES[k] == 600, 'no rule matched'
    return out


if __name__ == '__main__':
    import sys
    sys.path.insert(0, tt.os.path.join(tt.os.path.dirname(tt.os.path.abspath(__file__)), '..', 'prototype'))
    import words
    bad = 0
    for word in words.WORDS:
        up = word.upper()
        want = [10 * tb.CODE[p] for p in tt.tp.rules_word(up)]
        got = match_word([tt.CODE[c] for c in up])
        if got != want:
            bad += 1
            print(word, got, want)
    print(len(words.WORDS), 'words,', bad, 'differ')


# ---------------------------------------------------------------------------------------------------- machines
import re  # noqa: E402
tp = tt.tp
AX = tb.CODE['AX']
AH = tb.CODE['AH']


def scan(text):
    """scan.cq: characters -> the small-letter flag, then words (letters, -10, 1 if a small letter), numbers
    (500 + d, -12), punctuation (-2 to -5), -9."""
    out = [1 if any('a' <= ch <= 'z' for ch in text) else 0]
    for t in re.findall(r"[A-Za-z']+|\d+|[.,!?;:]", text):
        if t[0].isdigit():
            out += [500 + int(d) for d in t] + [-12]
        elif t in '.,!?;:':
            out.append({',': -2, ';': -2, ':': -2, '.': -3, '?': -4, '!': -5}[t])
        else:
            out += [tt.CODE[c.upper()] for c in t] + [-10, 1 if any('a' <= c <= 'z' for c in t) else 0]
    return out + [-9]


def num(cards):
    """num.cq: numbers -> number words: each its letters, -10, 2 (all capitals, as if in an all-caps text)."""
    out = []
    digits = []
    for c in cards:
        if 500 <= c <= 509:
            digits.append(c - 500)
        elif c == -12:
            n = int(''.join(map(str, digits)))
            for w in tp.say_number(n):
                out += [tt.CODE[ch] for ch in w] + [-10, 2]
            digits = []
        else:
            out.append(c)
    return out


def spcls(cards):
    """spcls.cq: the small-letter flag first; each word (letters, -10, lw) -> to be spelled: its letters as 100 +
    code, the last 200 + code, then -11; else its letters and -10.  Spelled: all capitals (lw 0 or 2) and a single
    letter other than A and I, or two or more letters with no vowel A E I O U, or not in an all-caps text (lw 0
    with the flag 1)."""
    lowt = cards[0]
    out = []
    word = []
    i = 1
    while i < len(cards):
        c = cards[i]
        if 1 <= c <= 28:
            word.append(c)
        elif c == -10:
            lw = cards[i + 1]; i += 1
            letters = [x for x in word if x != 27]
            L = len(letters)
            hv = any(x <= 5 for x in letters)
            up = lw != 1 and L >= 1
            caps = lw == 2 or not lowt
            sp = up and ((L == 1 and letters[0] not in (1, 5)) or (L >= 2 and (not caps or not hv)))
            if sp:
                for k, x in enumerate(letters):
                    out.append((200 if k == L - 1 else 100) + x)
                out.append(-11)
            else:
                out += word + [-10]
            word = []
        else:
            out.append(c)
        i += 1
    return out


def spell(cards):
    """spell.cq: spelled letters -> each letter's name (the letters deck): its first vowel other than AX stressed,
    1 for the last letter and 2 for the others; -1 between letters; -20 at the end."""
    out = []
    for c in cards:
        if 101 <= c <= 228:
            x = c % 100
            last = c >= 200
            rec = LETTERS[x * tt.LETTER_SIZE:(x + 1) * tt.LETTER_SIZE]
            done = False
            for p in rec[:rec.index(0)]:
                s = 0
                if 3 <= p <= 18 and not done and p != AX:
                    s = 1 if last else 2
                    done = True
                out.append(10 * p + s)
            if not last:
                out.append(-1)
        elif c == -11:
            out.append(-20)
        else:
            out.append(c)
    return out


def exc(cards):
    """exc.cq: each word (letters, -10) -> an exception's phonemes (stress 0 for a function word), then -20; or the
    word's letters and -13, or -14 for a function word."""
    out = []
    word = []
    for c in cards:
        if 1 <= c <= 28:
            word.append(c)
        elif c == -10:
            w = ''.join(tt.ORDER[x - 1] if x <= 26 else "'" for x in word)
            fn = w in tp.FUNCTION_WORDS
            if w in tp.EXCEPTIONS:
                for t in tp.EXCEPTIONS[w].split():
                    s = int(t[-1]) if t[-1].isdigit() else 0
                    out.append(10 * tb.CODE[t.rstrip('012')] + (0 if fn else s))
                out.append(-20)
            else:
                out += word + [-14 if fn else -13]
            word = []
        else:
            out.append(c)
    return out


def rules(cards):
    """ctx.cq, filter.cq and rule.cq together: each word (letters, -13 or -14) -> its phonemes by the NRL rules
    (10 x code), then the same end card."""
    out = []
    word = []
    for c in cards:
        if 1 <= c <= 28:
            word.append(c)
        elif c in (-13, -14):
            out += match_word(word) + [c]
            word = []
        else:
            out.append(c)
    return out


def post(cards):
    """post.cq: each word's phonemes (-13, or -14 for a function word) -> one of each run of a consonant, then the
    stress: a function word none; else the first vowel other than AX 1, the other long vowels (codes 3-12) 2 but
    not IY at the end, the rest 0; with no vowel but AX the first AX becomes AH 1.  Then -20."""
    out = []
    phs = []
    for c in cards:
        if c in (-13, -14):
            p = [x // 10 for x in phs]
            p = [x for i, x in enumerate(p) if i == 0 or x != p[i - 1] or 3 <= x <= 18]
            fn = c == -14
            res = []
            primary = fn
            for i, x in enumerate(p):
                if 3 <= x <= 18:
                    if not primary and x != AX:
                        res.append(10 * x + 1); primary = True
                    elif not fn and 3 <= x <= 12 and not (x == 3 and i == len(p) - 1):
                        res.append(10 * x + 2)
                    else:
                        res.append(10 * x)
                else:
                    res.append(10 * x)
            if not primary:
                for i, x in enumerate(res):
                    if x == 10 * AX:
                        res[i] = 10 * AH + 1
                        break
            out += res + [-20]
            phs = []
        elif c < 0:
            out += phs + [c]             # a finished word (or a part of a spelled one), or punctuation: as it is
            phs = []
        else:
            phs.append(c)
    return out


def join(cards):
    """join.cq: finished words (phonemes, -20), boundaries inside spelled words (-1), punctuation, -9 -> the front
    end's tokens: -1 between words, a pause card for punctuation, a period at the end if the text did not end a
    sentence, -9."""
    out = []
    pend = False
    last = 0          # 0 nothing yet, 1 a phoneme, 2 a boundary or punctuation
    started = False   # inside a word
    for c in cards:
        if c >= 30:
            if not started:
                started = True
                if last == 1:
                    pend = True
            if pend:
                out.append(-1); last = 2; pend = False
            out.append(c); last = 1
        elif c == -20:
            if not started and last == 1:
                pend = True
            started = False
        elif c == -1:
            out.append(-1); last = 2
        elif c in (-2, -3, -4, -5):
            pend = False
            out.append(c); last = 2
        elif c == -9:
            if pend:
                out.append(-1); last = 2
            if not out or out[-1] not in (-3, -4, -5):
                out.append(-3)
            out.append(-9)
    return out


def compose(text):
    return join(post(rules(exc(spell(spcls(num(scan(text))))))))


def numd(cards):
    """numd.cq: digits (500 + d) up to -12 -> with seven or more digits after the leading zeros, a word for each
    digit (700 + d); else -15, the count of digits after the leading zeros, and the last six digits."""
    out = []
    ds = []
    for c in cards:
        if 500 <= c <= 509:
            d = c - 500
            if ds or d:
                ds.append(d)
        elif c == -12:
            if len(ds) >= 7:
                out += [700 + d for d in ds]
            else:
                six = [0] * (6 - len(ds)) + ds
                out += [-15, len(ds)] + six
            ds = []
        else:
            out.append(c)
    return out


def words2(t, o):
    if t == 0:
        return [o] if o else []
    if t == 1:
        return [10 + o]
    return [18 + t] + ([o] if o else [])


def words3(h, t, o):
    return ([h, 28] if h else []) + words2(t, o)


def numw(cards):
    """numw.cq: -15, count, six digits -> the number's words as 700 + their number in the numbers deck: a year
    1100-1999 in pairs (nineteen hundred, nineteen oh five, nineteen sixty eight), zero for 0, else thousands and
    the rest by hundreds, tens and ones."""
    out = []
    i = 0
    while i < len(cards):
        c = cards[i]
        if c == -15:
            n, d5, d4, d3, d2, d1, d0 = cards[i + 1:i + 8]
            i += 8
            if n == 4 and d3 == 1 and d2 >= 1:
                w = words2(d3, d2)
                if d1 == 0 and d0 == 0:
                    w += [28]
                elif d1 == 0:
                    w += [30, d0]
                else:
                    w += words2(d1, d0)
            elif n == 0:
                w = [0]
            else:
                w = []
                if d5 or d4 or d3:
                    w += words3(d5, d4, d3) + [29]
                w += words3(d2, d1, d0)
            out += [700 + k for k in w]
            continue
        out.append(c)
        i += 1
    return out


def numf(cards):
    """numf.cq: 700 + k -> number word k's letters from the numbers deck, -10, 2."""
    out = []
    for c in cards:
        if c >= 700:
            k = c - 700
            rec = NUMBERS[k * tt.NUMBER_SIZE:(k + 1) * tt.NUMBER_SIZE]
            out += [x for x in rec if x] + [2]
        else:
            out.append(c)
    return out


def numg(cards):
    """numw.cq: -15, count, six digits -> words (700 + k) and groups (-16 h t o) for say3."""
    out = []
    i = 0
    while i < len(cards):
        c = cards[i]
        if c == -15:
            n, d5, d4, d3, d2, d1, d0 = cards[i + 1:i + 8]
            i += 8
            if n == 4 and d3 == 1 and d2 >= 1:
                out += [-16, 0, d3, d2]
                if d1 + d0 == 0:
                    out.append(728)
                elif d1 == 0:
                    out += [730, 700 + d0]
                else:
                    out += [-16, 0, d1, d0]
            elif n == 0:
                out.append(700)
            else:
                if d5 + d4 + d3:
                    out += [-16, d5, d4, d3, 729]
                out += [-16, d2, d1, d0]
            continue
        out.append(c)
        i += 1
    return out


def say3(cards):
    out = []
    i = 0
    while i < len(cards):
        if cards[i] == -16:
            h, t, o = cards[i + 1:i + 4]
            i += 4
            out += [700 + k for k in words3(h, t, o)]
            continue
        out.append(cards[i])
        i += 1
    return out


def spdec(cards):
    """spcls.cq: the flag, then words (letters, -10, lw) -> the letters and -11 (spelled) or -10."""
    lowt = cards[0]
    out = []
    i = 1
    word = []
    while i < len(cards):
        c = cards[i]
        if 1 <= c <= 28:
            word.append(c)
            out.append(c)
        elif c == -10:
            lw = cards[i + 1]; i += 1
            letters = [x for x in word if x != 27]
            L = len(letters)
            hv = any(x <= 5 for x in letters)
            up = lw != 1 and L >= 1
            caps = lw == 2 or not lowt
            sp = up and ((L == 1 and letters[0] not in (1, 5)) or (L >= 2 and (not caps or not hv)))
            out.append(-11 if sp else -10)
            word = []
        else:
            out.append(c)
        i += 1
    return out


def spmark(cards):
    """spell.cq: words ended by -11 -> letters 100 + code (the last 200 + code), apostrophes dropped, -11."""
    out = []
    word = []
    for c in cards:
        if 1 <= c <= 28:
            word.append(c)
        elif c in (-10, -11):
            if c == -10:
                out += word + [-10]
            else:
                letters = [x for x in word if x != 27]
                out += [(200 if k == len(letters) - 1 else 100) + x for k, x in enumerate(letters)] + [-11]
            word = []
        else:
            out.append(c)
    return out


def excl(cards):
    """excl.cq: words (letters, -10) -> letters, -10, fn (1 a function word), k (its number among the
    exceptions, 0 for none)."""
    out = []
    word = []
    for c in cards:
        if 1 <= c <= 28:
            word.append(c)
        elif c == -10:
            w = ''.join(tt.ORDER[x - 1] if x <= 26 else "'" for x in word)
            k = -100 - (tt.EXCEPTION_WORDS.index(w) + 1) if w in tp.EXCEPTIONS else 0
            out += word + [-99, 1 if w in tp.FUNCTION_WORDS else 0, k]
            word = []
        else:
            out.append(c)
    return out


def excp(cards):
    out = []
    word = []
    i = 0
    while i < len(cards):
        c = cards[i]
        if 1 <= c <= 28:
            word.append(c)
        elif c == -99:
            fn, k = cards[i + 1], cards[i + 2]
            i += 2
            k = -k - 100 if k else 0
            if k:
                for p in EXPHON[k * tt.EXPHON_SIZE:(k + 1) * tt.EXPHON_SIZE]:
                    if p:
                        out.append(p - p % 10 if fn else p)
                out.append(-20)
            else:
                out += word + [-14 if fn else -13]
            word = []
        else:
            out.append(c)
        i += 1
    return out


def posta(cards):
    """posta.cq: a consonant (190 and up) the same as the card before it is dropped; a card below 0 clears."""
    out = []
    prev = 0
    for c in cards:
        if c < 0:
            prev = 0
            out.append(c)
        elif c == prev and c >= 190:
            continue
        else:
            prev = c
            out.append(c)
    return out


def postb(cards):
    """postb.cq: a rules word (phonemes, -13 or -14) -> -30, fn, ah, its phonemes (the last as -100 - it), -20;
    anything else as it was."""
    out = []
    buf = []
    for c in cards:
        if c >= 0:
            buf.append(c)
        elif c in (-13, -14):
            fn = 1 if c == -14 else 0
            hv = any(x < 180 for x in buf)
            ah = 1 if (not fn and not hv) else 0
            out += [-30, fn, ah] + buf[:-1] + ([-100 - buf[-1]] if buf else []) + [-20]
            buf = []
        else:
            out += buf + [c]
            buf = []
    return out


def postc(cards):
    out = []
    i = 0
    mode = 0
    while i < len(cards):
        x = cards[i]
        if not mode:
            if x == -30:
                fn, ah = cards[i + 1], cards[i + 2]
                prim = fn
                mode = 1
                i += 3
                continue
            out.append(x)
            i += 1
            continue
        if x == -20:
            out.append(x)
            mode = 0
            i += 1
            continue
        lst = 0
        p = x
        if x <= -100:
            lst, p = 1, -x - 100
        if p < 190:
            if not prim:
                if p < 180:
                    p += 1; prim = 1
                elif ah:
                    p = 151; ah = 0
            elif not fn and p < 130 and not (p == 30 and lst):
                p += 2
        out.append(p)
        i += 1
    return out
