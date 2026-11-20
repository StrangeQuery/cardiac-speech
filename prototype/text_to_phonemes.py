#!/opt/homebrew/bin/python3
"""English text -> phonemes with stress, by letter-to-sound rules.

usage: text_to_phonemes.py "sentence" [out.phon]

The rules are version 3 of the Naval Research Laboratory English-to-IPA rules (Elovitz, Johnson, McHugh
and Shore, NRL Report 7948, 1976, Table 6), transcribed from the scanned report; the matcher below is
written from the report's description of the algorithm (scan left to right, for each letter try that
letter's rules in order, the first rule whose left context, bracketed text and right context all match
wins, emit its phonemes, skip the bracketed letters).  The phoneme names are the report's (ARPAbet-like).

Added here (not from the report, written for this program): a short exception list for common words the
rules get wrong, letter names for spelled-out words, number words, and a stress heuristic (the rules give
no stress).  See TTS_SOURCES.md.

Output: one token per phoneme, vowels carrying a stress digit (0 none, 1 primary, 2 secondary), "#" between
words, and the punctuation tokens , . ? ! as pauses.  Spelled-out letters are marked by a leading "~" on
the word's first phoneme only for the reader's benefit; the frame builder ignores it.
"""
import re
import sys

VOWELS = 'AEIOUY'
CONSONANTS = 'BCDFGHJKLMNPQRSTVWXZ'
VOICED = 'BDVGJLMNRWZ'

