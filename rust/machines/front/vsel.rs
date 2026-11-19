//! vsel: a frame's snd and V, and its segment's kind and s, and its u, in; out two modes and factors for mulx2 and
//! mulx3 (front_machines.f8_chain): for a sounding voiced vowel frame, 3 dB down when unstressed (mode 1, times
//! 0.708) and the fall across the vowel (mode 2, less 30 u thousandths); else mode 0.
use cardiac::*;

const VOWEL: i16 = 1;

fn main() {
    loop {
        let snd = inp();
        let v = inp();
        let kind = inp();
        let s = inp();
        let u = inp();
        let vowel = kind == VOWEL && snd == 1 && v != 0;
        out(if vowel && s == 0 { 1 } else { 0 });
        out(708);
        out(if vowel { 2 } else { 0 });
        out(if vowel { 30 * u } else { 0 });
    }
}
