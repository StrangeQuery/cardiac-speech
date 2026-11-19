//! lsel: a frame's snd and V, its segment's kind, and loud's two loudness cards, in; the mode and factor for mulx1
//! out (front_machines.f8_chain): a silent frame mode 3 (no sound); a sonorant's sounding frame mode 1, times the
//! loudness of the vowel next to it (the voiced one's, or for the breathy first frame the next vowel's); else
//! mode 0.
use cardiac::*;

const SONORANT: i16 = 2;

fn main() {
    loop {
        let snd = inp();
        let v = inp();
        let kind = inp();
        let voiced_loud = inp();
        let breathy_loud = inp();
        if snd != 1 {
            out(3);
            out(0);
        } else if kind == SONORANT {
            out(1);
            out(if v != 0 { voiced_loud } else { breathy_loud });
        } else {
            out(0);
            out(0);
        }
    }
}
