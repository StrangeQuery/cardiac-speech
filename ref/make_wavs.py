"""Step 5: talk on the three texts; the WAVs (prototype/out/*_cardiac.wav); the samples checked against the Python
references end to end (text_ref, front_ref, voice_ref); compared with the Python pipeline's WAVs."""
import os
import struct
import subprocess
import sys
import wave
import front_ref as fr
import table as tb
import text_ref as tr
import voice_ref as vr
sys.path.insert(0, vr.LPC)
import common   # noqa: E402

BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'target', 'release', 'talk')
OUT = os.path.join(vr.LPC, 'out')
TEXTS = [('born1968', "Hello, my name is cardiac and I was born in 1968 to D W Hagelbarger. And now I can talk."),
         ('mtv', "I want my MTV"),
         ('fox', "the quick brown fox jumps over the lazy dog")]
fr.load(tb.C)


def wav_write(path, samples):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(struct.pack('<%dh' % len(samples), *samples))


def stretch(x, n):
    """x resampled linearly to n samples (to set two renderings of the same text side by side)."""
    if len(x) == n:
        return x
    out = []
    for i in range(n):
        t = i * (len(x) - 1) / (n - 1)
        k = int(t)
        f = t - k
        out.append(x[k] * (1 - f) + (x[min(k + 1, len(x) - 1)] * f))
    return out


def rms(x):
    return (sum(v * v for v in x) / len(x)) ** 0.5


for name, text in TEXTS:
    r = subprocess.run([BIN, '-v'], input=text.encode(), capture_output=True)
    n = len(r.stdout) // 2
    got = list(struct.unpack('<%dh' % n, r.stdout))
    path = os.path.join(OUT, name + '_tts_cardiac.wav')
    wav_write(path, got)
    # the references, end to end
    toks = tr.compose(text)
    cards = fr.phonemes_to_cards(toks)
    vals, peak = vr.voice(cards)
    want = [v[0] * 1000 + v[1] for v in zip(vals[0::2], vals[1::2])]
    stats = r.stderr.decode().strip().split('\n')[-1]
    print('%s: %s, %s' % (path, 'exact' if got == want else 'DIFFERENT from the references', stats))
    # against the Python pipeline
    py = common.read_wav(os.path.join(OUT, name + '_tts.wav'))
    pyf = common.read_wav(os.path.join(OUT, name + '_tts_float.wav'))
    ours = [v / 32768 for v in got]
    a = stretch(ours, len(py))
    print('  length %.2f s (Python pipeline %.2f s); rms %.3f peak %.3f (Python %.3f / %.3f)' % (
        len(ours) / 8000, len(py) / 8000, rms(ours), max(map(abs, ours)), rms(py), max(map(abs, py))))
    s = rms(a) / rms(py)
    print('  log-spectral distance, time-stretched to match: to the Python CARDIAC-arithmetic WAV %.1f dB, to its float '
          'WAV %.1f dB; the Python pipeline\'s own two differ by %.1f dB' % (
              common.lsd_db(py, [v / s for v in a]), common.lsd_db(pyf, [v / s for v in a]), common.lsd_db(pyf, py)))
