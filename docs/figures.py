#!/usr/bin/env python3
"""The figures for the cardiac-speech paper (runcardiac's cardiac_speech.html), regenerated from the repository.

Every figure that shows data takes it from what the CARDIAC programs produced or from the tables they read:

  - talk (the hand-written version, under heartburn) on the README sentence, with CARDIAC_SPEECH_TAP set, which writes
    what each text and front-end machine punched (src/net.rs);
  - the voice box's interp, steps, ksteps and excite listings run on ref/cardiac.py, the Python CARDIAC, wired as
    ref/nets.py wires them (the voice box runs by rounds and isn't tapped; the instruction counts and excite's
    values are checked here against heartburn's counts and voice_ref);
  - upsample/target/release/talk (48 kHz) on the README sentence and the paper's three sample texts, with -v for
    the instruction counts and --8k for the 8 kHz samples underneath;
  - the decks front/features.cards, front/filters.cards, text/rules.cards and upsample/tables/fir1.cards and
    fir2.cards, and the listing voice/lattice.cq.

It needs matplotlib and numpy (neither Python on this Mac has them, so a venv in work/ does: python3 -m venv work/venv
&& work/venv/bin/pip install matplotlib numpy), carc (heartburn's assembler) on the PATH or in
../heartburn/target/release, and for the memory map runcardiac's memmap.py and tipmaps.py (../runcardiac). It builds
both versions with cargo first. Intermediates go in work/figures/ (gitignored); the captions go in
docs/figures/captions.md.

    work/venv/bin/python docs/figures.py                    # every figure, into docs/figures/
    work/venv/bin/python docs/figures.py --sheet OUT.pdf    # and a contact sheet, a page a figure with its caption
                                                            # (OUT.png tiles them); Chrome's headless shell renders
"""
import glob
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                     # noqa: E402
from matplotlib.colors import LinearSegmentedColormap               # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch, Polygon   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs' / 'figures'
WORK = ROOT / 'work' / 'figures'
REF = ROOT / 'ref'
RUNCARDIAC = ROOT.parent / 'runcardiac'
sys.path.insert(0, str(REF))

SENTENCE = "Hello, my name is cardiac and I was born in 1968 to D W Hagelbarger. And now I can talk."
# the paper's three sample texts measured in its Section 7.2, as runcardiac/build_site.py speaks them
SAMPLES = [('All your base', "All your base are belong to us. You have no chance to survive. Make your time."),
           ('Keep talking', "It doesn't have to be like this. All we need to do is make sure. we keep. talking."),
           ('For millions of years', "for millions of years, mankind lived just like the animals. Then something "
            "happened, which unleashed the power of our imagination. and we learned. to talk.")]

# the site's look
INK, ACCENT, RED, MUTED, RULE, PANEL = '#101410', '#087a2c', '#d8322a', '#586058', '#cfd5cc', '#eef1ec'
LIGHT = '#9fd9ab'          # the memory maps' code green, for fills
PALE = '#e3efe4'
GREY = '#8a948a'
FONT = 'Arial'
FONT_STACK = "Arial, 'Helvetica Neue', Helvetica, sans-serif"
W_IN = 5.4                 # figure width in inches: about 7 px a point on a 390 px phone, readable at 13 pt

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': [FONT, 'Helvetica', 'DejaVu Sans'], 'font.size': 12.5,
    'axes.edgecolor': INK, 'axes.labelcolor': INK, 'axes.linewidth': 0.9, 'axes.labelsize': 12.5,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.facecolor': 'white',
    'xtick.color': INK, 'ytick.color': INK, 'xtick.labelsize': 11.5, 'ytick.labelsize': 11.5,
    'xtick.major.width': 0.8, 'ytick.major.width': 0.8, 'legend.fontsize': 11, 'legend.frameon': False,
    'figure.facecolor': 'white', 'savefig.facecolor': 'white', 'svg.fonttype': 'none', 'svg.hashsalt': 'cardiac',
    'lines.linewidth': 1.6, 'mathtext.default': 'regular', 'path.simplify': True,
})
SPEC = LinearSegmentedColormap.from_list('sq', ['#ffffff', '#cfe9d4', LIGHT, ACCENT, '#0b3d1a', INK])

RATE = 8000
FRAME = 13                 # cards a frame: V, P, A, K10..K1
STEP_LEN, STEPS = 20, 10   # ten steps of 20 samples a frame


# --- running the programs ---------------------------------------------------------------------------------------
def carc_on_path():
    if shutil.which('carc'):
        return
    for d in (ROOT.parent / 'heartburn' / 'target' / 'release',):
        if (d / 'carc').exists():
            os.environ['PATH'] = str(d) + os.pathsep + os.environ['PATH']
            return
    raise SystemExit('carc (heartburn\'s assembler) is needed on the PATH')


def build():
    for d in (ROOT, ROOT / 'upsample'):
        subprocess.run(['cargo', 'build', '--release', '-q'], cwd=d, check=True)


def talk(args, text, out, env=None, err=None):
    e = dict(os.environ, **(env or {}))
    with open(out, 'wb') as f:
        r = subprocess.run([str(args[0])] + args[1:] + [text], stdout=f, stderr=subprocess.PIPE, env=e, check=True)
    if err:
        Path(err).write_bytes(r.stderr)


def s16(path):
    return np.fromfile(path, dtype='<i2').astype(float)


def cards(path):
    return [int(x) for x in Path(path).read_text().split()]


def run_all():
    """Run the programs once; everything the figures read goes into work/figures/."""
    WORK.mkdir(parents=True, exist_ok=True)
    build()
    t8, t48 = ROOT / 'target' / 'release' / 'talk', ROOT / 'upsample' / 'target' / 'release' / 'talk'
    tap = WORK / 'tap8'
    shutil.rmtree(tap, ignore_errors=True)
    talk([t8, '-v'], SENTENCE, WORK / 'hello8k.s16', {'CARDIAC_SPEECH_TAP': str(tap)}, WORK / 'hello8k.v.txt')
    talk([t48, '-v'], SENTENCE, WORK / 'hello48k.s16', err=WORK / 'hello48k.v.txt')
    talk([t8, '--frames'], SENTENCE, WORK / 'hello.frames')
    talk([t8, '--phonemes'], SENTENCE, WORK / 'hello.phonemes')
    for i, (_, text) in enumerate(SAMPLES):
        talk([t48], text, WORK / ('sample%d.48k.s16' % i))
        talk([t48, '--8k'], text, WORK / ('sample%d.8k.s16' % i))
    assert cards(tap / 'asm') == cards(WORK / 'hello.frames')


def run_voice_front_half():
    """interp, steps, ksteps and excite on the Python CARDIAC, wired as ref/nets.py's voice_box wires them, on the
    frame cards talk made: what each punched, and their instruction counts."""
    import cardiac
    import nets
    import voice_ref as vr
    carc_on_path()
    V = str(ROOT / 'voice') + '/'
    deck = cards(WORK / 'hello.frames')
    net = cardiac.Net()
    net.merge('pairs', [('frames', 1), ('frames2', 1)])
    net.add('interp', V + 'interp.cq', 'pairs', 'int')
    net.fan['int'] = ['int_p', 'int_k']
    net.collate('tosteps', [('int_p', 25, list(range(5)))])
    net.collate('toksteps', [('int_k', 25, list(range(3, 25)))])
    net.add('steps', V + 'steps.cq', 'tosteps', 'exc')
    net.add('ksteps', V + 'ksteps.cq', 'toksteps', 'kin')
    net.add('excite', V + 'excite.cq', 'exc', 'e')
    nets.deal_frames(net, deck)
    net.run()
    got = {n: net.punched[n] for n in ('steps', 'ksteps', 'excite')}
    counts = {n: m.steps for n, m in net.machines.items()}
    hb = instruction_counts(WORK / 'hello8k.v.txt')
    for n, c in counts.items():
        assert hb[n] == c, (n, hb[n], c)          # the same programs, the same counts as under heartburn
    fr = vr.parse_cards(deck)
    assert vr.excitation(vr.cl.interp_steps(fr, 0, len(fr))) == got['excite']
    return got


def instruction_counts(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        m = re.match(r'^\s*(\S+)\s+(\d+)$', line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def stages(path):
    """The machines of each stage, in the order talk -v lists them, and their instruction counts."""
    counts = instruction_counts(path)
    names = list(counts)
    up = [n for n in names if re.match(r'(digits|words)\d$', n) or n in ('yd', 'fir1', 'fir2')]
    rest = [n for n in names if n not in up]
    cut = [rest.index('join') + 1, rest.index('asm') + 1]
    parts = [rest[:cut[0]], rest[cut[0]:cut[1]], rest[cut[1]:], up]
    assert parts[2][-1] == 'output'
    return [[(n, counts[n]) for n in p] for p in parts]


# --- tables ------------------------------------------------------------------------------------------------------
def table():
    import table as tb
    feats = cards(ROOT / 'front' / 'features.cards')
    filt = cards(ROOT / 'front' / 'filters.cards')
    rec = lambda pc: feats[pc * tb.FEAT:(pc + 1) * tb.FEAT]
    flt = lambda n: filt[n * 11:(n + 1) * 11]                     # K10..K1, G
    return tb, rec, flt


def lattice_response(K, G, voiced, n=4096):
    """The voice box's path for one pulse through a filter, in floating point: the excitation's low-pass (voiced),
    the lattice with k = K / 1000 (cards K10..K1) and the de-emphasis, times the gain G (as ref/table.py's
    k_energy, which the gains and the glide table are made from). Returns frequencies (Hz) and level (dB)."""
    ks = [k / 1000 for k in reversed(K)]
    b = [0.0] * 11
    yd = 0.0
    h = np.zeros(n)
    for i in range(n):
        f = 0.5 ** i if voiced else (1.0 if i == 0 else 0.0)
        for j in range(10, 0, -1):
            f = f - ks[j - 1] * b[j - 1]
            b[j] = b[j - 1] + ks[j - 1] * f
        b[0] = f
        yd = f + 0.9 * yd
        h[i] = yd
    H = np.fft.rfft(h * G)
    return np.fft.rfftfreq(n, 1 / RATE), 20 * np.log10(np.abs(H) + 1e-9), float(np.sum((h * G) ** 2))


# --- output ------------------------------------------------------------------------------------------------------
CAPTIONS = []


def save(fig, name, caption):
    n = len(CAPTIONS) + 1
    stem = 'fig%02d-%s' % (n, name)
    path = OUT / (stem + '.svg')
    fig.savefig(path, format='svg', metadata={'Date': None, 'Creator': None})
    plt.close(fig)
    svg = path.read_text()
    svg = re.sub(r"font-family:\s*'?%s'?" % FONT, 'font-family:%s' % FONT_STACK, svg)
    svg = re.sub(r"font: ([\d.]+)px '%s'" % FONT, r'font-size:\1px; font-family:%s' % FONT_STACK, svg)
    path.write_text(svg)
    CAPTIONS.append((n, stem + '.svg', caption))
    return stem


def write_svg(name, svg, caption):
    n = len(CAPTIONS) + 1
    stem = 'fig%02d-%s' % (n, name)
    (OUT / (stem + '.svg')).write_text(svg)
    CAPTIONS.append((n, stem + '.svg', caption))


def label(ax, s, x=-0.02, y=1.02):
    ax.text(x, y, s, transform=ax.transAxes, ha='right', va='bottom', fontsize=13, fontweight='bold', color=INK)


def box(ax, x, y, w, h, text='', fc='white', ec=INK, lw=1.1, fs=12, color=INK, weight='normal', r=0.04, z=2,
        ha='center', ls='-'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=%g' % r, fc=fc, ec=ec, lw=lw,
                                zorder=z, ls=ls))
    if text:
        tx = x + w / 2 if ha == 'center' else x + 0.12
        ax.text(tx, y + h / 2, text, ha=ha, va='center', fontsize=fs, color=color, fontweight=weight, zorder=z + 1,
                linespacing=1.3)


def arrow(ax, x0, y0, x1, y1, color=INK, lw=1.3, style='-|>', ms=12, z=1, ls='-', shrink=0):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=ms, color=color, lw=lw,
                                 zorder=z, linestyle=ls, shrinkA=shrink, shrinkB=shrink))