# --- NRL Report 7948, Table 6: version 3 of the English-to-IPA rules, in the report's order. ---------
# Notation (report Table 2): #  one or more vowels      *  one or more consonants
#   .  a voiced consonant (B D V G J L M N R W Z)       $  one consonant followed by E or I
#   %  a suffix (ER E ES ED ING ELY)                    &  a sibilant (S C G Z X J CH SH)
#   @  T S R D L Z N J TH CH SH                         ^  one consonant
#   +  a front vowel (E I Y)                            :  zero or more consonants
#   a blank: the edge of a word.   Each rule is  left[text]right=/phonemes/.
RULES_TEXT = r"""
[A] =/AX/
 [ARE] =/AA R/
 [AR]O=/AX R/
[AR]#=/EH R/
 ^[AS]#=/EY S/
[A]WA=/AX/
[AW]=/AO/
 :[ANY]=/EH N IY/
[A]^+#=/EY/
#:[ALLY]=/AX L IY/
 [AL]#=/AX L/
[AGAIN]=/AX G EH N/
#:[AG]E=/IH JH/
[A]^+:#=/AE/
 :[A]^+ =/EY/
[A]^%=/EY/
 [ARR]=/AX R/
[ARR]=/AE R/
 :[AR] =/AA R/
[AR] =/ER/
[AR]=/AA R/
[AIR]=/EH R/
[AI]=/EY/
[AY]=/EY/
[AU]=/AO/
#:[AL] =/AX L/
#:[ALS] =/AX L Z/
[ALK]=/AO K/
[AL]^=/AO L/
 :[ABLE]=/EY B AX L/
[ABLE]=/AX B AX L/
[ANG]+=/EY N JH/
[A]=/AE/
 [BE]^#=/B IH/
[BEING]=/B IY IH NX/
 [BOTH] =/B OW TH/
 [BUS]#=/B IH Z/
[BUIL]=/B IH L/
[B]=/B/
 [CH]^=/K/
^E[CH]=/K/
[CH]=/CH/
 S[CI]#=/S AY/
[CI]A=/SH/
[CI]O=/SH/
[CI]EN=/SH/
[C]+=/S/
[CK]=/K/
[COM]%=/K AH M/
[C]=/K/
#:[DED] =/D IH D/
.E[D] =/D/
#^:E[D] =/T/
 [DE]^#=/D IH/
 [DO] =/D UW/
 [DOES]=/D AH Z/
 [DOING]=/D UW IH NX/
 [DOW]=/D AW/
[DU]A=/JH UW/
[D]=/D/
#:[E] =/ /
'^:[E] =/ /
 :[E] =/IY/
#[ED] =/D/
#:[E]D =/ /
[EV]ER=/EH V/
[E]^%=/IY/
[ERI]#=/IY R IY/
[ERI]=/EH R IH/
#:[ER]#=/ER/
[ER]#=/EH R/
[ER]=/ER/
 [EVEN]=/IY V EH N/
#:[E]W=/ /
@[EW]=/UW/
[EW]=/Y UW/
[E]O=/IY/
#:&[ES] =/IH Z/
#:[E]S =/ /
#:[ELY] =/L IY/
#:[EMENT]=/M EH N T/
[EFUL]=/F UH L/
[EE]=/IY/
[EARN]=/ER N/
 [EAR]^=/ER/
[EAD]=/EH D/
#:[EA] =/IY AX/
[EA]SU=/EH/
[EA]=/IY/
[EIGH]=/EY/
[EI]=/IY/
 [EYE]=/AY/
[EY]=/IY/
[EU]=/Y UW/
[E]=/EH/
[FUL]=/F UH L/
[F]=/F/
[GIV]=/G IH V/
 [G]I^=/G/
[GE]T=/G EH/
SU[GGES]=/G JH EH S/
[GG]=/G/
 B#[G]=/G/
[G]+=/JH/
[GREAT]=/G R EY T/
#[GH]=/ /
[G]=/G/
 [HAV]=/HH AE V/
 [HERE]=/HH IY R/
 [HOUR]=/AW ER/
[HOW]=/HH AW/
[H]#=/HH/
[H]=/ /
 [IN]=/IH N/
 [I] =/AY/
[IN]D=/AY N/
[IER]=/IY ER/
#:R[IED] =/IY D/
[IED] =/AY D/
[IEN]=/IY EH N/
[IE]T=/AY EH/
 :[I]%=/AY/
[I]%=/IY/
[IE]=/IY/
[I]^+:#=/IH/
[IR]#=/AY R/
[IZ]%=/AY Z/
[IS]%=/AY Z/
[I]D%=/AY/
+^[I]^+=/IH/
[I]T%=/AY/
#^:[I]^+=/IH/
[I]^+=/AY/
[IR]=/ER/
[IGH]=/AY/
[ILD]=/AY L D/
[IGN] =/AY N/
[IGN]^=/AY N/
[IGN]%=/AY N/
[IQUE]=/IY K/
[I]=/IH/
[J]=/JH/
 [K]N=/ /
[K]=/K/
[LO]C#=/L OW/
L[L]=/ /
#^:[L]%=/AX L/
[LEAD]=/L IY D/
[L]=/L/
[MOV]=/M UW V/
[M]=/M/
E[NG]+=/N JH/
[NG]R=/NX G/
[NG]#=/NX G/
[NGL]%=/NX G AX L/
[NG]=/NX/
[NK]=/NX K/
 [NOW] =/N AW/
[N]=/N/
[OF] =/AX V/
[OROUGH]=/ER OW/
#:[OR] =/ER/
#:[ORS] =/ER Z/
[OR]=/AO R/
 [ONE]=/W AH N/
[OW]=/OW/
 [OVER]=/OW V ER/
[OV]=/AH V/
[O]^%=/OW/
[O]^EN=/OW/
[O]^I#=/OW/
[OL]D=/OW L/
[OUGHT]=/AO T/
[OUGH]=/AH F/
 [OU]=/AW/
H[OU]S#=/AW/
[OUS]=/AX S/
[OUR]=/AO R/
[OULD]=/UH D/
^[OU]^L=/AH/
[OUP]=/UW P/
[OU]=/AW/
[OY]=/OY/
[OING]=/OW IH NX/
[OI]=/OY/
[OOR]=/AO R/
[OOK]=/UH K/
[OOD]=/UH D/
[OO]=/UW/
[O]E=/OW/
[O] =/OW/
[OA]=/OW/
 [ONLY]=/OW N L IY/
 [ONCE]=/W AH N S/
[ON'T]=/OW N T/
C[O]N=/AA/
[O]NG=/AO/
 ^:[O]N=/AH/
I[ON]=/AX N/
#:[ON] =/AX N/
#^[ON]=/AX N/
[O]ST =/OW/
[OF]^=/AO F/
[OTHER]=/AH DH ER/
[OSS] =/AO S/
#^:[OM]=/AH M/
[O]=/AA/
[PH]=/F/
[PEOP]=/P IY P/
[POW]=/P AW/
[PUT] =/P UH T/
[P]=/P/
[QUAR]=/K W AO R/
[QU]=/K W/
[Q]=/K/
 [RE]^#=/R IY/
[R]=/R/
[SH]=/SH/
#[SION]=/ZH AX N/
[SOME]=/S AH M/
#[SUR]#=/ZH ER/
[SUR]#=/SH ER/
#[SU]#=/ZH UW/
#[SSU]#=/SH UW/
#[SED] =/Z D/
#[S]#=/Z/
[SAID]=/S EH D/
^[SION]=/SH AX N/
[S]S=/ /
.[S] =/Z/
#:.E[S] =/Z/
#^:##[S] =/Z/
#^:#[S] =/S/
U[S] =/S/
 :#[S] =/Z/
 [SCH]=/S K/
[S]C+=/ /
#[SM]=/Z M/
#[SN]'=/Z AX N/
[S]=/S/
 [THE] =/DH AX/
[TO] =/T UW/
[THAT] =/DH AE T/
 [THIS] =/DH IH S/
 [THEY]=/DH EY/
 [THERE]=/DH EH R/
[THER]=/DH ER/
[THEIR]=/DH EH R/
 [THAN] =/DH AE N/
 [THEM] =/DH EH M/
[THESE] =/DH IY Z/
 [THEN]=/DH EH N/
[THROUGH]=/TH R UW/
[THOSE]=/DH OW Z/
[THOUGH] =/DH OW/
 [THUS]=/DH AH S/
[TH]=/TH/
#:[TED] =/T IH D/
S[TI]#N=/CH/
[TI]O=/SH/
[TI]A=/SH/
[TIEN]=/SH AX N/
[TUR]#=/CH ER/
[TU]A=/CH UW/
 [TWO]=/T UW/
[T]=/T/
 [UN]I=/Y UW N/
 [UN]=/AH N/
 [UPON]=/AX P AO N/
@[UR]#=/UH R/
[UR]#=/Y UH R/
[UR]=/ER/
[U]^ =/AH/
[U]^^=/AH/
[UY]=/AY/
 G[U]#=/ /
G[U]%=/ /
G[U]#=/W/
#N[U]=/Y UW/
@[U]=/UW/
[U]=/Y UW/
[VIEW]=/V Y UW/
[V]=/V/
 [WERE]=/W ER/
[WA]S=/W AA/
[WA]T=/W AA/
[WHERE]=/WH EH R/
[WHAT]=/WH AA T/
[WHOL]=/HH OW L/
[WHO]=/HH UW/
[WH]=/WH/
[WAR]=/W AO R/
[WOR]^=/W ER/
[WR]=/R/
[W]=/W/
[X]=/K S/
[YOUNG]=/Y AH NX/
 [YOU]=/Y UW/
 [YES]=/Y EH S/
 [Y]=/Y/
#^:[Y] =/IY/
#^:[Y]I=/IY/
 :[Y] =/AY/
 :[Y]#=/AY/
 :[Y]^+:#=/IH/
 :[Y]^#=/AY/
[Y]=/IH/
[Z]=/Z/
"""


