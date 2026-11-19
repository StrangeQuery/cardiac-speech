#!/bin/bash
# Says a sentence with the rule-based front end and the CARDIAC-arithmetic LPC synthesizer: no recording and no
# speech synthesizer anywhere in the chain.
#
#     tts.sh "sentence" NAME [--rate R] [--noplay]
#
# text_to_phonemes.py (NRL letter-to-sound rules) -> out/NAME_tts.phon
# phonemes_to_frames.py (Klatt formant targets and duration rules) -> out/NAME_tts.frames
# synth_float.py's float lattice on those frames -> out/NAME_tts_float.wav (the closed loop's target)
# closedloop.py NAME_tts 2 (CARDIAC arithmetic, two digit terms per coefficient) -> out/NAME_tts.wav, played.
set -euo pipefail
cd "$(dirname "$0")"
text=$1; name=$2; shift 2
rate=1.0; play=1
while [ $# -gt 0 ]; do
  case $1 in
    --rate) rate=$2; shift 2;;
    --noplay) play=0; shift;;
    *) echo "unknown option $1" >&2; exit 1;;
  esac
done
PY=/opt/homebrew/bin/python3
mkdir -p out
$PY text_to_phonemes.py "$text" "out/${name}_tts.phon"
$PY phonemes_to_frames.py "out/${name}_tts.phon" "out/${name}_tts.frames" --rate "$rate"
$PY -c "
import synth_float as sf, common as c
sf.SHAPE = 'chirp'          # the excitation closedloop.py uses
fr = c.read_frames('out/${name}_tts.frames')
c.write_wav('out/${name}_tts_float.wav', sf.synth(sf.schedule_float(fr)))
"
$PY closedloop.py "${name}_tts" 2
mv "out/${name}_tts_dec_t2_closedloop.wav" "out/${name}_tts.wav"
echo "wrote out/${name}_tts.wav"
if [ $play = 1 ]; then afplay "out/${name}_tts.wav"; fi
