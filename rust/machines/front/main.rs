//! main: each segment's kind, ts and te, the VOICED, NOISE and ALT cards of its row of the phoneme table, and the
//! BACK card of nxtpc's row, in; out the filters its sounding frames speak through (front_machines.f5_main): ma and
//! mb (gliding from ma to mb when uon), whether they are voiced (vm), and whether the segment glides at its ends
//! (gl). A vowel, sonorant, nasal or HH speaks through its own filters; a stop, fricative or affricate through its
//! noise filter (a stop before a back vowel through its other one, ALT).
use cardiac::*;

fn main() {
    loop {
        // kind: 1 a vowel, 2 a sonorant, 3 a nasal, 4 a stop, 5 a fricative, 6 an affricate, 7 HH, 8 a pause
        let kind = inp();
        let ts = inp();
        let te = inp();
        let voiced = inp();
        let noise = inp();
        let alt = inp();
        let next_back = inp();
        let (mut ma, mut mb, mut uon, mut vm, mut gl) = (0, 0, 0, 1, 0);
        if kind > 7 {
            // a pause: no filters
        } else if kind > 3 && kind < 7 {
            ma = noise;
            vm = voiced;
            if kind < 5 {
                vm = 0;
                if alt > 0 && next_back > 0 {
                    ma = alt;
                }
            }
            mb = ma;
        } else {
            (ma, mb, gl) = (ts, te, 1);
            if kind < 2 {
                uon = 1;
            }
            if kind > 6 {
                vm = 0;
            }
        }
        out(ma);
        out(mb);
        out(uon);
        out(vm);
        out(gl);
    }
}
