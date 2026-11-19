#!/opt/homebrew/bin/python3
"""LPC encoder: 8 kHz WAV -> text frames (voiced, pitch, gain, k1..k10).

usage: encode.py in.wav out.frames
"""
import math
import sys
from common import read_wav, write_frames, FRAME, ORDER, PRE


def autocorr(x, maxlag):
    n = len(x)
    return [sum(x[i] * x[i + l] for i in range(n - l)) for l in range(maxlag + 1)]


def levinson(r, order):
    """Returns reflection coefficients k[1..order] (list, 0-based) for A(z) = 1 + sum a_j z^-j,
    and the final normalized prediction error.  Convention: k_i = a_i^(i)."""
    a = [0.0] * (order + 1)
    a[0] = 1.0
    e = r[0]
    ks = []
    for i in range(1, order + 1):
        if e <= 0:
            ks.append(0.0)
            continue
        acc = r[i] + sum(a[j] * r[i - j] for j in range(1, i))
        k = -acc / e
        k = max(-0.999, min(0.999, k))
        ks.append(k)
        new = a[:]
        new[i] = k
        for j in range(1, i):
            new[j] = a[j] + k * a[i - j]
        a = new
        e *= (1 - k * k)
    return ks, a


def inverse_filter(x, a):
    order = len(a) - 1
    return [sum(a[j] * x[n - j] for j in range(order + 1) if n - j >= 0) for n in range(len(x))]


def pitch(x, lo=20, hi=160):
    """Simple autocorrelation pitch detector on a centre-clipped segment.
    Returns (period, normalized peak)."""
    m = max(abs(v) for v in x) if x else 0
    if m == 0:
        return 0, 0.0
    c = 0.3 * m
    y = [(v - c) if v > c else (v + c) if v < -c else 0.0 for v in x]
    r0 = sum(v * v for v in y)
    if r0 == 0:
        return 0, 0.0
    best, bl = -1.0, 0
    n = len(y)
    for l in range(lo, hi + 1):
        r = sum(y[i] * y[i + l] for i in range(n - l)) / r0 * n / (n - l)
        if r > best:
            best, bl = r, l
    return bl, best


def encode(x):
    pre = [x[0]] + [x[n] - PRE * x[n - 1] for n in range(1, len(x))]
    nfr = len(x) // FRAME
    win_len = 240
    ham = [0.54 - 0.46 * math.cos(2 * math.pi * i / (win_len - 1)) for i in range(win_len)]
    frames = []
    for f in range(nfr):
        c = f * FRAME + FRAME // 2
        seg = [pre[c - win_len // 2 + i] if 0 <= c - win_len // 2 + i < len(pre) else 0.0
               for i in range(win_len)]
        w = [seg[i] * ham[i] for i in range(win_len)]
        r = autocorr(w, ORDER)
        if r[0] < 1e-9:
            frames.append({'v': 0, 'p': 0, 'g': 0.0, 'k': [0.0] * ORDER})
            continue
        r[0] *= 1.0001                      # white-noise correction
        r = [r[l] * math.exp(-0.5 * (2 * math.pi * 60 * l / 8000) ** 2) for l in range(len(r))]  # 60 Hz lag window
        ks, a = levinson(r, ORDER)
        # gain: rms of the prediction residual over the frame (unwindowed, pre-emphasized)
        s0 = f * FRAME
        ctx = pre[max(0, s0 - ORDER):s0 + FRAME]
        res = inverse_filter(ctx, a)[len(ctx) - FRAME:]
        g = math.sqrt(sum(v * v for v in res) / FRAME)
        # pitch on the raw signal, 400-sample window around the frame
        ps = max(0, c - 200)
        P, peak = pitch(x[ps:ps + 400])
        rms = math.sqrt(sum(v * v for v in x[s0:s0 + FRAME]) / FRAME)
        voiced = 1 if (peak > 0.35 and rms > 0.01) else 0
        if rms < 0.002:
            g = 0.0
        frames.append({'v': voiced, 'p': P if voiced else 0, 'g': g, 'k': ks})
    # light pitch smoothing: median of three among voiced neighbours
    for i in range(1, len(frames) - 1):
        trio = [frames[j]['p'] for j in (i - 1, i, i + 1)]
        if frames[i]['v'] and all(frames[j]['v'] for j in (i - 1, i + 1)):
            frames[i]['p'] = sorted(trio)[1]
    return frames


if __name__ == '__main__':
    x = read_wav(sys.argv[1])
    fr = encode(x)
    write_frames(sys.argv[2], fr)
    nv = sum(f['v'] for f in fr)
    print('%s: %d frames, %d voiced, max|k| %.3f' % (sys.argv[1], len(fr), nv,
          max(abs(k) for f in fr for k in f['k'])))