def blank(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis('off')
    return fig, ax


def cardpile(ax, x, y, w, h, text, n=3, fc='white', fs=12, ec=INK):
    """A pile of cards: n outlines offset behind the front one."""
    for i in range(n - 1, 0, -1):
        ax.add_patch(Rectangle((x + 0.05 * i, y + 0.05 * i), w, h, fc=fc, ec=ec, lw=0.8, zorder=1))
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.1, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs, color=INK, zorder=3, linespacing=1.3)


# --- the README sentence, segment by segment ----------------------------------------------------------------------
WORDS = ['Hello', 'my', 'name', 'is', 'cardiac', 'and', 'I', 'was', 'born', 'in', 'nineteen', 'sixty', 'eight',
         'to', 'D', 'W', 'Hagelbarger', 'And', 'now', 'I', 'can', 'talk']


def segments():
    """The README sentence's segments as the front end made them: [{pc, name, s, word, inh, dur, frames}], pauses
    included (pc 0), from what feat, mul and nframes punched, with the inherent durations of the phoneme table."""
    tb, rec, _ = table()
    tap = WORK / 'tap8'
    feat, mul, nfr = cards(tap / 'feat'), cards(tap / 'mul'), cards(tap / 'nframes')
    out, w, f0 = [], -1, 0
    for i in range(len(mul)):
        pc, s, wf = feat[5 * i:5 * i + 3]
        if pc and wf:
            w += 1
        out.append({'pc': pc, 'name': tb.NAME.get(pc, 'pause'), 's': s, 'word': w if pc else None,
                    'inh': rec(pc)[tb.F_INH] if pc else None, 'dur': mul[i], 'f0': f0, 'n': nfr[i]})
        f0 += nfr[i]
    assert w + 1 == len(WORDS), w
    assert f0 == len(cards(WORK / 'hello.frames')) // FRAME
    return out


def frames():
    d = cards(WORK / 'hello.frames')
    out = []
    for i in range(0, len(d) - 1, FRAME):
        if d[i] < 0:
            break
        out.append((d[i], d[i + 1], d[i + 2], d[i + 3:i + 13]))      # V, P, A, K10..K1
    return out


