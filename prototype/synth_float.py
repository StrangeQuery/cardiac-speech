#!/opt/homebrew/bin/python3
"""Floating-point LPC reference synthesizer.

usage: synth_float.py in.frames out.wav

Excitation: pulse train at the pitch period (voiced) or +-1 noise from the decimal LCG
(unvoiced), scaled so its power matches the residual power.  10-stage lattice; parameters
interpolated linearly in 10 steps of 20 samples per frame (TMS5100 style: no interpolation
across a voiced/unvoiced change).  De-emphasis 0.9.
"""
import math
import sys
from common import read_frames, write_wav, Noise, STEPS, STEP_LEN, ORDER, PRE


def amplitude(fr):
    """Excitation amplitude: pulse of height g*sqrt(P) has power g^2 over a period of P."""
    if fr['g'] == 0:
        return 0.0
    if not fr['v']:
        return fr['g']
    energy = sum(v * v for v in SHAPES[SHAPE])
    return fr['g'] * math.sqrt(fr['p'] / energy)


def schedule_float(frames):
    """Per-step parameters: list of (voiced, period, amp, [k1..k10])."""
    out = []
    for i, cur in enumerate(frames):
        nxt = frames[i + 1] if i + 1 < len(frames) else cur
        interp = cur['v'] == nxt['v']
        a0, a1 = amplitude(cur), amplitude(nxt)
        for s in range(STEPS):
            t = s / STEPS if interp else 0.0
            ks = [cur['k'][j] + t * (nxt['k'][j] - cur['k'][j]) for j in range(ORDER)]
            P = cur['p'] + t * (nxt['p'] - cur['p'])
            out.append((cur['v'], max(1, int(round(P))) if cur['v'] else 0,
                        a0 + t * (a1 - a0), ks))
    return out


def make_chirp(L=16):
    """Unit-energy linear chirp, 0 to 4 kHz over L samples (the TMS5100 used a chirp too),
    each value rounded to two decimal places so a CARDIAC can hold it as two digit terms."""
    c = [math.sin(math.pi * n * n / (2 * L)) if n else 1.0 for n in range(L)]
    m = max(abs(v) for v in c)
    return [round(0.9 * v / m, 2) for v in c]   # peak 0.9; amplitude() divides by its energy


SHAPES = {'pulse': [1.0], 'chirp': make_chirp()}
SHAPE = 'pulse'


def excitation(sched, seed=123, shape=None):
    """Excitation sequence shared by all synthesizers, before the amplitude: the voiced shape
    value (pulse or chirp) or +-1 noise.  The caller applies the amplitude so the decimal
    model can use its own integer amplitude."""
    sh = SHAPES[shape or SHAPE]
    noise = Noise(seed)
    out = []
    cnt = 0
    j = len(sh)
    for (v, P, A, ks) in sched:
        for _ in range(STEP_LEN):
            if v:
                cnt += 1
                if cnt >= P:
                    cnt = 0
                    j = 0
                out.append(sh[j] if j < len(sh) else 0.0)
                j += 1
            else:
                j = len(sh)
                out.append(float(noise.next_sign()))
    return out


def synth(sched, internal=None):
    """Float lattice.  internal, if a dict, collects max |value| of signals for scaling."""
    exc = excitation(sched)
    b = [0.0] * (ORDER + 1)     # b[i] = backward value of stage i from the previous sample
    y_out = []
    yd = 0.0
    mx = 0.0
    n = 0
    for (v, P, A, ks) in sched:
        for _ in range(STEP_LEN):
            f = exc[n] * A
            n += 1
            m = abs(f)
            for i in range(ORDER, 0, -1):
                k = ks[i - 1]
                f = f - k * b[i - 1]
                b[i] = b[i - 1] + k * f
                if abs(f) > m: m = abs(f)
                if abs(b[i]) > m: m = abs(b[i])
            b[0] = f
            yd = f + PRE * yd
            y_out.append(yd)
            if m > mx: mx = m
    if internal is not None:
        internal['lattice_max'] = mx
        internal['out_max'] = max(abs(v) for v in y_out)
    return y_out


if __name__ == '__main__':
    fr = read_frames(sys.argv[1])
    y = synth(schedule_float(fr))
    write_wav(sys.argv[2], y)
    print('wrote', sys.argv[2], 'peak %.3f' % max(abs(v) for v in y))
