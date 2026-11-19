#!/usr/bin/env python3
"""The speech engine as a pipeline of CARDIAC machines: docs/pipeline.svg, laid out by hand.

The machines are read from the code: every net.add("name", LISTING, ...) in src/text.rs, src/front.rs and
src/voice.rs, and each listing's file from its include_str!. The script stops if a machine in the code is missing
from the diagram, or the diagram shows one the code doesn't run, so the picture can't drift from the wiring. The
stages, their descriptions and the labels on the arrows are written here by hand from the listings' comments.

  python3 docs/diagram.py              writes docs/pipeline.svg
  python3 docs/diagram.py --png OUT    also screenshots it to OUT with Playwright (headless Chromium)
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INK = "#1a1a1a"
FLOW = "#9a3b1b"
GREY = "#6a6a6a"
HOSTFILL = "#f4f1ea"
CHIPFILL = "#f3f6f8"
CHIPSTROKE = "#9aa7b0"
BG = "#fcfcfa"

COLW = 500
COLX = [56 + i * 680 for i in range(5)]
TOP = 190
PAD = 12
CHIP_H, CHIP_GAP = 22, 6


# --- the machines, from the code ---------------------------------------------------------------------------------
def machines():
    """[(phase, name, listing path relative to the repo)] in the order the host adds them."""
    out = []
    for phase, rs, folder in (("text", "text.rs", "text"), ("front", "front.rs", "front"), ("voice", "voice.rs", "voice")):
        src = (ROOT / "src" / rs).read_text()
        files = {m[1]: f"{folder}/{m[2]}" for m in re.finditer(r'(\w+) = "(\w+\.cq)"', src)}
        files.update({m[1]: m[2] for m in re.finditer(r'const (\w+): &str = include_str!\("\.\./(\w+/\w+\.cq)"\)', src)})
        for m in re.finditer(r'net\.add\("(\w+)", (\w+)', src):
            out.append((phase, m[1], files[m[2]]))
    return out


def cells(listing):
    """The cells a listing fills (each line that starts with an address)."""
    return len({l[2:4] for l in (ROOT / listing).read_text().splitlines() if re.match(r"^  \d\d ", l)})


# --- the stages --------------------------------------------------------------------------------------------------
# (id, column, title, when, what, machines, chip columns)
GROUPS = [
    ("words", 0, "Words and numbers", "ONCE A CHARACTER, THEN ONCE A NUMBER",
     "scan reads the text twice (is it all capitals?), sorts each character by its row of the ASCII table, and cuts "
     "words, numbers and punctuation; numbers become words, years in pairs",
     ["scan", "numd", "numw", "say3", "numf"], 5),
    ("spell", 0, "Spelled words and exceptions", "ONCE A WORD",
     "which all-capital words are spelled out, letter by letter by name; the function words and the hand-written "
     "exceptions, looked up in a deck read through for each word",
     ["spcls", "spell", "names", "excl", "excp"], 5),
    ("rules", 0, "Letter-to-sound rules (NRL, 1976)", "ONCE A LETTER, RULE BY RULE",
     "the letter's section of the rule deck; each rule's left and right contexts tested by two machines, one reading "
     "each way through the word; the first rule that matches gives the phonemes",
     ["loader", "filter", "rule", "ctxl", "ctxr"], 5),
    ("post", 0, "Doubled consonants, stress, joins", "ONCE A PHONEME",
     "one of each run of the same consonant; primary stress on a content word's first full vowel, secondary on the "
     "other long ones; boundaries between words, pauses, the end",
     ["posta", "postb", "postc", "join"], 5),

    ("feat", 1, "Segments", "ONCE A PHONEME OR PAUSE",
     "an 11-card record for each segment: its code, stress, word start, pause length, sentence end, and six cards of "
     "its row of the phoneme table",
     ["feat"], 5),
    ("ahead", 1, "What lies ahead", "ONCE A SEGMENT, LAST FIRST",
     "run on the records in reverse, so each segment learns what comes after it in its word: a vowel later, the next "
     "vowel's stress, the next sound's kind and filters",
     ["after", "ahead", "next"], 5),

    ("dur", 2, "Durations (Klatt, 1979)", "ONCE A SEGMENT",
     "a consonant's stress; Klatt's rules 2 to 11 as lists of factors in hundredths, multiplied into PRCNT; "
     "DUR = (INHDUR - MINDUR) PRCNT / 100 + MINDUR; whole 25 ms frames",
     ["stress", "base", "rules2", "rules9", "mul", "nframes"], 5),
    ("frames", 2, "Frames", "ONCE A SEGMENT, THEN ONCE A FRAME",
     "the segment before each one; a summary of each sentence for the pitch; each frame's place in its segment, in "
     "tenths, and the weights of the glides at its ends",
     ["back", "sum", "framer"], 5),

    ("pitch", 3, "Pitch", "ONCE A FRAME",
     "130 Hz falling to 100 across the sentence, a rise at stressed vowels, the fall (85 Hz) or rise (160 Hz) at the "
     "end, and the pitch period, 8000 / f0 samples",
     ["decl", "rise", "taily", "tailf", "period"], 5),
    ("filters", 3, "Filters and glides", "ONCE A FRAME",
     "a stop's closure and burst, aspiration after P T K, each frame's two target filters blended by its place, the "
     "glides at the segment's ends; a silent frame keeps the filter before it",
     ["closure", "main", "edge", "choose", "glides", "glidea", "glideb", "kcarry"], 5),
    ("level", 3, "Level", "ONCE A FRAME",
     "the filter's gain times a sonorant's loudness, 3 dB down when unstressed, falling across a vowel, and times "
     "sqrt(60 P) / 100 so a pulse carries the frame's power",
     ["lsel", "vsel", "psel", "mulx1", "mulx2", "mulx3", "mulx4"], 5),
    ("asm", 3, "Frame cards", "ONCE A FRAME",
     "each frame as the voice box reads it, a frame behind: V, P, A, K10 to K1",
     ["asm"], 5),

    ("interp", 4, "Frame glides", "ONCE A FRAME, THEN ONCE A STEP",
     "each value's step to the next frame, (next - this) / 10 by one SFT, none across a change of voicing; ten steps "
     "of 20 samples a frame",
     ["interp", "steps"], 5),
    ("reduce", 4, "Coefficient digits", "TEN TIMES A STEP",
     "each K as two digits, a sign and a shift: five cards that become the multiply routine",
     ["reduce"], 2),
    ("excite", 4, "Excitation", "ONCE A SAMPLE",
     "a pulse of height A every P samples, or +A and -A from a decimal random number generator",
     ["excite"], 2),
    ("lattice", 4, "The lattice filter, ten stages", "ONCE A SAMPLE",
     "five machines of two stages each: f goes down from L1 to L5, each b goes back up one machine; every multiply "
     "is a jump into a row of nine ADDs, an SFT and another jump",
     ["L1", "L2", "L3", "L4", "L5"], 5),
    ("output", 4, "De-emphasis and output", "ONCE A SAMPLE",
     "yd = f + 0.9 yd, kept as thousands and units; out goes 20 yd as two values, the thousands and then the units",
     ["output"], 5),
]

# (id, column, title, lines, height)
HOSTS = {
    "text": (0, "the text", ["ASCII codes, a card a character, then -1;", "dealt twice"], 66),
    "decks": (0, "text/*.cards", ["ASCII rows, number words, letter names,", "exceptions, the rule deck (5,680 cards)"], 66),
    "rev": (1, "the records, last first", ["the host puts the segment records", "in the opposite order"], 66),
    "fwd": (1, "back in order, by columns", ["each machine dealt the columns of the", "records it reads, collated a port"], 66),
    "table": (1, "front/features.cards, filters.cards", ["the phoneme table and the filters:", "the one precomputed part (ref/table.py)"], 66),
    "samples": (4, "standard output", ["8 kHz signed 16-bit little-endian:", "the host joins thousands x 1000 + units"], 66),
}

PHASES = [
    ("text", [0], "TEXT TO PHONEMES"),
    ("front", [1, 2, 3], "FRONT END: PHONEMES TO FRAME CARDS"),
    ("voice", [4], "VOICE BOX: FRAME CARDS TO SAMPLES"),
]


def esc(s):
    return html.escape(s, quote=True)


def text_w(s, size):
    return len(s) * size * 0.54


def wrap(s, size, width):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_w(t, size) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def group_width(gid):
    return (COLW - 20) / 2 if gid in ("reduce", "excite") else COLW


def group_height(g):
    gid, _, _, _, what, ms, cols = g
    lines = wrap(what, 12, group_width(gid) - 2 * PAD)
    rows = (len(ms) + cols - 1) // cols
    return 62 + 15 * len(lines) + rows * (CHIP_H + CHIP_GAP) + PAD - CHIP_GAP + 6


def layout():
    order = {
        0: [("h", "text", 0), ("g", "words", 56), ("g", "spell", 64), ("g", "rules", 64), ("g", "post", 64),
            ("h", "decks", 56)],
        1: [("g", "feat", 0), ("h", "rev", 56), ("g", "ahead", 56), ("h", "fwd", 56), ("h", "table", 150)],
        2: [("g", "dur", 0), ("g", "frames", 64)],
        3: [("g", "pitch", 0), ("g", "filters", 64), ("g", "level", 64), ("g", "asm", 64)],
        4: [("g", "interp", 0), ("g", "reduce", 64), ("g", "lattice", 64), ("g", "output", 56), ("h", "samples", 56)],
    }
    gs = {g[0]: g for g in GROUPS}
    rect = {}
    for col, items in order.items():
        y = TOP
        for kind, gid, gap in items:
            y += gap
            h = group_height(gs[gid]) if kind == "g" else HOSTS[gid][3]
            rect[gid] = (COLX[col], y, group_width(gid) if kind == "g" else COLW, h)
            y += h
    x, y, w, h = rect["reduce"]
    rect["excite"] = (x + w + 20, y, w, h)
    return rect


class Svg:
    def __init__(self):
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, cls, anchor=None):
        a = f' text-anchor="{anchor}"' if anchor else ""
        self.add(f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}"{a}>{esc(s)}</text>')


WIRES, LABELS = [], []


def arrow(pts, head=True):
    WIRES.append((pts, head))


def label(x, y, lines, anchor=None):
    LABELS.append((x, y, [lines] if isinstance(lines, str) else lines, anchor))


def draw_wires(svg):
    """Every wire, a horizontal run hopping over any other wire's vertical run it crosses."""
    verts = []
    for i, (pts, _) in enumerate(WIRES):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if abs(x0 - x1) < 0.5:
                verts.append((i, x0, min(y0, y1), max(y0, y1)))
    r = 6
    for i, (pts, head) in enumerate(WIRES):
        d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if abs(y0 - y1) < 0.5 and abs(x0 - x1) > 0.5:
                lo, hi = min(x0, x1), max(x0, x1)
                xs = sorted({round(vx, 1) for j, vx, a, b in verts
                             if j != i and lo + r < vx < hi - r and a + 0.5 < y0 < b - 0.5}, reverse=x1 < x0)
                sgn = 1 if x1 > x0 else -1
                for vx in xs:
                    d += f" L{vx - sgn * r:.1f} {y0:.1f} A{r} {r} 0 0 {1 if sgn > 0 else 0} {vx + sgn * r:.1f} {y0:.1f}"
            d += f" L{x1:.1f} {y1:.1f}"
        svg.add(f'<path class="{"flow" if head else "line"}" d="{d}"/>')