def parse_rules(text):
    rules = {}
    for line in text.split('\n'):
        if not line.strip():
            continue
        m = re.match(r"^(.*)\[(.+)\](.*)=/(.*)/$", line)
        assert m, line
        left, mid, right, out = m.groups()
        rules.setdefault(mid[0], []).append((left, mid, right, out.split()))
    return rules


RULES = parse_rules(RULES_TEXT)
RULE_COUNT = sum(len(v) for v in RULES.values())

SUFFIXES = ('ELY', 'ING', 'ER', 'ES', 'ED', 'E')       # longest first; backtracking tries each


def _right(pat, text, i):
    """Does pattern `pat` match text starting at i (moving right)?  Backtracking."""
    if not pat:
        return True
    c, rest = pat[0], pat[1:]
    ch = text[i] if i < len(text) else ' '
    if c == ' ':
        return not ch.isalpha() and _right(rest, text, i + 1)
    if c == '#':                                   # one or more vowels
        j = i
        while j < len(text) and text[j] in VOWELS:
            j += 1
            if _right(rest, text, j):
                return True
        return False
    if c == ':':                                   # zero or more consonants
        j = i
        while True:
            if _right(rest, text, j):
                return True
            if j < len(text) and text[j] in CONSONANTS:
                j += 1
            else:
                return False
    if c == '*':                                   # one or more consonants
        j = i
        while j < len(text) and text[j] in CONSONANTS:
            j += 1
            if _right(rest, text, j):
                return True
        return False
    if c == '^':
        return ch in CONSONANTS and _right(rest, text, i + 1)
    if c == '.':
        return ch in VOICED and _right(rest, text, i + 1)
    if c == '+':
        return ch in 'EIY' and _right(rest, text, i + 1)
    if c == '$':
        return (ch in CONSONANTS and i + 1 < len(text) and text[i + 1] in 'EI'
                and _right(rest, text, i + 2))
    if c == '%':
        return any(text.startswith(s, i) and _right(rest, text, i + len(s)) for s in SUFFIXES)
    if c == '&':
        if text.startswith('CH', i) or text.startswith('SH', i):
            if _right(rest, text, i + 2):
                return True
        return ch in 'SCGZXJ' and _right(rest, text, i + 1)
    if c == '@':
        for two in ('TH', 'CH', 'SH'):
            if text.startswith(two, i) and _right(rest, text, i + 2):
                return True
        return ch in 'TSRDLZNJ' and _right(rest, text, i + 1)
    return ch == c and _right(rest, text, i + 1)


