"""Shared helpers for the LPC prototype: WAV I/O, frame files, noise, metrics."""
import math
import struct
import wave

RATE = 8000
FRAME = 200          # samples per frame (25 ms)
STEPS = 10           # interpolation steps per frame
STEP_LEN = FRAME // STEPS   # 20 samples per step
ORDER = 10
PRE = 0.9            # pre-emphasis / de-emphasis coefficient (one decimal term: 0.9)


def read_wav(path):
    with wave.open(path, 'rb') as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2, path
        n = w.getnframes()
        data = w.readframes(n)
    return [v / 32768.0 for v in struct.unpack('<%dh' % n, data)]


def write_wav(path, x, peak_norm=False):
    if peak_norm:
        m = max(1e-9, max(abs(v) for v in x))
        x = [v * 0.9 / m for v in x]
    out = []
    for v in x:
        s = int(round(v * 32767))
        out.append(max(-32768, min(32767, s)))
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(struct.pack('<%dh' % len(out), *out))


def write_frames(path, frames):
    with open(path, 'w') as f:
        f.write('# frame voiced pitch gain k1..k10  (gain = residual rms, input full scale = 1)\n')
        for i, fr in enumerate(frames):
            f.write('%d %d %d %.6f %s\n' % (i, fr['v'], fr['p'], fr['g'],
                                            ' '.join('%.5f' % k for k in fr['k'])))


def read_frames(path):
    frames = []
    for line in open(path):
        if line.startswith('#') or not line.strip():
            continue
        t = line.split()
        frames.append({'v': int(t[1]), 'p': int(t[2]), 'g': float(t[3]),
                       'k': [float(v) for v in t[4:4 + ORDER]]})
    return frames


class Noise:
    """Decimal LCG, the one a CARDIAC would run: x = (21 x + 7) mod 1000.
    21x = 2*(10x) + x: CLA x, SFT 10, STO t, ADD t, ADD x, ADD seven, STO x (mod 1000 by STO).
    Full period 1000 (Hull-Dobell).  Sign of (x - 500) gives +-1 noise."""
    def __init__(self, seed=123):
        self.x = seed

    def next_sign(self):
        self.x = (21 * self.x + 7) % 1000
        return 1 if self.x >= 500 else -1


# ---------- metrics ----------

def snr_db(ref, test):
    n = min(len(ref), len(test))
    s = sum(ref[i] ** 2 for i in range(n))
    e = sum((ref[i] - test[i]) ** 2 for i in range(n))
    if e == 0:
        return float('inf')
    return 10 * math.log10(max(s, 1e-30) / e)


def fft(a):
    """In-place iterative radix-2 FFT on a list of complex numbers."""
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    size = 2
    while size <= n:
        w = complex(math.cos(-2 * math.pi / size), math.sin(-2 * math.pi / size))
        half = size // 2
        for start in range(0, n, size):
            wk = 1 + 0j
            for k in range(half):
                u = a[start + k]
                v = a[start + k + half] * wk
                a[start + k] = u + v
                a[start + k + half] = u - v
                wk *= w
        size *= 2
    return a


def log_spectra(x, n=256, hop=200):
    win = [0.54 - 0.46 * math.cos(2 * math.pi * i / (n - 1)) for i in range(n)]
    specs = []
    for start in range(0, len(x) - n, hop):
        a = [complex(x[start + i] * win[i], 0) for i in range(n)]
        fft(a)
        specs.append([10 * math.log10(abs(a[k]) ** 2 + 1e-10) for k in range(1, n // 2)])
    return specs


def lsd_db(ref, test, floor_db=40.0):
    """Log-spectral distance (dB rms over frequency, averaged over frames whose reference
    energy is within floor_db of the loudest frame).  Lower is better."""
    A = log_spectra(ref)
    B = log_spectra(test)
    n = min(len(A), len(B))
    energies = [sum(10 ** (v / 10) for v in A[i]) for i in range(n)]
    top = max(energies)
    tot, cnt = 0.0, 0
    for i in range(n):
        if energies[i] < top * 10 ** (-floor_db / 10):
            continue
        d = [(A[i][k] - B[i][k]) ** 2 for k in range(len(A[i]))]
        tot += math.sqrt(sum(d) / len(d))
        cnt += 1
    return tot / max(cnt, 1)