# --- Section 3.1: designing in tens ------------------------------------------------------------------------------
def fig_tens(vb):
    fr = frames()
    ks = vb['ksteps']                                  # per step: A, K10, A, K9, ... A, K1 (20 cards)
    k1 = [ks[20 * s + 19] for s in range(len(ks) // 20)]
    best = None
    vw = vowels()
    for s in segments():
        if s['name'] not in vw:
            continue
        for f in range(s['f0'], s['f0'] + s['n'] - 2):          # frames f, f + 1 and f + 2 all in the vowel
            (v0, _, _, K0), (v1, _, _, K1), (v2, _, _, _) = fr[f], fr[f + 1], fr[f + 2]
            if v0 == v1 == v2 == 1:
                d = abs(K1[9] - K0[9])
                if d % 10 and (best is None or d > best[0]):
                    best = (d, f, s)
    _, f, seg = best
    a, b, c = fr[f][3][9], fr[f + 1][3][9], fr[f + 2][3][9]
    st = k1[10 * f:10 * f + 20]
    assert st[0] == a and st[10] == b
    fig, ax = plt.subplots(figsize=(W_IN, 3.9))
    fig.subplots_adjust(left=0.16, right=0.97, top=0.83, bottom=0.17)
    xs = np.arange(0, 401)
    ys = [st[min(n // STEP_LEN, 19)] for n in xs]
    ax.plot([0, 200, 400], [a, b, c], color=GREY, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.step(xs, ys, where='post', color=ACCENT, lw=2, zorder=2)
    ax.plot([0, 200, 400], [a, b, c], 'o', ms=7, mfc='white', mec=INK, mew=1.5, zorder=3)
    for x in (200,):
        ax.axvline(x, color=RULE, lw=1, zorder=0)
    step = (b - a) / 10
    trunc = int(step)
    up = lambda u, v: 12 if v <= u else -36
    ax.annotate('frame %d\nK1 = %d' % (f, a), (0, a), xytext=(8, up(a, b)), textcoords='offset points',
                fontsize=11.5, ha='left')
    ax.annotate('frame %d\nK1 = %d' % (f + 1, b), (200, b), xytext=(8, up(b, c)), textcoords='offset points',
                fontsize=11.5, ha='left')
    s9 = st[9]
    ax.annotate('step 10: %d' % s9, (190, s9), xytext=(-14, -34 if b < a else 26),
                textcoords='offset points', fontsize=11.5, ha='right',
                arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.8))
    ax.set_xlim(0, 400)
    ax.set_xticks(range(0, 401, 40))
    ax.set_xticks(range(0, 401, 20), minor=True)
    ax.set_xlabel('Sample from the start of frame %d (8 kHz)' % f)
    ax.set_ylabel('K1 (thousandths)')
    lo, hi = min(st + [c]), max(st + [c])
    ax.set_ylim(lo - 0.42 * (hi - lo), hi + 0.3 * (hi - lo))
    top = ax.secondary_xaxis('top', functions=(lambda x: x / 8, lambda x: x * 8))
    top.set_xticks([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50])
    top.set_xlabel('Time (ms)')
    cap = ('One reflection coefficient, K1, across two 25 ms frames of the README sentence, frames %d and %d, in the '
           '%s of "%s" (the pair of frames within a vowel with the largest change of K1 that is not a multiple of '
           'ten). Circles are the values on the frame cards the front end punched, and the green staircase is the '
           'value the voice box uses for each sample, as the ksteps program punched it. Each frame is ten steps of '
           '20 samples. The first step holds the frame’s own value and each later step adds (next - this) / 10, '
           'formed by one SFT 01, which truncates toward zero. From %d to %d the step is %d where the exact step is '
           '%.1f. The tenth step holds %d, and the next frame starts from its own card, %d. The dashed line is exact '
           'linear interpolation between the cards, for comparison. Data from talk --frames (heartburn) and from '
           'interp and ksteps run on ref/cardiac.py.'
           % (f, f + 1, seg['name'], WORDS[seg['word']], a, b, trunc, step, s9, b))
    save(fig, 'tens', cap)


# --- Section 4.1: letter codes ------------------------------------------------------------------------------------
CLASSES = [('#', 'vowel', [(1, 6)]), ('+', 'front vowel', [(4, 6)]), ('^', 'consonant', [(7, 26)]),
           ('.', 'voiced consonant', [(16, 26)]), ('&', 'sibilant', [(13, 18)]),
           ('@', 'T S J Z D L N R', [(12, 13), (17, 22)]), ("' '", 'blank', [(27, 28)])]


def fig_codes():
    import text_tables as tt
    assert (tt.V, tt.FRONT, tt.C, tt.VOICED, tt.SIB, tt.AT1, tt.AT2, tt.BLANK) == \
        ((1, 6), (4, 6), (7, 26), (16, 26), (13, 18), (12, 13), (17, 22), (27, 28))
    letter = {v: k for k, v in tt.CODE.items()}
    letter[28] = 'edge'
    rh, top, x0 = 0.215, 2.0, 0.25
    h = top + 28 * rh + 0.2
    fig, ax = blank(W_IN, h)
    y = lambda c: h - top - c * rh                       # bottom of code c's row
    ax.text(x0 + 0.25, h - top + 0.08, 'code', ha='center', va='bottom', fontsize=11.5, color=MUTED)
    ax.text(x0 + 0.78, h - top + 0.08, 'letter', ha='center', va='bottom', fontsize=11.5, color=MUTED)
    for c in range(1, 29):
        if c % 2 == 0:
            ax.add_patch(Rectangle((x0, y(c)), W_IN - 2 * x0 + 0.05, rh, fc=PANEL, ec='none', zorder=0))
        ax.text(x0 + 0.25, y(c) + rh / 2, str(c), ha='center', va='center', fontsize=11.5)
        ax.text(x0 + 0.78, y(c) + rh / 2, letter[c], ha='center', va='center',
                fontsize=11.5 if c < 28 else 10.5, fontweight='bold' if c < 27 else 'normal')
    cw, cx = 0.55, x0 + 1.08
    for j, (sym, name, ranges) in enumerate(CLASSES):
        x = cx + j * cw
        ax.text(x + cw / 2, h - top + 0.08, name, rotation=90, ha='center', va='bottom', fontsize=11.5)
        ax.text(x + cw / 2, h - 0.06, sym, ha='center', va='top', fontsize=15, fontweight='bold', color=ACCENT,
                family='monospace')
        for lo, hi in ranges:
            ax.add_patch(FancyBboxPatch((x + 0.08, y(hi) + 0.02), cw - 0.16, (hi - lo + 1) * rh - 0.04,
                                        boxstyle='round,pad=0,rounding_size=0.05', fc=LIGHT, ec=ACCENT, lw=1, zorder=2))
            short = hi - lo < 3
            ax.text(x + cw / 2, y(hi) + (hi - lo + 1) * rh / 2, ('%d\n%d' if hi == lo + 1 else '%d\u2013%d') % (lo, hi),
                    ha='center', va='center', rotation=0 if short else 90, fontsize=10 if short else 10.5, zorder=3,
                    color=INK, linespacing=1.0)
    cap = ('The letter codes of the text programs and the classes of the NRL rules. Letters are numbered 1 to 26 in '
           'the order A O U E I Y F H K P Q T S C X G J Z D L N R B M V W, so that each class a rule names is a range '
           'of codes; 27 is the apostrophe and 28 the edge of a word. The symbol above each column is the one the '
           'rules use (Elovitz et al. 1976), and the label under it its meaning; the blank matches the edge '
           'of a word or an apostrophe. The rules\u2019 & and @ also match the pairs CH and SH (and @ also TH), '
           'which are written as separate rules. A rule’s ":" and "#" are counts on the same ranges (none or '
           'more consonants, one or more vowels). Testing a letter against a class is two subtractions and two '
           'conditional jumps. Ranges from ref/text_tables.py, which writes the rule decks.')
    save(fig, 'codes', cap)


def fig_match():
    import text_tables as tt
    tap = WORK / 'tap8'
    letters, left, right, first = (cards(tap / n) for n in ('letters', 'left', 'right', 'first'))
    nrec = len(letters) // 19
    most = len(left) // nrec
    assert most * nrec == len(left) == len(right) and len(first) == nrec
    want = [tt.CODE[c] for c in 'NAME']
    idx = next(i for i in range(nrec) if letters[19 * i] == 1 and letters[19 * i + 1] == 1
               and letters[19 * i + 4:19 * i + 10] == [28] + want + [28])
    rule = first[idx]
    secs = tt.sections(cards(ROOT / 'text' / 'rules.cards'))
    nA = len(secs[1])
    n, lctx, rctx, phs = secs[1][rule]
    lv, rv = left[most * idx:most * idx + nA], right[most * idx:most * idx + nA]
    both = [i for i in range(nA) if lv[i] and rv[i]]
    assert both[0] == rule
    nrl = [r for l, m, rr, p in tt.tp.RULES['A'] for la in tt.tokens(l, True) for ra in tt.tokens(rr, False)
           for r in [(l, m, rr, p)]]
    L, M, R, P = nrl[rule]
    fig = plt.figure(figsize=(W_IN, 6.9))
    ax = fig.add_axes([0, 0.30, 1, 0.70])
    ax.set_xlim(0, W_IN)
    ax.set_ylim(0, 6.9 * 0.70)
    ax.axis('off')
    H = 6.9 * 0.70
    ax.text(0.25, H - 0.3, 'Rule %d of A' % rule, fontsize=12.5, fontweight='bold', va='center')
    ax.text(1.75, H - 0.3, '%s[%s]%s = /%s/' % (L.replace(' ', '␣'), M, R.replace(' ', '␣'), ' '.join(P)),
            fontsize=14, family='monospace', va='center')
    word = ['edge', 'N', 'A', 'M', 'E', 'edge']
    codes = [28] + want + [28]
    cw, x0, yw = 0.72, 0.55, H - 1.35
    for i, (ch, c) in enumerate(zip(word, codes)):
        fc = LIGHT if ch == 'A' else 'white'
        box(ax, x0 + i * cw, yw, cw - 0.06, 0.5, ch if ch != 'edge' else '', fc=fc, fs=15, weight='bold', r=0.03)
        if ch == 'edge':
            ax.text(x0 + i * cw + (cw - 0.06) / 2, yw + 0.25, 'edge', ha='center', va='center', fontsize=10.5,
                    color=MUTED)
        ax.text(x0 + i * cw + (cw - 0.06) / 2, yw - 0.2, str(c), ha='center', va='center', fontsize=12)
    ax.text(x0 - 0.12, yw + 0.25, 'letter', ha='right', va='center', fontsize=11, color=MUTED)
    ax.text(x0 - 0.12, yw - 0.2, 'code', ha='right', va='center', fontsize=11, color=MUTED)
    # the elements, each against the letters it takes
    rows = []
    sym = {(10, 7, 26): ':', (1, 27, 28): '␣', (1, 7, 26): '^', (1, 4, 6): '+', (1, 1, 1): 'A'}
    pos = 1                                          # left context read leftwards from the letter before A (N)
    for e in lctx:
        q, lo, hi = e
        took = []
        while True:
            c = codes[pos]
            if lo <= c <= hi and (q != 1 or not took):
                took.append(pos)
                pos -= 1
                if q == 1:
                    break
            else:
                break
        rows.append(('left', sym[tuple(e)], q, lo, hi, took))
    pos = 2
    for e in rctx:
        q, lo, hi = e
        took = [pos] if lo <= codes[pos] <= hi else []
        pos += 1
        rows.append(('right', sym[tuple(e)], q, lo, hi, took))
    yr = yw - 0.75
    ax.text(0.25, yr, 'context', fontsize=11, color=MUTED, va='center')
    ax.text(1.25, yr, 'element', fontsize=11, color=MUTED, va='center', ha='center')
    ax.text(2.35, yr, 'how many, codes', fontsize=11, color=MUTED, va='center', ha='center')
    ax.text(4.25, yr, 'test', fontsize=11, color=MUTED, va='center', ha='center')
    qn = {1: 'one', 10: 'none or more', 11: 'one or more', 12: 'two or more'}
    for k, (side, s, q, lo, hi, took) in enumerate(rows):
        y = yr - 0.42 * (k + 1)
        ax.text(0.25, y, side if k in (0, len(lctx)) else '', fontsize=12, va='center')
        ax.text(1.25, y, s, fontsize=15, family='monospace', va='center', ha='center', color=ACCENT,
                fontweight='bold')
        ax.text(2.35, y, '%s, %d–%d' % (qn[q], lo, hi) if hi > lo else '%s, %d' % (qn[q], lo), fontsize=12,
                va='center', ha='center')
        t = ', '.join('%d ≤ %d ≤ %d' % (lo, codes[p], hi) for p in took)
        ax.text(4.25, y, t if took else '(none)', fontsize=12, va='center', ha='center')
        if side == 'right' and k == len(lctx):
            ax.plot([0.2, W_IN - 0.2], [y + 0.21, y + 0.21], color=RULE, lw=0.8)
    # the verdicts of every A rule at this letter
    ax2 = fig.add_axes([0.13, 0.07, 0.84, 0.16])
    grid = np.array([lv, rv], dtype=float)
    for r in range(2):
        for i in range(nA):
            on = grid[r, i] > 0
            ax2.add_patch(Rectangle((i + 0.08, 1 - r + 0.1), 0.84, 0.8, fc=ACCENT if on else 'white',
                                    ec=ACCENT if on else RULE, lw=0.8))
    ax2.add_patch(Rectangle((rule, 0), 1, 2, fc='none', ec=RED, lw=2))
    ax2.set_xlim(0, nA)
    ax2.set_ylim(0, 2)
    ax2.set_yticks([1.5, 0.5])
    ax2.set_yticklabels(['left', 'right'])
    ax2.set_xticks([i + 0.5 for i in range(0, nA, 5)])
    ax2.set_xticklabels([str(i) for i in range(0, nA, 5)])
    ax2.tick_params(length=0)
    for s in ax2.spines.values():
        s.set_visible(False)
    ax2.set_xlabel('Rule of A (in the deck’s order)')
    fig.text(0.13, 0.255, 'Verdicts for the A of NAME, as left and right punched them', fontsize=11.5, color=MUTED)
    cap = ('A worked match of one NRL rule on the A of NAME in the README sentence. Above, the word as the text '
           'programs hold it, with an edge (28) on each side, and the rule that matched, %s[%s]%s = /%s/, its '
           'elements tested in turn. The left context is read leftwards from the letter before the bracket, and the '
           'right context rightwards from the bracket’s first letter. Each element is a count and a range of '
           'codes, and each test is the two comparisons shown. Below, the verdicts the left and right programs '
           'punched for each of the %d rules of A at this letter (filled: the context matches); first chose rule %d, '
           'the first with both, outlined in red, and pick punched its phoneme EY. Data from the taps of talk on the '
           'README sentence (heartburn) and text/rules.cards.'
           % (L.replace(' ', '␣'), M, R.replace(' ', '␣'), ' '.join(P), nA, rule))
    save(fig, 'match', cap)


# --- Section 4.2: durations ---------------------------------------------------------------------------------------
def fig_durations():
    seg = [s for s in segments() if s['pc']]
    half = next(i for i, s in enumerate(seg) if i >= len(seg) // 2 and seg[i - 1]['word'] != s['word'])
    cols = [seg[:half], seg[half:]]
    nrow = max(len(c) for c in cols)
    fig, axs = plt.subplots(1, 2, figsize=(W_IN, 0.155 * nrow + 1.3), sharex=True)
    fig.subplots_adjust(left=0.215, right=0.955, top=1 - 0.55 / (0.155 * nrow + 1.3), bottom=0.75 / (0.155 * nrow + 1.3),
                        wspace=0.75)
    xmax = max(max(s['dur'], s['inh']) for s in seg)
    for ax, col in zip(axs, cols):
        for r, s in enumerate(col):
            ax.plot([s['inh'], s['dur']], [r, r], color=GREY if s['dur'] <= s['inh'] else ACCENT, lw=1.4, zorder=1)
            ax.plot(s['inh'], r, 'o', ms=5.5, mfc='white', mec=INK, mew=1.1, zorder=2)
            ax.plot(s['dur'], r, 'o', ms=5.5, mfc=ACCENT, mec=ACCENT, zorder=3)
        ax.set_yticks(range(len(col)))
        ax.set_yticklabels([s['name'] + ('ˈ' if s['s'] == 1 else 'ˌ' if s['s'] == 2 else '') for s in col],
                           fontsize=10, family='monospace')
        ax.set_ylim(nrow - 0.4, -0.6)
        ax.tick_params(axis='y', length=0, pad=2)
        ax.set_xlim(0, 300)
        ax.set_xticks([0, 100, 200, 300])
        ax.grid(axis='x', color=RULE, lw=0.6)
        ax.set_axisbelow(True)
        ax.spines['left'].set_visible(False)
        for r, s in enumerate(col):
            if r == 0 or col[r - 1]['word'] != s['word']:
                ax.annotate(WORDS[s['word']], (0, r), xycoords=('axes fraction', 'data'), xytext=(-34, 0),
                            textcoords='offset points', ha='right', va='center', fontsize=10, color=MUTED,
                            style='italic')
                if r:
                    ax.axhline(r - 0.5, color=RULE, lw=0.6)
    fig.supxlabel('Duration (ms)', fontsize=12.5, y=0.012)
    h = 0.155 * nrow + 1.3
    fig.legend(handles=[plt.Line2D([], [], marker='o', ls='', mfc='white', mec=INK, ms=6, label='inherent'),
                        plt.Line2D([], [], marker='o', ls='', mfc=ACCENT, mec=ACCENT, ms=6, label='computed')],
               loc='upper center', ncol=2, bbox_to_anchor=(0.55, 1 - 0.05 / h), fontsize=11.5, handletextpad=0.2)
    longer = sum(s['dur'] > s['inh'] for s in seg)
    assert seg[3]['name'] == 'OW'
    tap = WORK / 'tap8'
    i = next(k for k, s in enumerate(segments()) if s['name'] == 'OW')
    fs = [v for n in ('rules2', 'rules5', 'rules9') for v in cards(tap / n)[4 * i:4 * i + 4] if v not in (0, 100)]
    ow_factors = ', '.join(map(str, fs[:-1])) + ' and ' + str(fs[-1])
    cap = ('The inherent duration in the phoneme table of each of the %d sounds of the README sentence (open '
           'circles; Klatt 1979), against the duration the mul program computed for it, (D_inh - D_min) P / 100 + '
           'D_min, after the rules\u2019 factors (filled). Sounds are listed in order down the left column and then '
           'the right, under the words they belong to; \u02c8 marks primary and \u02cc secondary stress. Of the '
           'sounds, %d are lengthened (green line) and %d shortened (grey line). The longest, OW at the end of "Hello" before the '
           'comma, takes the factors %s, and lasts %d ms against its inherent %d ms. Pauses are omitted. Data from '
           'what the feat, rules2, rules5, rules9 and mul programs punched (talk on the README sentence under '
           'heartburn) and front/features.cards.'
           % (len(seg), longer, len(seg) - longer, ow_factors, seg[3]['dur'], seg[3]['inh']))
    save(fig, 'durations', cap)


# --- Section 4.3: formants and the filter -------------------------------------------------------------------------
def filter_names():
    tb, rec, _ = table()
    names = {}
    for p in tb.PHONEMES:
        r = rec(tb.CODE[p])
        for slot, what in ((tb.F_TS, 'start'), (tb.F_TE, 'end'), (tb.F_ASP, 'aspirated'), (tb.F_NOISE, 'noise'),
                           (tb.F_ALT, 'alternative noise'), (tb.F_VBAR, 'voice bar')):
            if r[slot] and r[slot] not in names:
                names[r[slot]] = (p, what)
    return names


def fig_filters():
    tb, rec, flt = table()
    import table as T
    T.build(T.C)                                                 # which filters speak voiced (T.VOICED)
    voiced = T.VOICED
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(W_IN, 7.4))
    fig.subplots_adjust(left=0.15, right=0.97, top=0.95, bottom=0.08, hspace=0.42)
    show = [('IY', tb.F_TS, ACCENT, '-'), ('AA', tb.F_TS, INK, '-'), ('UW', tb.F_TS, ACCENT, (0, (5, 2))),
            ('S', tb.F_NOISE, GREY, '-')]
    used = []
    for p, slot, col, ls in show:
        n = rec(tb.CODE[p])[slot]
        K, G = flt(n)[:10], flt(n)[10]
        f, db, _ = lattice_response(K, G, voiced[n])
        a1.plot(f, db, color=col, ls=ls, lw=1.8, label='%s (filter %d)' % (p, n))
        used.append((p, n, G))
    a1.set_xlim(0, 4000)
    a1.set_ylabel('Level (dB)')
    a1.set_xlabel('Frequency (Hz)')
    a1.legend(loc='upper right', ncol=2, fontsize=10.5, columnspacing=1, handlelength=1.8)
    lo, hi = a1.get_ylim()
    a1.set_ylim(hi - 70, hi + 8)
    a1.grid(color=RULE, lw=0.5)
    label(a1, 'a')
    # the glide with the largest level factor in the sentence
    tap = WORK / 'tap8'
    gl, gb, gn = cards(tap / 'glides'), cards(tap / 'glideb'), cards(tap / 'gnorm')
    nf = len(gn) // 3
    assert len(gl) == 6 * nf and len(gb) == 12 * nf
    f = max(range(nf), key=lambda i: gn[3 * i + 2] if gn[3 * i + 1] == 4 else 0)
    _, _, _, n_, o_, w = gl[6 * f:6 * f + 6]
    c = gn[3 * f + 2]
    Kg = gb[12 * f + 2:12 * f + 12]
    Ko, Go, Kn, Gn = flt(o_)[:10], flt(o_)[10], flt(n_)[:10], flt(n_)[10]
    assert Kg == [T.blend(T.blend(x, y, 5), y, w) for x, y in zip(Kn, Ko)]
    assert c == cards(ROOT / 'front' / 'glides.cards')[o_ * 3 * (len(cards(ROOT / 'front' / 'filters.cards')) // 11)
                                                        + 3 * n_ + T.GLIDE_W.index(w)]
    names = filter_names()
    fo, dbo, Eo = lattice_response(Ko, Go, voiced[o_])
    _, dbn, En = lattice_response(Kn, Gn, voiced[n_])
    _, dbg, Eg = lattice_response(Kg, Go, voiced[o_])
    loss = 10 * math.log10(Eo / Eg)
    a2.plot(fo, dbo, color=INK, lw=1.8, label='own: %s %s (filter %d)' % (names[o_][0], names[o_][1], o_))
    a2.plot(fo, dbn, color=GREY, lw=1.6, label='neighbour: %s %s (filter %d)' % (names[n_][0], names[n_][1], n_))
    a2.plot(fo, dbg, color=RED, lw=1.6, ls=(0, (4, 2)), label='blended, own gain')
    a2.plot(fo, dbg + 20 * math.log10(c / 100), color=ACCENT, lw=2, label='blended × %d / 100' % c)
    a2.set_xlim(0, 4000)
    a2.set_ylabel('Level (dB)')
    a2.set_xlabel('Frequency (Hz)')
    lo, hi = a2.get_ylim()
    a2.set_ylim(hi - 82, hi + 24)
    a2.legend(loc='upper right', fontsize=10.5, handlelength=1.8)
    a2.grid(color=RULE, lw=0.5)
    label(a2, 'b')
    t = f * 0.025
    cap = ('Spectral envelopes of filters from the phoneme table. Each curve is computed here in floating point as '
           'one pulse passes through the excitation\u2019s low-pass (voiced filters only), the ten-stage lattice with '
           'the table\u2019s reflection coefficients and the de-emphasis 0.9, times the filter\u2019s gain. (a) The '
           'start targets of IY, AA and UW and the noise filter of S, each with its own gain. (b) The glide in the '
           'README sentence with the largest level factor, at frame %d (%.3f s). The frame\u2019s own '
           'filter (%s %s) is moved towards halfway to its neighbour’s (%s %s) with weight %d tenths, by '
           'blending the reflection coefficients as the glideb program punched them. With the own filter’s gain '
           'the blend is %.1f dB quieter than the own filter (dashed red); the glide table’s factor %d, fetched '
           'by gnorm, restores it (green). Data from front/filters.cards and front/glides.cards and the taps of '
           'glides, glideb and gnorm (talk under heartburn).'
           % (f, t, names[o_][0], names[o_][1], names[n_][0], names[n_][1], w, loss, c))
    save(fig, 'filters', cap)


# --- Section 4.4: pitch ---------------------------------------------------------------------------------------------
def fig_pitch():
    fr = frames()
    seg = segments()
    decl = cards(WORK / 'tap8' / 'decl')
    t = np.arange(len(fr)) * 0.025
    f0 = np.array([8000 / P if v == 1 else np.nan for v, P, A, K in fr])
    fig, ax = plt.subplots(figsize=(W_IN, 4.6))
    fig.subplots_adjust(left=0.14, right=0.97, top=0.80, bottom=0.13)
    named = set()
    for s in seg:
        if s['pc'] and s['s'] and s['name'] in vowels():
            x0, x1 = s['f0'] * 0.025, (s['f0'] + s['n']) * 0.025
            ax.axvspan(x0, x1, color=LIGHT if s['s'] == 1 else PALE, lw=0, zorder=0)
            if s['word'] not in named:
                ax.text((x0 + x1) / 2, 1.01, WORDS[s['word']], transform=ax.get_xaxis_transform(), rotation=90,
                        ha='center', va='bottom', fontsize=10.5, color=INK)
                named.add(s['word'])
    ax.plot(t + 0.0125, decl, color=GREY, lw=1.2, ls=(0, (4, 3)), zorder=1, label='declination (decl)')
    ax.plot(t + 0.0125, f0, color=ACCENT, lw=1.8, marker='o', ms=2.5, zorder=2, label='8000 / P, voiced frames')
    ax.set_xlim(0, len(fr) * 0.025)
    ax.set_ylim(70, 170)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Fundamental frequency (Hz)')
    ax.legend(loc='lower left', fontsize=10.5, ncol=1)
    ax.grid(axis='y', color=RULE, lw=0.5)
    nv = int(np.sum(~np.isnan(f0)))
    cap = ('The fundamental frequency of the README sentence, 8000 / P for each of its %d voiced frames, from the '
           'pitch period P on the frame cards the front end punched (green; points 25 ms apart, at the frames’ '
           'centres). Shading marks the frames of vowels with primary stress (darker) and secondary stress (lighter), '
           'with each word named once above, where the rise program raises the pitch by 15 or 7 percent. The dashed line is '
           'the declination the decl program punched, 130 Hz falling towards 100 Hz across each sentence by '
           'Bresenham’s method; the second sentence starts again at 130 Hz. Each sentence ends with the fall '
           'towards 85 Hz. Data from talk --frames and the taps of feat, nframes and decl (heartburn).' % nv)
    save(fig, 'pitch', cap)


def vowels():
    tb, rec, _ = table()
    return {p for p in tb.PHONEMES if rec(tb.CODE[p])[tb.F_KIND] == tb.KIND['vowel']}


# --- Section 5.1: excitation --------------------------------------------------------------------------------------
def fig_excitation(vb):
    e = vb['excite']
    fr = frames()
    seg = segments()
    # a voiced stretch: the middle of the longest vowel; an unvoiced one: the middle of the longest
    # voiceless fricative
    tb, rec, _ = table()
    v = max((s for s in seg if s['pc'] and s['name'] in vowels()), key=lambda s: s['n'])
    u = max((s for s in seg if s['pc'] and s['name'] in ('S', 'SH', 'F', 'TH')), key=lambda s: s['n'])
    n = 160                                                     # 20 ms
    fig, axs = plt.subplots(2, 1, figsize=(W_IN, 6.2))
    fig.subplots_adjust(left=0.16, right=0.97, top=0.93, bottom=0.09, hspace=0.5)
    for ax, s, lab in ((axs[0], v, 'a'), (axs[1], u, 'b')):
        mid = (s['f0'] + s['n'] // 2) * 200
        x0 = mid - n // 2
        x0 -= x0 % 20
        ys = np.array(e[x0:x0 + n])
        ts = (np.arange(n) + x0 - s['f0'] * 200) / RATE * 1000
        ax.vlines(ts, 0, ys, color=ACCENT, lw=1.1)
        ax.plot(ts, ys, 'o', ms=2.2, color=ACCENT)
        ax.axhline(0, color=INK, lw=0.6)
        ax.set_xlim(ts[0], ts[-1])
        ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(5))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%d'))
        ax.set_xlabel('Time from the start of %s (ms)' % s['name'])
        ax.set_ylabel('Excitation value')
        label(ax, lab)
        fi = x0 // 200
        V, P, A, _ = fr[fi]
        if s is v:
            ax.set_title('%s in "%s", voiced: P = %d samples, A = %d' % (s['name'], WORDS[s['word']], P, A),
                         fontsize=12, loc='left', pad=8)
        else:
            ax.set_title('%s in "%s", unvoiced: A = %d' % (s['name'], WORDS[s['word']], A), fontsize=12, loc='left',
                         pad=8)
        assert V == (1 if s is v else 0)
    cap = ('The excitation as the excite program punched it, one value a sample, for 20 ms in the middle of two sounds of the README sentence, the longest vowel and the longest voiceless fricative. '
           '(a) Voiced: a pulse of height A every P samples through the one-pole low-pass e = pulse + 0.5 e '
           '(formed as five ADDs and SFT 01, truncated toward zero), which leaves each pulse with a tail of halving '
           'values. (b) Unvoiced: +A or -A by the sign of x - 500, where x follows the generator x = 21 x + 7 mod 1000. '
           'P and A are those of the frame card; within a frame they move by tenths of the change to the next. Data '
           'from interp, steps and excite run on ref/cardiac.py on the frame cards of talk --frames; the values '
           'equal ref/voice_ref.py’s and the programs’ instruction counts equal heartburn’s.')
    save(fig, 'excitation', cap)


# --- the contact sheet ----------------------------------------------------------------------------------------------
def chrome():
    for p in sorted(glob.glob(os.path.expanduser('~/Library/Caches/ms-playwright/chromium_headless_shell-*/*/'
                                                 'chrome-headless-shell'))):
        return p
    return shutil.which('chrome-headless-shell') or shutil.which('chromium')


def render(svg, png, width):
    """A browser's rendering of an SVG at a page width of `width` CSS px, as a PNG (2x)."""
    txt = Path(svg).read_text()
    m = re.search(r'viewBox="([\d.\s-]+)"', txt)
    vw, vh = [float(v) for v in m.group(1).split()][2:]
    height = int(math.ceil(width * vh / vw))
    page = WORK / ('page-%s.html' % Path(svg).stem)
    page.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff}img{display:block;'
                    'width:%dpx}</style><img src="%s">' % (width, Path(svg).resolve().as_uri()))
    subprocess.run([chrome(), '--headless', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=2',
                    '--user-data-dir=%s' % (WORK / 'chrome-profile'),
                    '--allow-file-access-from-files', '--window-size=%d,%d' % (width, height),
                    '--screenshot=%s' % png, page.resolve().as_uri()], check=True, capture_output=True)


# --- Section 1: the overview --------------------------------------------------------------------------------------
def fig_overview():
    st = stages(WORK / 'hello48k.v.txt')
    nprog = [len(s) for s in st]
    assert nprog == [25, 43, 11, 7], nprog
    nph = len(cards(WORK / 'hello.phonemes'))
    nfr = len(frames())
    n8 = len(s16(WORK / 'hello8k.s16'))
    n48 = len(s16(WORK / 'hello48k.s16'))
    assert n48 == 6 * n8
    H = 8.3
    fig, ax = blank(W_IN, H)
    xd, wd = 0.12, 1.95                    # data piles, left
    xh, wh = 2.22, 0.62                    # the host's lane
    xp, wp = 3.0, 2.28                     # programs, right
    top, row = H - 0.55, 0.86
    ax.add_patch(Rectangle((xh, 0.12), wh, top - 0.05), )
    ax.patches[-1].set(fc=PANEL, ec='none', zorder=0)
    ax.text(xh + wh / 2, top + 0.22, 'host', ha='center', va='center', fontsize=12, color=MUTED, fontweight='bold')
    ax.text(xd + wd / 2, top + 0.22, 'cards', ha='center', va='center', fontsize=12, color=MUTED, fontweight='bold')
    ax.text(xp + wp / 2, top + 0.22, 'CARDIAC programs', ha='center', va='center', fontsize=12, color=MUTED,
            fontweight='bold')
    data = ['Text\n%d characters' % len(SENTENCE), 'Phoneme cards\n%d' % nph,
            'Frame cards\n%d frames × 13' % nfr, '8 kHz samples\n{:,} \u00d7 2 cards'.format(n8),
            '48 kHz samples\n{:,}'.format(n48)]
    progs = ['%d programs\ntext to phonemes' % nprog[0], '%d programs\nphonemes to frames' % nprog[1],
             '%d programs\nvoice box' % nprog[2], '%d programs\nresampler' % nprog[3]]
    tables = ['Rule and word decks', 'Phoneme, filter\nand glide tables', None, 'Filter coefficients']
    ph, pph = 0.62, 0.66
    for i, d in enumerate(data):
        y = top - (2 * i) * row - ph
        cardpile(ax, xd + 0.1, y, wd - 0.25, ph, d, fs=11.5)
        if i < len(progs):
            yp = top - (2 * i + 1) * row - pph
            box(ax, xp, yp, wp, pph, progs[i], fc=LIGHT, ec=ACCENT, fs=12, r=0.06)
            arrow(ax, xd + wd - 0.08, y + 0.08, xp, yp + pph * 0.65, color=ACCENT, lw=1.6)
            arrow(ax, xp, yp + pph * 0.3, xd + wd - 0.08, top - (2 * i + 2) * row - ph + ph * 0.85, color=ACCENT,
                  lw=1.6)
            if tables[i]:
                yt = yp + 0.06
                ax.text(xd + wd / 2 + 0.05, yt + pph / 2 - 0.06, tables[i], ha='center', va='center', fontsize=10.5,
                        color=MUTED, style='italic', linespacing=1.15)
                arrow(ax, xd + wd - 0.02, yt + pph / 2 - 0.06, xp, yt + pph / 2 - 0.06, color=GREY, lw=1.1,
                      ls=(0, (3, 2)))
    cap = ('The system as four stages of CARDIAC programs, with the counts for the README sentence. Each program '
           'reads one deck of cards and punches one stream of cards; the host (shaded) only moves cards, dealing, '
           'copying, collating and merging them in fixed orders and fetching table records by number (dashed), and '
           'does no arithmetic on the speech. Text becomes %d phoneme cards in %d programs, the phonemes become %d '
           'frames of 13 cards in %d programs, %d programs turn the frames into {:,} samples at 8 kHz (each two '
           'cards, thousands and units), and %d programs resample them to {:,} samples at 48 kHz. Counts from talk '
           '-v, --phonemes and --frames (both versions, heartburn); docs/pipeline.svg shows every program.'
           .format(n8, n48) % (nph, nprog[0], nfr, nprog[1], nprog[2], nprog[3]))
    save(fig, 'overview', cap)


# --- Section 2: lineage ------------------------------------------------------------------------------------------
def fig_lineage():
    H = 6.05
    fig, ax = blank(W_IN, H)
    L, R, w, h = 0.36, 2.92, 2.28, 0.6
    ax.text(L + w / 2, H - 0.25, 'Synthesis by rule', ha='center', fontsize=12.5, fontweight='bold', color=MUTED)
    ax.text(R + w / 2, H - 0.25, 'Signal processing', ha='center', fontsize=12.5, fontweight='bold', color=MUTED)

    def node(x, y, year, who, what, used=True, width=w):
        fs = 11.5 if width == w else 10.5
        box(ax, x, y, width, h, '', fc=PALE if used else 'white', ec=ACCENT if used else GREY,
            lw=1.3 if used else 1, r=0.06)
        ax.text(x + 0.1, y + h - 0.17, year, ha='left', va='center', fontsize=11.5, fontweight='bold',
                color=INK if used else MUTED)
        ax.text(x + (0.58 if year else 0.1), y + h - 0.17, who, ha='left', va='center', fontsize=fs,
                color=INK if used else MUTED)
        ax.text(x + 0.1, y + 0.17, what, ha='left', va='center', fontsize=fs - 1, color=MUTED, style='italic')
        return (x, y, width)

    yy = lambda k: H - 0.95 - k * 0.78
    nrl = node(L, yy(0), '1976', 'Elovitz et al., NRL', 'letter-to-sound rules')
    k79 = node(L, yy(1), '1979', 'Klatt', 'segmental durations')
    k80 = node(L, yy(2), '1980', 'Klatt', 'formant targets')
    mit = node(L, yy(3.25), '', 'MITalk', 'Klatt’s text-to-speech system', used=False)
    hw = (w - 0.1) / 2
    dec = node(L, yy(4.45), '', 'DECtalk', 'c. 1984', used=False, width=hw)
    ct = node(L + hw + 0.1, yy(4.45), '', 'CallText 5010', 'Hawking’s voice', used=False, width=hw)
    sb = node(R, yy(0), '1926', 'Sacia and Beck', 'power of speech sounds')
    br = node(R, yy(1), '1965', 'Bresenham', 'running remainder')
    ka = node(R, yy(2), '1974', 'Kaiser', 'window for filter design')
    mg = node(R, yy(3), '1976', 'Markel and Gray', 'LPC lattice')
    cr = node(R, yy(4), '1983', 'Crochiere, Rabiner', 'polyphase interpolation')
    # Klatt's two papers into MITalk, by a bracket on the left; MITalk into DECtalk and the CallText
    gx = L - 0.16
    for n in (k79, k80):
        ax.plot([n[0], gx], [n[1] + h / 2] * 2, color=GREY, lw=1.1)
    ax.plot([gx, gx], [k79[1] + h / 2, mit[1] + h / 2], color=GREY, lw=1.1)
    arrow(ax, gx, mit[1] + h / 2, L, mit[1] + h / 2, color=GREY, lw=1.1, ms=9)
    for n in (dec, ct):
        arrow(ax, n[0] + n[2] / 2, mit[1], n[0] + n[2] / 2, n[1] + h, color=GREY, lw=1.1, ms=9)
    # the methods this system uses, on two buses into it
    cs_y, cs_h = 0.15, 0.66
    box(ax, 0.75, cs_y, W_IN - 1.5, cs_h, '', fc=LIGHT, ec=ACCENT, lw=1.5, r=0.06)
    ax.text(W_IN / 2, cs_y + cs_h / 2 + 0.12, '2026   cardiac-speech', ha='center', va='center', fontsize=12.5,
            fontweight='bold')
    ax.text(W_IN / 2, cs_y + cs_h / 2 - 0.15, 'each method recast in decimal integer arithmetic', ha='center',
            va='center', fontsize=10.5, color=INK, style='italic')
    join = cs_y + cs_h + 0.3
    for x, nodes in ((L + w + 0.12, (nrl, k79, k80)), (R + w + 0.1, (sb, br, ka, mg, cr))):
        ax.plot([x, x], [nodes[0][1] + h / 2, join], color=ACCENT, lw=1.6)
        for n in nodes:
            ax.plot([n[0] + n[2], x], [n[1] + h / 2] * 2, color=ACCENT, lw=1.6)
        arrow(ax, x, join, W_IN / 2 + (0.5 if x > W_IN / 2 else -0.5), cs_y + cs_h, color=ACCENT, lw=1.6)
    cap = ('The published methods this system draws on (green, joined to it) and the synthesizers that came from '
           'Klatt\u2019s work (grey). Klatt\u2019s work at MIT, which includes his duration rules (1979) and '
           'formant targets (1980), became MITalk, and from it came DECtalk and the CallText 5010 that gave Stephen Hawking his voice (Garcia 2018; '
           'Hallahan 1995). This system takes the NRL letter-to-sound rules (Elovitz et al. 1976) and Klatt’s '
           'rules for its front end, and an LPC lattice (Markel and Gray 1976) and polyphase interpolation '
           '(Crochiere and Rabiner 1983) for its back end. It also uses Sacia and Beck’s powers of speech '
           'sounds (1926), Bresenham’s running remainder (1965) for the fall of the pitch and Kaiser’s '
           'window (1974) for the second resampling filter. Years are those of the paper’s references, and '
           'DECtalk’s is the Computer History Museum’s dating.')
    save(fig, 'lineage', cap)


# --- Section 5.2: the lattice ------------------------------------------------------------------------------------
def fig_lattice():
    stage_h, gap = 0.62, 0.34
    H = 0.85 + 5 * (2 * stage_h + gap) + 0.55
    fig, ax = blank(W_IN, H)
    xf, xb = 1.25, 3.35
    top = H - 0.75
    ax.text(xf, H - 0.2, 'e from excite', ha='center', va='center', fontsize=11.5)
    arrow(ax, xf, H - 0.36, xf, top - 0.02, lw=1.4)
    ys, edges = [], []
    y = top
    for m in range(5):
        mtop = y + 0.08
        for j in range(2):
            i = 10 - 2 * m - j
            yF = y - 0.12                     # the f node
            yB = y - 0.36                     # the b node
            yP = y - 0.56                     # the delayed b(i-1), tapped for the f node
            ys.append((i, yF, yB, yP))
            y -= stage_h
        mbot = y - 0.12
        edges.append((mtop, mbot))
        ax.add_patch(FancyBboxPatch((xf - 0.62, mbot), xb - xf + 1.24, mtop - mbot,
                                    boxstyle='round,pad=0,rounding_size=0.08', fc='none', ec=GREY, lw=1,
                                    ls=(0, (4, 3)), zorder=0))
        ax.text(xb + 0.75, (mtop + mbot) / 2 + 0.12, 'L%d' % (m + 1), ha='left', va='center', fontsize=13,
                fontweight='bold')
        ax.text(xb + 0.75, (mtop + mbot) / 2 - 0.16, 'stages %d, %d' % (10 - 2 * m, 9 - 2 * m), ha='left',
                va='center', fontsize=10.5, color=MUTED)
        y -= gap
    bottom = ys[-1][3] - 0.42
    ax.plot([xf, xf], [top, bottom], color=INK, lw=1.4, zorder=1)
    ax.plot([xb, xb], [ys[0][3], bottom], color=INK, lw=1.4, zorder=1)
    for i, yF, yB, yP in ys:
        ax.add_patch(Circle((xf, yF), 0.11, fc='white', ec=INK, lw=1.3, zorder=3))
        ax.text(xf, yF, '+', ha='center', va='center', fontsize=12, zorder=4)
        arrow(ax, xb, yP, xf + 0.1, yF - 0.05, lw=1.1, ms=9, z=2)
        mx, my = xf + 0.32 * (xb - xf), yF + 0.32 * (yP - yF)
        ax.text(mx + 0.05, my + 0.14, '−k$_{%d}$' % i, ha='left', va='center', fontsize=11, color=ACCENT,
                fontweight='bold')
        ax.text(xf - 0.17, yF, 'f$_{%d}$' % i, ha='right', va='center', fontsize=11)
        box(ax, xb - 0.2, yP - 0.26, 0.4, 0.22, 'z$^{-1}$', fc='white', fs=10.5, r=0.03, z=3)
        if i == 10:
            continue                                   # stage 10's b is never used, so L1 doesn't work it out
        ax.add_patch(Circle((xb, yB), 0.11, fc='white', ec=INK, lw=1.3, zorder=3))
        ax.text(xb, yB, '+', ha='center', va='center', fontsize=12, zorder=4)
        arrow(ax, xf, yB, xb - 0.11, yB, lw=1.1, ms=9, z=2)
        ax.text(xb - 0.5, yB + 0.13, 'k$_{%d}$' % i, ha='center', va='center', fontsize=11, color=ACCENT,
                fontweight='bold')
        ax.text(xb + 0.17, yB, 'b$_{%d}$' % i, ha='left', va='center', fontsize=11)
    ax.text(xf - 0.16, bottom + 0.08, 'f$_{0}$', ha='right', va='center', fontsize=11)
    arrow(ax, xf, bottom, xf, bottom - 0.3, lw=1.4)
    ax.text(xf, bottom - 0.42, 'to output', ha='center', va='center', fontsize=11.5)
    ax.plot([xf, xb], [bottom, bottom], color=INK, lw=1.4)
    ax.text((xf + xb) / 2, bottom + 0.08, 'b$_{0}$ = f$_{0}$', ha='center', va='bottom', fontsize=10.5)
    cut = (edges[0][1] + edges[1][0]) / 2
    ax.text(xf - 0.1, cut, 'f card \u2193', ha='right', va='center', fontsize=10.5, color=RED)
    ax.text(xb + 0.26, cut, 'b card \u2191', ha='left', va='center', fontsize=10.5, color=RED)
    cap = ('The ten-stage lattice as five CARDIAC programs of two stages each (dashed). The forward value f passes '
           'down the left rail and the backward value b up the right; stage i computes f(i-1) = f(i) - k(i) b(i-1) '
           'and b(i) = b(i-1) + k(i) f(i-1), where b(i-1) is from the sample before (z⁻¹). Stage 10’s '
           'b is never used, so L1 does not compute it. Between programs each sample crosses as two cards (marked '
           'in red at the first boundary): f down to the program below, and b back up to the program above for the '
           'next sample. Each program also reads ten coefficient cards every 20 samples, five for each of its '
           'stages. Wiring from src/voice.rs and voice/lattice_top.cq, lattice.cq and lattice_bottom.cq.')
    save(fig, 'lattice', cap)


def fig_memmap():
    sys.path.insert(0, str(RUNCARDIAC))
    try:
        import memmap
        import tipmaps
    except ImportError:
        raise SystemExit('the memory map needs runcardiac\'s memmap.py and tipmaps.py in %s' % RUNCARDIAC)
    path = ROOT / 'voice' / 'lattice.cq'
    ops = set(tipmaps.OPS)
    cells = {}
    cardcells = {'sh': '±', 'sl': '±', 't1h': 'd2', 't1l': 'd2', 't2h': 'd1', 't2l': 'd1', 'finh': 'SFT',
                 'finl': 'SFT', 'hh': '½', 'hl': '½'}
    for line in path.read_text().splitlines():
        m = re.match(r'^\s+(\d\d)\s+(.*)$', line)
        if not m or line.lstrip().startswith(';'):
            continue
        a = int(m.group(1))
        toks = m.group(2).split()
        lab = None
        if toks[0] not in ops and toks[0] != 'DATA':
            lab, toks = toks[0], toks[1:]
        op = toks[0]
        if op == 'DATA':
            if lab in cardcells:
                cells[a] = ('focus', cardcells[lab], False)
            elif lab in ('reth', 'retl'):
                cells[a] = ('var', 'ret', False)
            else:
                cells[a] = ('var', lab, False)
        elif 90 <= a <= 98:
            cells[a] = ('table', 'ADD', False)
        else:
            cells[a] = ('code', op, False)
    filled = len(cells)
    cells[99] = ('var', 'back', False)
    col = tipmaps.COLOURS
    grid = memmap.svg(cells, col, aria='The cells of the lattice program, voice/lattice.cq, as ten lines of ten')
    gw = 422
    keys = [('code', 'Code'), ('focus', 'Coefficient cards, read in as instructions'),
            ('table', 'The row of nine ADDs, running on into 99'), ('var', 'Variables; 99 holds the way back'),
            ('zero', 'Cell 00, always 001'), ('free', 'Free, or the loader’s (01, 02)')]
    kh = 24
    Hh = gw + 16 + kh * len(keys)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
           'aria-label="The cells of the lattice program">' % (gw + 4, Hh, gw + 4, Hh),
           '<style>.grid{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}'
           '.ax{font-size:12px;fill:#586058;text-anchor:middle;font-weight:700}.ad{font-size:8.5px;fill:#7a8478}'
           '.lb{font-size:13px;text-anchor:middle;font-weight:700}.lbs{font-size:9.5px;text-anchor:middle;'
           'font-weight:700}.k{font-family:%s;font-size:13px;fill:%s}</style>' % (FONT_STACK.replace("'", ''), INK),
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           grid.replace('<svg class="grid" ', '<svg class="grid" x="1" y="0" width="%d" height="%d" ' % (gw + 2, gw + 2), 1)]
    for j, (k, t) in enumerate(keys):
        y = gw + 14 + j * kh
        out.append('<rect x="24" y="%d" width="16" height="16" rx="3" fill="%s"/>' % (y, col[k][0]))
        out.append('<text class="k" x="48" y="%d">%s</text>' % (y + 13, t))
    out.append('</svg>')
    focus = sorted(a for a, c in cells.items() if c[0] == 'focus')
    cap = ('The cells of one lattice program, voice/lattice.cq (L2, L3 and L4 run it), which fills %d of the 97 '
           'cells a program has. The row of nine ADDs is cells 90 to 98, and it runs on into cell 99, where the JMP '
           'into it leaves the way back. The ten coefficient cards of each 20-sample step are read straight into '
           'the two multiply routines (orange, cells %s). For each stage they are the sign word (±, ADD t or SUB t), the '
           'two jumps into the row for the coefficient’s digits (d2, d1), the final shift (SFT) and the '
           'rounding half (½), so the routines are rewritten every step. Cells and roles read from the '
           'listing; drawn by runcardiac’s memmap.py.' % (filled, ', '.join('%02d' % a for a in focus)))
    write_svg('lattice-cells', '\n'.join(out) + '\n', cap)


# --- Sections 5.3 and 5.4: spectrograms and the resampler's filters -------------------------------------------------
def stft_db(x, rate=48000, n=1024, hop=240):
    win = np.hanning(n)
    frames_ = np.lib.stride_tricks.sliding_window_view(np.concatenate([np.zeros(n // 2), x, np.zeros(n // 2)]),
                                                        n)[::hop]
    P = np.abs(np.fft.rfft(frames_ * win, axis=1)) ** 2
    return np.arange(P.shape[0]) * hop / rate, np.fft.rfftfreq(n, 1 / rate), P


SPEC_REF = {}


def spectrogram(x, name, cap):
    t, f, P = stft_db(x)
    ref = SPEC_REF.setdefault('ref', P.max())
    db = 10 * np.log10(P / ref + 1e-20)
    fig, ax = plt.subplots(figsize=(W_IN, 5.3), dpi=150)
    fig.subplots_adjust(left=0.15, right=0.97, top=0.97, bottom=0.3)
    im = ax.pcolormesh(t, f / 1000, db.T, cmap=SPEC, vmin=-90, vmax=0, shading='auto', rasterized=True)
    ax.axhline(4, color=RED, lw=1.2, ls=(0, (4, 3)))
    ax.text(t[-1] * 0.995, 4.4, '4 kHz', color=RED, ha='right', va='bottom', fontsize=11)
    ax.set_ylim(0, 24)
    ax.set_yticks(range(0, 25, 4))
    ax.set_xlim(0, t[-1])
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Frequency (kHz)')
    cax = fig.add_axes([0.15, 0.115, 0.82, 0.028])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal')
    cb.set_label('Level (dB, relative to the loudest point of either spectrogram)', fontsize=11)
    cb.outline.set_visible(False)
    save(fig, name, cap)


def fig_spec8():
    x = s16(WORK / 'hello8k.s16')
    SPEC_REF['ref'] = max(stft_db(np.repeat(x, 6))[2].max(), stft_db(s16(WORK / 'hello48k.s16'))[2].max())
    spectrogram(np.repeat(x, 6), 'spectrogram-8k',
                'Spectrogram of the README sentence as the voice box produces it at 8 kHz, played at 48 kHz by '
                'repeating each sample six times, the simplest way a player can raise the rate. Repetition leaves '
                'images of the speech band reflected about every multiple of 8 kHz, so everything above 4 kHz (red '
                'line) is an artefact heard as tones and hiss over the voice. Hann windows of 1,024 samples (21 ms) '
                'every 240 samples (5 ms); levels relative to the loudest point of this figure and the next '
                'spectrogram. Data from talk (heartburn).')


def fig_spec48():
    import up_measure as um
    x = s16(WORK / 'hello48k.s16')
    up = um.images(list(x.astype(int)))[0]
    rep = um.images(list(np.repeat(s16(WORK / 'hello8k.s16'), 6).astype(int)))[0]
    spectrogram(x, 'spectrogram-48k',
                'Spectrogram of the README sentence as the 48 kHz version produces it, resampled by the seven CARDIAC '
                'programs, for comparison with the previous spectrogram, with the same analysis and the same '
                'reference level. For this sentence the energy from 4 to 24 kHz (above the red line) is %.1f dB '
                'relative to 0 to 4 kHz, against %.1f dB for the previous spectrogram (measured as in Figure 16), and '
                'most of what remains is rounding noise rather than images. Data from upsample/target/release/talk '
                'and talk --8k (heartburn).' % (up, rep))


def fir_from_table(path):
    """A stage's filter rebuilt from its table, as the machines read it: the stage, then the coefficient and a
    last-tap flag for each tap, phase by phase (0 2 for the phase that is the sample itself)."""
    import up_table as ut
    c = cards(path)
    stage, R = c[0], (2 if c[0] == 1 else 3)
    phases, cur, i = [], [], 1
    while i < len(c):
        v, last = c[i], c[i + 1]
        i += 2
        if last == 2:
            phases.append(None)
            continue
        cur.append(v)
        if last:
            phases.append(cur)
            cur = []
    if stage == 2:
        phases = phases[-1:] + phases[:-1]                          # the table's order is 1, 2, 0
    N = (ut.N1 if stage == 1 else ut.N2)
    h = [0] * N
    for p, taps in enumerate(phases):
        if taps is None:
            h[(N - 1) // 2] = 1000
            continue
        for j, v in enumerate(taps):
            h[p + R * j] = v
    assert h == (ut.stage1() if stage == 1 else ut.stage2())
    return np.array(h) / 1000, stage


def response_db(h, f, rate, gain):
    w = 2 * np.pi * f / rate
    H = np.abs(np.exp(-1j * np.outer(w, np.arange(len(h)))) @ h) / gain
    return 20 * np.log10(H + 1e-12)


def fig_responses():
    h1, _ = fir_from_table(ROOT / 'upsample' / 'tables' / 'fir1.cards')
    h2, _ = fir_from_table(ROOT / 'upsample' / 'tables' / 'fir2.cards')
    f1 = np.linspace(0, 8000, 1601)
    f2 = np.linspace(0, 24000, 4801)
    d1 = response_db(h1, f1, 16000, 2)
    d2 = response_db(h2, f2, 48000, 3)
    dboth = response_db(h1, f2, 16000, 2) + d2
    at = lambda f, d, x: float(np.interp(x, f, d))
    a3, a4 = at(f1, d1, 3000), at(f1, d1, 4000)
    s1 = -float(d1[f1 >= 4500].max())
    s2 = -float(d2[f2 >= 12000].max())
    pass1 = float(np.abs(d1[f1 <= 3000]).max())
    fig, axs = plt.subplots(3, 1, figsize=(W_IN, 8.2))
    fig.subplots_adjust(left=0.16, right=0.97, top=0.96, bottom=0.07, hspace=0.62)
    for ax, f, d, lab, xl, rate in ((axs[0], f1, d1, 'a', 'Frequency at 16 kHz (kHz)', 16),
                                    (axs[1], f2, d2, 'b', 'Frequency at 48 kHz (kHz)', 48),
                                    (axs[2], f2, dboth, 'c', 'Frequency at 48 kHz (kHz)', 48)):
        ax.plot(f / 1000, d, color=ACCENT, lw=1.6)
        ax.set_xlim(0, f[-1] / 1000)
        ax.set_ylim(-90, 8)
        ax.set_yticks([-80, -60, -40, -20, 0])
        ax.set_ylabel('Gain (dB)')
        ax.set_xlabel(xl)
        ax.axvline(4, color=RED, lw=1, ls=(0, (4, 3)))
        ax.grid(color=RULE, lw=0.5)
        label(ax, lab)
    axs[0].set_xticks(range(0, 9))
    axs[1].set_xticks(range(0, 25, 4))
    axs[2].set_xticks(range(0, 25, 4))
    axs[0].set_title('Stage 1, 39 taps, 8 to 16 kHz', fontsize=12, loc='left', pad=6, x=0.03)
    axs[1].set_title('Stage 2, 19 taps, 16 to 48 kHz', fontsize=12, loc='left', pad=6, x=0.03)
    axs[2].set_title('Both stages', fontsize=12, loc='left', pad=6, x=0.03)
    cap = ('The frequency responses of the two resampling filters, computed from the coefficients in thousandths '
           'that the CARDIAC programs read (upsample/tables/fir1.cards and fir2.cards, which equal '
           'ref/up_table.py’s design), each divided by its gain. (a) Stage 1, the 39-tap least-squares low-pass '
           'at 16 kHz, is within %.1f dB of flat to 3 kHz, %.1f dB down at 4 kHz and at least %.1f dB down from '
           '4.5 kHz. (b) Stage 2, the 19-tap Kaiser-windowed sinc at 48 kHz, is at least %.1f dB down from 12 to '
           '24 kHz. (c) The two together, stage 1’s response repeating every 16 kHz at the 48 kHz rate. The '
           'dashed line marks 4 kHz, the top of the 8 kHz speech band.' % (pass1, -a4, s1, s2))
    save(fig, 'resampler-filters', cap)


# --- Section 6.1: the host ----------------------------------------------------------------------------------------
def fig_host():
    H = 10.3
    fig, ax = blank(W_IN, H)
    cw, ch = 0.36, 0.3

    def card(x, y, t, fc='white', ec=INK, fs=10, w=cw):
        ax.add_patch(Rectangle((x, y), w, ch, fc=fc, ec=ec, lw=1, zorder=2))
        ax.text(x + w / 2, y + ch / 2, t, ha='center', va='center', fontsize=fs, zorder=3)

    def head(y, lab, title, use):
        ax.text(0.12, y, lab, fontsize=13, fontweight='bold', va='center')
        ax.text(0.42, y, title, fontsize=12.5, fontweight='bold', va='center')
        ax.text(0.42, y - 0.27, use, fontsize=10.5, color=MUTED, va='center', style='italic')

    # (a) deal
    y = H - 0.25
    head(y, 'a', 'Deal', 'reduce’s coefficient cards, ten to each lattice program in turn')
    yy = y - 0.85
    for g in range(5):
        x = 0.42 + g * 0.72
        card(x, yy, 'K×10', fc=LIGHT if g % 2 == 0 else PALE, w=0.6, fs=9.5)
        card(x + 0.06, yy - 0.7, 'L%d' % (g + 1), w=0.48)
        arrow(ax, x + 0.3, yy, x + 0.3, yy - 0.7 + ch + 0.02, color=ACCENT, lw=1, ms=8)
    ax.text(0.42 + 5 * 0.72, yy + ch / 2, '… each step', fontsize=10.5, va='center')
    # (b) copy
    y = H - 2.1
    head(y, 'b', 'Copy', 'each 8 kHz sample onto the deck of every tap of the first filter')
    yy = y - 1.05
    card(0.42, yy + 0.35, 'y', fc=LIGHT)
    xs = [1.3 + g * 0.78 for g in range(5)]
    ax.plot([0.42 + cw, xs[-1] + cw / 2], [yy + 0.35 + ch / 2] * 2, color=ACCENT, lw=1)
    for g, t in enumerate(['tap 1', 'tap 2', 'tap 3', '…', 'tap 39']):
        tx = xs[g]
        if t == '…':
            ax.text(tx + cw / 2, yy + ch / 2, t, ha='center', va='center', fontsize=13)
            continue
        card(tx, yy - 0.15, 'y', fc=LIGHT)
        ax.text(tx + cw / 2 + 0.25, yy - 0.15 + ch / 2, t, ha='left', va='center', fontsize=10, color=MUTED)
        arrow(ax, tx + cw / 2, yy + 0.35 + ch / 2, tx + cw / 2, yy - 0.15 + ch + 0.02, color=ACCENT, lw=1, ms=8)
    # (c) collate
    y = H - 3.75
    head(y, 'c', 'Collate', 'feat’s five cards for a sound beside six of its row of the phoneme table')
    yy = y - 1.05
    a_ = ['pc', 's', 'wf', 'pms', 'snd']
    b_ = ['kind', 'inh', 'mn', 'cls9', 'liq', 'vls']
    pitch = 0.43
    for k, t in enumerate(a_):
        card(0.42 + k * pitch, yy, t, fc=LIGHT, fs=9)
    for k, t in enumerate(b_):
        card(0.42 + (k + 5.6) * pitch, yy, t, fc=PALE, fs=9)
    ax.text(0.42 + 2.5 * pitch + cw / 2 - 0.2, yy + 0.45, 'from feat', fontsize=10, color=MUTED, ha='center')
    ax.text(0.42 + 8.1 * pitch + cw / 2, yy + 0.45, 'from the table', fontsize=10, color=MUTED, ha='center')
    yr = yy - 0.75
    for k, t in enumerate(a_ + b_):
        card(0.42 + k * pitch, yr, t, fc=LIGHT if k < 5 else PALE, fs=9)
    arrow(ax, 0.42 + 2 * pitch + cw / 2, yy, 0.42 + 2 * pitch + cw / 2, yr + ch + 0.02, color=ACCENT, lw=1, ms=8)
    arrow(ax, 0.42 + 8.1 * pitch + cw / 2, yy, 0.42 + 7.5 * pitch + cw / 2, yr + ch + 0.02, color=ACCENT, lw=1,
          ms=8)
    # (d) merge
    y = H - 6.0
    head(y, 'd', 'Merge in a fixed order', 'L2’s deck: ten coefficient cards, then twenty times f from L1 '
         'and b from L3')
    yy = y - 1.0
    card(0.42, yy, 'K×10', fc=PALE, w=0.6, fs=9.5)
    card(1.2, yy, 'f', fc=LIGHT)
    card(1.75, yy, 'b', fc='white')
    ax.text(0.72, yy + 0.4, 'reduce', ha='center', fontsize=10, color=MUTED)
    ax.text(1.38, yy + 0.4, 'L1', ha='center', fontsize=10, color=MUTED)
    ax.text(1.93, yy + 0.4, 'L3', ha='center', fontsize=10, color=MUTED)
    yr = yy - 0.75
    x = 0.42
    seq = [('K×10', PALE, 0.6)] + [('f', LIGHT, cw), ('b', 'white', cw)] * 3
    for t, fc, w in seq:
        card(x, yr, t, fc=fc, w=w, fs=9.5)
        x += w + 0.06
    ax.text(x + 0.05, yr + ch / 2, '… 20 pairs, then again', fontsize=10.5, va='center')
    for x0 in (0.72, 1.38, 1.93):
        arrow(ax, x0, yy, x0, yr + ch + 0.02, color=ACCENT, lw=1, ms=8)
    # (e) fetch: the first record of the glide table gnorm asked for in the README sentence
    g = cards(WORK / 'tap8' / 'gnorm')
    rec = next(g[i] for i in range(0, len(g), 3) if g[i] > 0)
    y = H - 8.1
    head(y, 'e', 'Fetch by record number', 'gnorm names a record of the glide table, and the host puts it in its '
         'deck')
    yy = y - 1.2
    card(0.42, yy - 0.3, str(rec), fc=LIGHT)
    ax.text(0.42 + cw / 2, yy + 0.12, 'card', ha='center', fontsize=10, color=MUTED)
    tx = 1.35
    for r, t in enumerate(['record %d' % (rec - 1), 'record %d' % rec, 'record %d' % (rec + 1)]):
        ax.add_patch(Rectangle((tx, yy - 0.05 - r * 0.38), 1.3, 0.32, fc=LIGHT if r == 1 else 'white',
                               ec=ACCENT if r == 1 else GREY, lw=1.2 if r == 1 else 0.8, zorder=2))
        ax.text(tx + 0.65, yy + 0.11 - r * 0.38, t, ha='center', va='center', fontsize=10, zorder=3)
    ax.text(tx + 0.65, yy + 0.4, 'glide table', ha='center', fontsize=10, color=MUTED)
    arrow(ax, 0.42 + cw + 0.02, yy - 0.15, tx - 0.02, yy - 0.27, color=ACCENT, lw=1, ms=8)
    for k in range(4):
        card(3.3 + k * 0.4, yy - 0.3, '', fc=LIGHT)
    ax.text(3.3 + 0.78, yy + 0.12, '291 cards into gnorm’s deck', ha='center', fontsize=10, color=MUTED)
    arrow(ax, tx + 1.32, yy - 0.27, 3.28, yy - 0.15, color=ACCENT, lw=1, ms=8)
    cap = ('The five operations of the host, each with one of its uses in this system. (a) It deals cards a fixed '
           'number at a time to several decks in turn. (b) It copies every card put on a pile onto several decks. '
           '(c) It collates whole records from fixed columns of several piles. (d) It merges several piles, taking a '
           'fixed number of cards from each in a fixed order, each pile waiting its turn. (e) It fetches the record '
           'of a table deck that a card names and puts that record in a deck, as a '
           'librarian fetches a book by its call number; record %d is the first that gnorm asked for in the README '
           'sentence. None of the operations depends on what a card says, except the fetch, which uses it only as a '
           'record number. Uses from src/net.rs, src/front.rs, src/voice.rs and upsample/src/lib.rs.' % rec)
    save(fig, 'host', cap)


# --- Section 7: evaluation ----------------------------------------------------------------------------------------
def fig_images():
    import up_measure as um
    rows = []
    for i, (name, _) in enumerate(SAMPLES):
        up, low = s16(WORK / ('sample%d.48k.s16' % i)), s16(WORK / ('sample%d.8k.s16' % i))
        rep = np.repeat(low, 6)
        rows.append((name, um.images(list(up.astype(int)))[0], um.images(list(rep.astype(int)))[0]))
        if i == 0:
            pu = np.array(um.spectrum(list(up.astype(int))))
            pr = np.array(um.spectrum(list(rep.astype(int))))
    f = np.arange(len(pu)) * 48000 / um.N
    ref = max(pu.max(), pr.max())
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(W_IN, 7.4), gridspec_kw={'height_ratios': [2.1, 1.15]})
    fig.subplots_adjust(left=0.16, right=0.96, top=0.95, bottom=0.08, hspace=0.42)
    a1.axvspan(4, 24, color=PANEL, lw=0, zorder=0)
    a1.plot(f / 1000, 10 * np.log10(pr / ref + 1e-20), color=GREY, lw=1.1, label='each sample six times')
    a1.plot(f / 1000, 10 * np.log10(pu / ref + 1e-20), color=ACCENT, lw=1.2, label='CARDIAC resampler')
    a1.set_xlim(0, 24)
    a1.set_ylim(-100, 5)
    a1.set_xticks(range(0, 25, 4))
    a1.set_xlabel('Frequency (kHz)')
    a1.set_ylabel('Power (dB re maximum)')
    a1.legend(loc='upper right', fontsize=10.5)
    a1.grid(color=RULE, lw=0.5)
    label(a1, 'a')
    a1.set_title(SAMPLES[0][0], fontsize=12, loc='left', x=0.03, pad=6)
    for k, (name, u, r) in enumerate(rows):
        a2.plot([u, r], [k, k], color=RULE, lw=2, zorder=1)
        a2.plot(u, k, 'o', color=ACCENT, ms=8, zorder=2)
        a2.plot(r, k, 'o', color=GREY, ms=8, zorder=2)
        a2.text(u + 1.2, k, '%.1f' % u, ha='left', va='center', fontsize=10.5, color=ACCENT)
        a2.text(r - 1.2, k, '%.1f' % r, ha='right', va='center', fontsize=10.5, color=MUTED)
        a2.text(-25, k - 0.3, name, ha='center', va='bottom', fontsize=11)
    a2.set_yticks([])
    a2.set_ylim(len(rows) - 0.5, -0.85)
    a2.set_xlim(-50, 0)
    a2.set_xlabel('Energy 4–24 kHz re 0–4 kHz (dB)')
    a2.spines['left'].set_visible(False)
    a2.grid(axis='x', color=RULE, lw=0.5)
    label(a2, 'b')
    cap = ('Images above 4 kHz. (a) The power spectrum of "%s" averaged over the whole utterance (Hann windows of '
           '4,096 samples, half overlapping), for the 48 kHz output of the CARDIAC resampler and for the same 8 kHz '
           'samples each repeated six times; shading marks 4 to 24 kHz, where the 8 kHz speech has nothing. (b) The '
           'energy from 4 to 24 kHz relative to 0 to 4 kHz for the paper\u2019s three sample texts, as in the table of '
           'Section 7.2, which is %s for the resampler (green) against %s for repetition (grey). Measured by '
           'ref/up_measure.py on the output of upsample/target/release/talk and talk --8k (heartburn).'
           % (SAMPLES[0][0], ', '.join('%.1f' % r[1] for r in rows) + ' dB',
              ', '.join('%.1f' % r[2] for r in rows) + ' dB'))
    save(fig, 'images', cap)


def fig_cost():
    st = stages(WORK / 'hello48k.v.txt')
    secs = len(s16(WORK / 'hello8k.s16')) / RATE
    names = ['Text to phonemes', 'Phonemes to frames', 'Voice box, 8 kHz', 'Resampling to 48 kHz']
    mult = {'L1', 'L2', 'L3', 'L4', 'L5', 'fir1', 'fir2'}
    tot = [sum(c for _, c in s) for s in st]
    rows_ = [sum(c for n, c in s if n in mult) for s in st]
    assert tot == [860492, 2209801, 40408815, 126353878], tot
    fig, ax = plt.subplots(figsize=(W_IN, 3.9))
    fig.subplots_adjust(left=0.05, right=0.95, top=0.82, bottom=0.17)
    y = np.arange(4)
    ax.barh(y, [(t - r) / secs / 1e6 for t, r in zip(tot, rows_)], color=LIGHT, height=0.6, label='other work')
    ax.barh(y, [r / secs / 1e6 for r in rows_], left=[(t - r) / secs / 1e6 for t, r in zip(tot, rows_)],
            color=ACCENT, height=0.6, label='multiplication by rows of ADDs (L1–L5, fir1, fir2)')
    for k in range(4):
        v = tot[k] / secs / 1e6
        ax.text(v + 0.25, k, '%.2f' % v if v < 1 else '%.1f' % v, va='center', fontsize=11.5)
        ax.text(0.15, k - 0.42, '%s, %d programs' % (names[k], len(st[k])), va='bottom', fontsize=11)
    ax.set_yticks([])
    ax.set_ylim(3.6, -0.75)
    ax.set_xlim(0, 18)
    ax.set_xlabel('Million instructions per second of speech')
    ax.spines['left'].set_visible(False)
    ax.legend(loc='lower right', bbox_to_anchor=(1.0, 1.0), fontsize=10.5, ncol=1)
    ax.grid(axis='x', color=RULE, lw=0.5)
    ax.set_axisbelow(True)
    lat = rows_[2] / tot[2] * 100
    lat8 = rows_[2] / sum(tot[:3]) * 100
    cap = ('CARDIAC instructions per second of speech for each stage, for the README sentence (%.2f s of speech; '
           '{:,} instructions in all, loading included). The darker part of each bar is the programs that multiply '
           'by jumping into a row of ADDs. In the voice box they are the five lattice programs, %.0f percent of its '
           'instructions and %.0f percent of the whole 8 kHz pipeline\u2019s, and in the resampler the two filter '
           'programs. Counts from talk -v of the 48 kHz version under heartburn.'
           .format(sum(tot)) % (secs, lat, lat8))
    save(fig, 'cost', cap)


# --- the lot ------------------------------------------------------------------------------------------------------
def write_captions():
    lines = ['# Figures for the cardiac-speech paper', '',
             'Made by docs/figures.py from the programs’ own output and the tables they read.', '']
    for n, f, c in CAPTIONS:
        lines += ['**Figure %d.** %s' % (n, c), '', '`%s`' % f, '']
    (OUT / 'captions.md').write_text('\n'.join(lines))


def sheet(path):
    """Each figure as a browser draws it at 640 px, with its number and caption, a page each (PDF) or tiled (PNG)."""
    import textwrap
    from matplotlib.backends.backend_pdf import PdfPages
    png = WORK / 'png'
    png.mkdir(parents=True, exist_ok=True)
    imgs = []
    for n, f, c in CAPTIONS:
        p = png / (Path(f).stem + '.png')
        render(OUT / f, p, 640)
        imgs.append((n, plt.imread(p), c))
    path = Path(path)
    if path.suffix == '.pdf':
        with PdfPages(path) as pdf:
            for n, im, c in imgs:
                h, w = im.shape[:2]
                cap = textwrap.fill('Figure %d. %s' % (n, c), 96)
                ch = 0.17 * (cap.count('\n') + 1) + 0.4
                fw = 8.5
                fh = min(fw * h / w * 0.82, 11 - ch - 0.6) + ch + 0.6
                fig = plt.figure(figsize=(fw, fh))
                iw = min(0.82, (fh - ch - 0.6) / fh * fh / fw * w / h)
                ax = fig.add_axes([(1 - iw) / 2, (ch + 0.3) / fh, iw, (fh - ch - 0.6) / fh])
                ax.imshow(im)
                ax.axis('off')
                fig.text(0.07, (ch + 0.1) / fh, cap, ha='left', va='top', fontsize=9, color=INK, linespacing=1.4)
                pdf.savefig(fig)
                plt.close(fig)
    else:
        cols, cw = 3, 900
        tiles = []
        for n, im, c in imgs:
            h, w = im.shape[:2]
            tiles.append((n, im, int(h * cw / w)))
        rows_h = [max(t[2] for t in tiles[i:i + cols]) + 70 for i in range(0, len(tiles), cols)]
        W, H = cols * (cw + 40) + 40, sum(rows_h) + 40
        fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
        y = H - 20
        for r in range(0, len(tiles), cols):
            for k, (n, im, h) in enumerate(tiles[r:r + cols]):
                x = 40 + k * (cw + 40)
                ax = fig.add_axes([x / W, (y - 60 - h) / H, cw / W, h / H])
                ax.imshow(im)
                ax.axis('off')
                fig.text(x / W, (y - 30) / H, 'Figure %d' % n, fontsize=22, fontweight='bold', va='center')
            y -= rows_h[r // cols]
        fig.savefig(path, dpi=100)
        plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob('fig*.svg'):
        old.unlink()
    run_all()
    vb = run_voice_front_half()
    fig_overview()          # 1. Introduction
    fig_lineage()           # 2. Background
    fig_tens(vb)            # 3.1 Designing in tens
    fig_codes()             # 4.1 Text to phonemes
    fig_match()
    fig_durations()         # 4.2 Durations
    fig_filters()           # 4.3 Formants and the filter
    fig_pitch()             # 4.4 Pitch
    fig_excitation(vb)      # 5.1 Excitation
    fig_lattice()           # 5.2 The lattice
    fig_memmap()
    fig_spec8()             # 5.3 Output at 8 kHz
    fig_responses()         # 5.4 Resampling on CARDIAC
    fig_spec48()
    fig_host()              # 6.1 The host
    fig_images()            # 7.2 Images above 4 kHz
    fig_cost()              # 7.3 Cost
    write_captions()
    if '--sheet' in sys.argv:
        for p in sys.argv[sys.argv.index('--sheet') + 1:]:
            sheet(p)
    for n, f, c in CAPTIONS:
        print('Figure %2d  %s' % (n, f))


if __name__ == '__main__':
    main()