def _left(pat, text, i):
    """Does pattern `pat` match text ending at i (moving left from i)?  The pattern is read from its end."""
    if not pat:
        return True
    c, rest = pat[-1], pat[:-1]
    ch = text[i] if i >= 0 else ' '
    if c == ' ':
        return not ch.isalpha() and _left(rest, text, i - 1)
    if c == '#':
        j = i
        while j >= 0 and text[j] in VOWELS:
            j -= 1
            if _left(rest, text, j):
                return True
        return False
    if c == ':':
        j = i
        while True:
            if _left(rest, text, j):
                return True
            if j >= 0 and text[j] in CONSONANTS:
                j -= 1
            else:
                return False
    if c == '*':
        j = i
        while j >= 0 and text[j] in CONSONANTS:
            j -= 1
            if _left(rest, text, j):
                return True
        return False
    if c == '^':
        return ch in CONSONANTS and _left(rest, text, i - 1)
    if c == '.':
        return ch in VOICED and _left(rest, text, i - 1)
    if c == '+':
        return ch in 'EIY' and _left(rest, text, i - 1)
    if c == '$':          # consonant followed by E or I, read leftwards: E/I at i, consonant at i-1
        return ch in 'EI' and i >= 1 and text[i - 1] in CONSONANTS and _left(rest, text, i - 2)
    if c == '&':
        if i >= 1 and text[i - 1:i + 1] in ('CH', 'SH') and _left(rest, text, i - 2):
            return True
        return ch in 'SCGZXJ' and _left(rest, text, i - 1)
    if c == '@':
        if i >= 1 and text[i - 1:i + 1] in ('TH', 'CH', 'SH') and _left(rest, text, i - 2):
            return True
        return ch in 'TSRDLZNJ' and _left(rest, text, i - 1)
    if c == '%':
        return any(i - len(s) + 1 >= 0 and text[i - len(s) + 1:i + 1] == s and _left(rest, text, i - len(s))
                   for s in SUFFIXES)
    return ch == c and _left(rest, text, i - 1)


def rules_word(word, trace=None):
    """Letter-to-sound rules on one upper-case word (letters and apostrophes)."""
    text = ' ' + word + ' '
    out = []
    i = 1
    while i < len(text) - 1:
        c = text[i]
        if c not in RULES:          # apostrophe etc.: silent
            i += 1
            continue
        for left, mid, right, ph in RULES[c]:
            if (text.startswith(mid, i) and _left(left, text, i - 1)
                    and _right(right, text, i + len(mid))):
                out.extend(ph)
                if trace is not None:
                    trace.append('%s[%s]%s=/%s/' % (left, mid, right, ' '.join(ph)))
                i += len(mid)
                break
        else:
            raise ValueError('no rule for %r in %r' % (c, word))
    return out