def draw_group(svg, g, r):
    gid, _, title, when, what, ms, cols = g
    x, y, w, h = r
    svg.add(f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>')
    svg.text(x + PAD, y + 22, title, "gtitle")
    svg.text(x + PAD, y + 39, when, "when")
    ty = y + 57
    for line in wrap(what, 12, w - 2 * PAD):
        svg.text(x + PAD, ty, line, "what")
        ty += 15
    cy = ty - 4
    cw = (w - 2 * PAD - (cols - 1) * 6) / cols
    for i, name in enumerate(ms):
        cx = x + PAD + (i % cols) * (cw + 6)
        yy = cy + (i // cols) * (CHIP_H + CHIP_GAP)
        svg.add(f'<rect class="chip" x="{cx:.1f}" y="{yy:.1f}" width="{cw:.1f}" height="{CHIP_H}" rx="5"/>')
        svg.text(cx + cw / 2, yy + 15.5, name, "mname", "middle")


def draw_host(svg, gid, r):
    _, title, lines, _ = HOSTS[gid]
    x, y, w, h = r
    svg.add(f'<rect class="host" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>')
    svg.text(x + PAD, y + 21, title, "htitle")
    for i, l in enumerate(lines):
        svg.text(x + PAD, y + 38 + 15 * i, l, "what")


def build():
    ms = machines()
    shown = [m for g in GROUPS for m in g[5]]
    in_code = [m for _, m, _ in ms]
    dup = sorted({m for m in shown if shown.count(m) > 1})
    assert not dup, f"shown twice: {dup}"
    missing, extra = sorted(set(in_code) - set(shown)), sorted(set(shown) - set(in_code))
    assert not missing and not extra, f"in the code but not drawn: {missing}; drawn but not in the code: {extra}"
    phase_of = {m: p for p, m, _ in ms}
    for g in GROUPS:
        want = {0: "text", 1: "front", 2: "front", 3: "front", 4: "voice"}[g[1]]
        assert all(phase_of[m] == want for m in g[5]), g[0]
    count = {p: sum(1 for q, _, _ in ms if q == p) for p in ("text", "front", "voice")}
    biggest = max(cells(f) for _, _, f in set(ms))

    rect = layout()
    WIRES.clear()
    LABELS.clear()
    R = lambda k: rect[k]
    L = lambda k, f=0.5: (R(k)[0], R(k)[1] + R(k)[3] * f)
    Rt = lambda k, f=0.5: (R(k)[0] + R(k)[2], R(k)[1] + R(k)[3] * f)
    T = lambda k, f=0.5: (R(k)[0] + R(k)[2] * f, R(k)[1])
    B = lambda k, f=0.5: (R(k)[0] + R(k)[2] * f, R(k)[1] + R(k)[3])
    gap = lambda col, f=0.5: COLX[col] + COLW + (COLX[1] - COLX[0] - COLW) * f
    down = lambda a, b, f=0.5: arrow([B(a, f), (B(a, f)[0], R(b)[1] - 2)])

    bottom = max(r[1] + r[3] for r in rect.values())
    W, H = COLX[4] + COLW + 32, bottom + 110

    svg = Svg()
    svg.add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'font-family="-apple-system, Helvetica, Arial, sans-serif" font-size="13" fill="{INK}">')
    svg.add("<title>Speech, as a pipeline of CARDIAC machines</title>")
    svg.add(f'''<defs>
  <marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{FLOW}"/></marker>
  <style>
    .box {{ fill: #ffffff; stroke: #333; stroke-width: 1.5; }}
    .host {{ fill: {HOSTFILL}; stroke: #333; stroke-width: 1.5; }}
    .chip {{ fill: {CHIPFILL}; stroke: {CHIPSTROKE}; stroke-width: 1; }}
    .phase {{ fill: none; stroke: #8a8a8a; stroke-width: 1.2; stroke-dasharray: 6 4; }}
    .phasename {{ fill: {GREY}; font-size: 12px; font-weight: 700; letter-spacing: 0.04em; }}
    .gtitle {{ font-size: 15px; font-weight: 700; }}
    .htitle {{ font: 700 14px ui-monospace, Menlo, monospace; }}
    .when {{ fill: {GREY}; font-size: 10.5px; font-weight: 700; letter-spacing: 0.04em; }}
    .what {{ fill: #444; font-size: 12px; }}
    .mname {{ font: 700 12px ui-monospace, Menlo, monospace; }}
    .flow {{ stroke: {FLOW}; stroke-width: 2; fill: none; marker-end: url(#a); }}
    .line {{ stroke: {FLOW}; stroke-width: 2; fill: none; }}
    .data {{ fill: {FLOW}; font-size: 12px; paint-order: stroke; stroke: {BG}; stroke-width: 4px; stroke-linejoin: round; }}
    .title {{ font-size: 30px; font-weight: 700; }}
    .sub {{ fill: #444; font-size: 15px; }}
    .legend {{ fill: #444; font-size: 12.5px; }}
  </style>
</defs>''')
    svg.add(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>')

    # --- the header -------------------------------------------------------------------------------------------
    svg.text(20, 50, "Speech, as a pipeline of CARDIAC machines", "title")
    svg.text(20, 82, f"{len(ms)} machines: {count['text']} turn text into phonemes, {count['front']} turn phonemes into "
             f"frame cards and {count['voice']} turn frame cards into 8 kHz samples; the largest fills {biggest} of its "
             "100 cells. The host deals the text and the decks, carries each machine's output cards on to the next, and "
             "joins each sample's two values.", "sub")
    lx, ly = 20, 108
    svg.add(f'<rect class="box" x="{lx}" y="{ly}" width="34" height="22" rx="6"/>')
    svg.add(f'<rect class="chip" x="{lx + 5}" y="{ly + 5}" width="24" height="12" rx="3"/>')
    svg.text(lx + 44, ly + 16, "a stage, its machines inside", "legend")
    lx += 250
    svg.add(f'<rect class="host" x="{lx}" y="{ly}" width="34" height="22" rx="6"/>')
    svg.text(lx + 44, ly + 16, "the host's cards and decks", "legend")
    lx += 240
    svg.add(f'<path class="flow" d="M{lx} {ly + 11} L{lx + 40} {ly + 11}"/>')
    svg.text(lx + 50, ly + 16, "cards the host carries", "legend")

    # --- the phases ---------------------------------------------------------------------------------------------
    for phase, cols, name in PHASES:
        x0 = COLX[cols[0]] - 26
        x1 = COLX[cols[-1]] + COLW + 16
        svg.add(f'<rect class="phase" x="{x0}" y="{TOP - 40}" width="{x1 - x0}" height="{bottom - TOP + 70}" rx="14"/>')
        svg.text(x0 + 14, TOP - 20, f"{name}, {count[phase]} MACHINES", "phasename")

    # --- text to phonemes ---------------------------------------------------------------------------------------
    down("text", "words")
    down("words", "spell")
    label(B("words")[0] + 8, B("words")[1] + 22, ["words as letter codes; numbers", "as number words, all capitals"])
    down("spell", "rules")
    label(B("spell")[0] + 8, B("spell")[1] + 22, ["words for the rules; finished words", "(names, exceptions) as phonemes"])
    down("rules", "post")
    label(B("rules")[0] + 8, B("rules")[1] + 22, ["phonemes as 10 x code, the rules'", "words and the finished ones in order"])
    lane = COLX[0] - 16
    x, y = T("decks", 0.06)
    arrow([(x, y), (x, y - 20), (lane, y - 20), (lane, L("words", 0.75)[1]), (L("words")[0] - 2, L("words", 0.75)[1])])
    for k in ("spell", "rules"):
        arrow([(lane, L(k, 0.75)[1]), (L(k)[0] - 2, L(k, 0.75)[1])])
    label(T("decks", 0.1)[0] + 6, T("decks")[1] - 26, "fetched by record number, or read through again and again")

    # --- the front end ----------------------------------------------------------------------------------------
    g0 = gap(0, 0.75)
    y0, y1 = Rt("post", 0.5)[1], L("feat", 0.5)[1]
    arrow([Rt("post", 0.5), (g0, y0), (g0, y1), (L("feat")[0] - 2, y1)])
    label(g0 - 8, y0 - 80, ["phoneme cards:", "10 x code + stress;", "-1 between words,", "-2 to -5 pauses,", "-9 the end"], "end")
    down("feat", "rev")
    label(B("feat")[0] + 8, B("feat")[1] + 22, "an 11-card record a segment")
    down("rev", "ahead")
    down("ahead", "fwd")
    label(B("ahead")[0] + 8, B("ahead")[1] + 22, "what lies ahead of each segment: three decks, A, B and C")
    g1 = gap(1, 0.3)
    yf = Rt("fwd", 0.5)[1]
    arrow([Rt("fwd", 0.5), (g1, yf), (g1, L("dur", 0.5)[1]), (L("dur")[0] - 2, L("dur", 0.5)[1])])
    arrow([(g1, L("frames", 0.5)[1]), (L("frames")[0] - 2, L("frames", 0.5)[1])])
    label(Rt("fwd")[0] + 8, yf + 22, ["the records and A, B, C, a few columns to", "each machine of every stage that follows"])
    # the phoneme table: into feat and next, and along the bottom to the filters and the level
    xt = Rt("table")[0] - 30
    yt = R("table")[1]
    lt = COLX[1] - 18
    arrow([(T("table", 0.04)[0], yt), (T("table", 0.04)[0], yt - 24), (lt, yt - 24), (lt, L("feat", 0.8)[1]),
           (L("feat")[0] - 2, L("feat", 0.8)[1])])
    arrow([(lt, L("ahead", 0.8)[1]), (L("ahead")[0] - 2, L("ahead", 0.8)[1])])
    low = B("table")[1] + 30
    g2 = gap(2, 0.25)
    arrow([B("table", 0.94), (B("table", 0.94)[0], low), (g2, low), (g2, L("filters", 0.85)[1]),
           (L("filters")[0] - 2, L("filters", 0.85)[1])])
    arrow([(g2, L("level", 0.7)[1]), (L("level")[0] - 2, L("level", 0.7)[1])])
    label(B("table", 0.06)[0], low + 20, "rows and filters fetched by number: K10..K1 and a gain each")
    # frames into the pitch, the filters, the level
    g2b = gap(2, 0.6)
    yfr = Rt("frames", 0.35)[1]
    arrow([Rt("frames", 0.35), (g2b, yfr), (g2b, L("pitch", 0.5)[1]), (L("pitch")[0] - 2, L("pitch", 0.5)[1])])
    arrow([(g2b, yfr), (g2b, L("level", 0.3)[1])], head=False)
    arrow([(g2b, L("filters", 0.4)[1]), (L("filters")[0] - 2, L("filters", 0.4)[1])])
    arrow([(g2b, L("level", 0.3)[1]), (L("level")[0] - 2, L("level", 0.3)[1])])
    label(Rt("frames")[0] + 6, yfr + 22, ["each frame's", "place, u;", "sentence", "summaries"])
    down("dur", "frames")
    label(B("dur")[0] + 8, B("dur")[1] + 22, ["frames a segment", "(25 ms each)"])
    # pitch, filters, level, frame cards
    g3 = gap(3, 0.2)
    yp = Rt("pitch", 0.5)[1]
    arrow([Rt("pitch", 0.5), (g3, yp), (g3, Rt("asm", 0.5)[1]), (Rt("asm")[0] + 2, Rt("asm", 0.5)[1])])
    arrow([(g3, Rt("level", 0.5)[1]), (Rt("level")[0] + 2, Rt("level", 0.5)[1])])
    label(g3 + 6, yp + 22, ["the pitch", "period P"])
    down("filters", "level", 0.3)
    label(B("filters", 0.3)[0] + 8, B("filters")[1] + 22, ["the gain G,", "V, sounding"])
    xk = B("filters", 0.75)[0]
    arrow([(xk, B("filters")[1]), (xk, R("asm")[1] - 2)])
    label(xk + 8, B("filters")[1] + 22, "K10..K1")
    down("level", "asm", 0.3)
    label(B("level", 0.3)[0] + 8, B("level")[1] + 22, ["the excitation", "amplitude A"])

    # --- the voice box ----------------------------------------------------------------------------------------
    g4 = gap(3, 0.8)
    ya = Rt("asm", 0.75)[1]
    arrow([(Rt("asm")[0], ya), (g4, ya), (g4, L("interp", 0.5)[1]), (L("interp")[0] - 2, L("interp", 0.5)[1])])
    label(g4 - 8, ya - 100, ["frame cards: V, P, A,", "K10..K1; 13 a frame,", "40 frames a second"], "end")
    xr, xe = B("reduce")[0], B("excite")[0]
    yi = B("interp")[1]
    arrow([(xr, yi), (xr, R("reduce")[1] - 2)])
    arrow([(xe, yi), (xe, R("excite")[1] - 2)])
    label(xr + 8, yi + 22, "K10..K1 a step")
    label(xe + 8, yi + 22, "V, P, A a step")
    yr = B("reduce")[1]
    arrow([(xr, yr), (xr, R("lattice")[1] - 2)])
    arrow([(xe, yr), (xe, R("lattice")[1] - 2)])
    label(xr + 8, yr + 22, "5 cards a K, ten to each")
    label(xe + 8, yr + 22, ["the excitation,", "a sample"])
    down("lattice", "output")
    label(B("lattice")[0] + 8, B("lattice")[1] + 20, "f, a sample")
    down("output", "samples")
    label(B("output")[0] + 8, B("output")[1] + 20, "two values a sample: thousands, units")

    draw_wires(svg)
    gs = {g[0]: g for g in GROUPS}
    for k in gs:
        draw_group(svg, gs[k], rect[k])
    for k in HOSTS:
        draw_host(svg, k, rect[k])
    for x, y, lines, anchor in LABELS:
        for i, l in enumerate(lines):
            svg.text(x, y + 14 * i, l, "data", anchor)
    svg.add("</svg>")
    return "\n".join(svg.parts) + "\n", W, H


def main():
    svg, w, h = build()
    out = ROOT / "docs" / "pipeline.svg"
    out.write_text(svg)
    print(out, f"{w}x{h}")
    if "--png" in sys.argv:
        png = sys.argv[sys.argv.index("--png") + 1]
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
            page.set_content(f'<!doctype html><html><body style="margin:0;background:{BG}">'
                             f'<style>svg{{display:block}}</style>{svg}</body></html>')
            page.screenshot(path=png, clip={"x": 0, "y": 0, "width": w, "height": h})
            b.close()
        print(png)


if __name__ == "__main__":
    main()
