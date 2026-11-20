"""How much of the 48 kHz speech is images above 4 kHz: the energy from 4 to 24 kHz against the energy below 4 kHz
(the speech band), from an averaged spectrum (Hann windows of 4,096 samples, half overlapping), for the upsampler's
output and for the same 8 kHz samples each repeated six times, the naive way to make 48 kHz of them.

    python3 up_measure.py SPEECH_48K.s16 SPEECH_8K.s16      # raw s16le files, from talk and talk --8k"""
import cmath
import math
import struct
import sys

N = 4096
BANDS = [(4000, 24000), (4000, 4500), (4500, 8000), (8000, 24000)]


def read(path):
    b = open(path, 'rb').read()
    return list(struct.unpack('<%dh' % (len(b) // 2), b))


def fft(a):
    n = len(a)
    a = a[:]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    m = 2
    while m <= n:
        w = cmath.exp(-2j * math.pi / m)
        h = m // 2
        for k in range(0, n, m):
            wk = 1
            for t in range(h):
                u, v = a[k + t], a[k + t + h] * wk
                a[k + t], a[k + t + h] = u + v, u - v
                wk *= w
        m <<= 1
    return a


def spectrum(x):
    """The averaged power spectrum, bins 0 to N / 2."""
    win = [0.5 - 0.5 * math.cos(2 * math.pi * i / N) for i in range(N)]
    acc = [0.0] * (N // 2 + 1)
    for s in range(0, len(x) - N + 1, N // 2):
        X = fft([x[s + i] * win[i] for i in range(N)])
        for k in range(N // 2 + 1):
            acc[k] += abs(X[k]) ** 2
    return acc


def band(p, lo, hi, rate=48000):
    return sum(v for k, v in enumerate(p) if lo <= k * rate / N < hi)


def images(x):
    """Each band's energy against the speech band's, in dB."""
    p = spectrum(x)
    speech = band(p, 0, 4000)
    return [10 * math.log10(band(p, lo, hi) / speech) for lo, hi in BANDS]


if __name__ == '__main__':
    up, low = read(sys.argv[1]), read(sys.argv[2])
    assert len(up) == 6 * len(low)
    print('energy against the speech band (0-4 kHz), in dB:  ' + '  '.join('%d-%d Hz' % b for b in BANDS))
    for name, x in (('upsampler on CARDIACs', up), ('each sample six times', [v for v in low for _ in range(6)])):
        print('  %-24s' % name + '  '.join('%10.1f' % v for v in images(x)))