# --- written for this program (not from the NRL report) ------------------------------------------------

VOWEL_PH = {'IY', 'IH', 'EY', 'EH', 'AE', 'AA', 'AO', 'OW', 'UH', 'UW', 'ER', 'AX', 'AH', 'AY', 'AW', 'OY'}

# Common words the rules get wrong (checked by running the rules), plus words whose stress the
# heuristic would misplace.  Pronunciations written by hand; stress digits on vowels.
EXCEPTIONS = {
    'SEVENTEEN': 'S EH1 V AX0 N T IY2 N',   # rules: S IY V EH N T IY N
    'NINETEEN': 'N AY1 N T IY2 N',  # rules: N IH N IY T IY N
    'SEVENTY': 'S EH1 V AX0 N T IY0',      # rules: S IY V EH N T IY
    'NINETY': 'N AY1 N T IY0',      # rules: N IH N EH T IY
    'OH': 'OW1',                    # rules: AA
    'CARDIAC': 'K AA1 R D IY0 AE2 K',   # CAR-dee-ack, a full but unstressed IY; rules: K AA R D IH AE K, the IH swallowed
    'FATHER': 'F AA1 DH ER0',          # rules: F AE DH ER
    'HAGELBARGER': 'HH EY1 G AX0 L B AA2 R G ER0',   # HAIG-uhl-bar-grr; rules give soft Gs
    'LIVED': 'L IH1 V D',            # rules: L AY V D
    'HAPPENED': 'HH AE1 P AX0 N D',  # rules: HH AE P IY N D
    'UNLEASHED': 'AH0 N L IY1 SH T', # rules: AH N AX L IY SH T, stressed on UN
    'MILLIONS': 'M IH1 L Y AX0 N Z', # rules: M IH L IH AX N Z
    'MILLION': 'M IH1 L Y AX0 N',
    'DOESN\'T': 'D AH1 Z AX0 N T',  # rules: D AH Z N T
    'IMAGINATION': 'IH0 M AE2 JH IH0 N EY1 SH AX0 N',   # rules put the stress on the first syllable
    'BELONG': 'B IH0 L AO1 NX',      # rules: stressed on the first syllable
    'SURVIVE': 'S ER0 V AY1 V',      # rules: S ER V IH V, stressed on the first syllable
    'COOPERATE': 'K OW0 AA1 P ER0 EY2 T',     # rules read COOP as one syllable (K UW P)
    'COOPERATES': 'K OW0 AA1 P ER0 EY2 T S',
    'COOPERATED': 'K OW0 AA1 P ER0 EY2 T IH0 D',
    'COOPERATING': 'K OW0 AA1 P ER0 EY2 T IH0 NX',
    'COOPERATION': 'K OW0 AA2 P ER0 EY1 SH AX0 N',
    'COOPERATIVE': 'K OW0 AA1 P ER0 AX0 T IH0 V',
    'ACRONYM': 'AE1 K R AX0 N IH0 M',
    'ILLUSTRATIVE': 'IH0 L AH1 S T R AX0 T IH0 V',
    'COMPUTATION': 'K AA2 M P Y UW0 T EY1 SH AX0 N',
    'OPERATION': 'AA2 P ER0 EY1 SH AX0 N',
    'WITHOUT': 'W IH0 DH AW1 T',
    'EVEN': 'IY1 V AX0 N',
    'COMPUTING': 'K AX0 M P Y UW1 T IH0 NX',
    'COMPUTERS': 'K AX0 M P Y UW1 T ER0 Z',
    'UNDERSTAND': 'AH2 N D ER0 S T AE1 N D',
    'UNDERSTANDING': 'AH2 N D ER0 S T AE1 N D IH0 NX',
    'PROGRAMMING': 'P R OW1 G R AE2 M IH0 NX',
    'ABOUT': 'AX0 B AW1 T',
    'EFFORT': 'EH1 F ER0 T',
    'BEHIND': 'B IH0 HH AY1 N D',
    'HELLO': 'HH AX0 L OW1',         # rules: HH EH L OW (stress would land on the first syllable)
    'WANT': 'W AA1 N T',             # rules: W AE N T
    'WANTS': 'W AA1 N T S',
    'SAYS': 'S EH1 Z',               # rules: S EY Z
    'BEEN': 'B IH1 N',               # rules: B IY N
    'YOUR': 'Y AO1 R',               # rules: Y UW R
    'ZERO': 'Z IY1 R OW2',           # rules: Z EH R OW
    'COMPUTER': 'K AX0 M P Y UW1 T ER0',   # rules: K AA M P Y UW T ER
    'MACHINE': 'M AX0 SH IY1 N',     # rules: M AE CH IH N
    'WOMEN': 'W IH1 M IH0 N',        # rules: W OW M EH N
    'DONE': 'D AH1 N',               # rules: D OW N
    'GONE': 'G AO1 N',               # rules: G OW N
    'FRIEND': 'F R EH1 N D',         # rules: F R IY EH N D
    'SEVEN': 'S EH1 V AX0 N',        # rules: S IY V EH N
    'ELEVEN': 'IH0 L EH1 V AX0 N',   # rules: IY L IY V EH N
    'HUNDRED': 'HH AH1 N D R IH0 D', # rules: HH AH N D R D
    'THOUSAND': 'TH AW1 Z AX0 N D',  # rules: TH AW Z AE N D (stress right, vowel full)
    'OKAY': 'OW2 K EY1',             # rules: AA K EY
    'LISTEN': 'L IH1 S AX0 N',       # rules: L IH S T EH N
    'OFTEN': 'AO1 F AX0 N',          # rules: AO F T EH N
    'BROWN': 'B R AW1 N',            # rules: B R OW N ([OW]=/OW/ has no AW case)
    'DOWN': 'D AW1 N',
    'TOWN': 'T AW1 N',
    'COW': 'K AW1',
    'CROWN': 'K R AW1 N',
    'POWER': 'P AW1 ER0',
}

# Words that take no primary stress in a sentence (function words; Klatt 1979 marks these #F).
FUNCTION_WORDS = {'A', 'AN', 'THE', 'OF', 'TO', 'IN', 'ON', 'AT', 'AND', 'OR', 'BUT', 'IS', 'WAS', 'ARE',
                  'WERE', 'BE', 'BEEN', 'AM', 'MY', 'YOUR', 'HIS', 'HER', 'ITS', 'OUR', 'THEIR', 'IT', 'FOR',
                  'WITH', 'FROM', 'BY', 'AS', 'THAT', 'THAN', 'SO', 'IF', 'HAS', 'HAVE', 'HAD', 'DO', 'DOES',
                  'CAN', 'WILL', 'SHALL', 'WOULD', 'COULD', 'SHOULD', 'ME', 'HIM', 'US', 'THEM', 'WE', 'HE',
                  'SHE', 'THEY', 'YOU', 'I'}

LETTERS = {
    'A': 'EY', 'B': 'B IY', 'C': 'S IY', 'D': 'D IY', 'E': 'IY', 'F': 'EH F', 'G': 'JH IY', 'H': 'EY CH',
    'I': 'AY', 'J': 'JH EY', 'K': 'K EY', 'L': 'EH L', 'M': 'EH M', 'N': 'EH N', 'O': 'OW', 'P': 'P IY',
    'Q': 'K Y UW', 'R': 'AA R', 'S': 'EH S', 'T': 'T IY', 'U': 'Y UW', 'V': 'V IY',
    'W': 'D AH B AX L Y UW', 'X': 'EH K S', 'Y': 'W AY', 'Z': 'Z IY',
}

ONES = ['ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN', 'ELEVEN',
        'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN', 'SEVENTEEN', 'EIGHTEEN', 'NINETEEN']
TENS = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY']


def number_words(n):
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + (number_words(n % 10) if n % 10 else [])
    if n < 1000:
        return [ONES[n // 100], 'HUNDRED'] + (number_words(n % 100) if n % 100 else [])
    if n < 1000000:
        return number_words(n // 1000) + ['THOUSAND'] + (number_words(n % 1000) if n % 1000 else [])
    return [ONES[int(d)] for d in str(n)]


def say_number(n):
    """A number as it is spoken: 1100 to 1999 in pairs, as a year usually is (nineteen sixty-eight, nineteen
    hundred, nineteen oh five); anything else as number_words reads it."""
    if 1100 <= n <= 1999:
        hi, lo = divmod(n, 100)
        if lo == 0:
            return number_words(hi) + ['HUNDRED']
        return number_words(hi) + (['OH', ONES[lo]] if lo < 10 else number_words(lo))
    return number_words(n)


def stress_rules(phs, function_word):
    """Stress heuristic (mine, not the report's): a content word's primary stress goes on its first vowel
    other than AX; other long vowels and diphthongs get secondary stress; AX, IH, ER etc. stay unstressed.
    A function word gets no stress at all."""
    out = []
    primary_done = function_word
    for i, p in enumerate(phs):
        if p in VOWEL_PH:
            if not primary_done and p != 'AX':
                out.append(p + '1')
                primary_done = True
            elif (not function_word and p in ('EY', 'AY', 'OW', 'AW', 'OY', 'IY', 'UW', 'AA', 'AO', 'AE')
                  and not (p == 'IY' and i == len(phs) - 1)):     # final -Y (LAZY) stays unstressed
                out.append(p + '2')
            else:
                out.append(p + '0')
        else:
            out.append(p)
    if not primary_done:     # only AX vowels: stress the first one
        for i, p in enumerate(out):
            if p == 'AX0':
                out[i] = 'AH1'
                break
    return out


def spell(word):
    """Letters said as letters: each letter's name, secondary stress, primary on the last (em tee VEE)."""
    out = []
    for i, ch in enumerate(word):
        last = i == len(word) - 1
        phs = LETTERS[ch].split()
        done = False
        for p in phs:
            if p in VOWEL_PH:
                if not done and p != 'AX':
                    out.append(p + ('1' if last else '2'))
                    done = True
                else:
                    out.append(p + '0')
            else:
                out.append(p)
        if not last:
            out.append('#')
    return out


def word_phonemes(word, all_caps_text):
    up = word.upper()
    letters_only = up.replace("'", '')
    # a single capital other than A and I is an initial, spoken as its letter name (D W Hagelbarger)
    if word.isupper() and len(letters_only) == 1 and letters_only not in 'AI':
        return spell(letters_only), 'spelled'
    if word.isupper() and len(letters_only) >= 2 and (not all_caps_text or not any(v in letters_only for v in 'AEIOU')):
        return spell(letters_only), 'spelled'
    if up in EXCEPTIONS:
        phs = EXCEPTIONS[up].split()
        if up in FUNCTION_WORDS:
            phs = [p[:-1] + '0' if p[-1].isdigit() else p for p in phs]
        return phs, 'exception'
    phs = rules_word(up)
    # The rules have no doubled-consonant rules for most letters (LITTLE gives T T): one consonant
    # phoneme per run of identical ones.  Added here, not in the report.
    phs = [p for i, p in enumerate(phs) if i == 0 or p != phs[i - 1] or p in VOWEL_PH]
    return stress_rules(phs, up in FUNCTION_WORDS), 'rules'


def text_to_phonemes(text, report=None):
    all_caps_text = text.upper() == text
    toks = re.findall(r"[A-Za-z']+|\d+|[.,!?;:]", text)
    out = []
    for t in toks:
        if t[0].isdigit():
            words = say_number(int(t))
        elif t in '.,!?;:':
            p = {';': ',', ':': ','}.get(t, t)
            if out and out[-1] == '#':
                out.pop()
            out.append(p)
            continue
        else:
            words = [t]
        for w in words:
            phs, how = word_phonemes(w, all_caps_text or t[0].isdigit())
            if report is not None:
                report.append((w, how, ' '.join(phs)))
            if out and out[-1] not in ('#', ',', '.', '?', '!'):
                out.append('#')
            out.extend(phs)
    if not out or out[-1] not in ('.', '?', '!'):
        out.append('.')
    return out


if __name__ == '__main__':
    rep = []
    ph = text_to_phonemes(sys.argv[1], rep)
    for w, how, p in rep:
        print('%-12s %-9s %s' % (w, how, p), file=sys.stderr)
    line = ' '.join(ph)
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w') as f:
            f.write('# ' + sys.argv[1].replace('\n', ' ') + '\n' + line + '\n')
    print(line)
