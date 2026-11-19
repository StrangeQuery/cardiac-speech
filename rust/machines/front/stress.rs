//! stress: each segment's kind, s and wf, after's after, imm and nvs, and ahead's pfw in; out its stress s (a
//! consonant's worked out here), whether it is in its word's last syllable (fs), whether that is right before a
//! pause (pf), and whether a vowel came earlier in its word (bef) (front_machines.f3_stress). A consonant is
//! stressed when a stressed vowel of its word comes right after it, or when it comes before the word's first vowel
//! and that vowel is stressed.
use cardiac::*;

const VOWEL: i16 = 1;
const PAUSE: i16 = 8;

fn main() {
    let mut bef = 0;
    loop {
        let kind = inp();
        let mut s = inp();
        let wf = inp();
        let after = inp();
        let imm = inp();
        let nvs = inp();
        let pfw = inp();
        if kind == PAUSE {
            out(0);
            out(0);
            out(0);
            out(bef);
            continue;
        }
        if wf != 0 {
            bef = 0;
        }
        let syl = kind == VOWEL;
        if !syl {
            s = if imm != 0 || (bef == 0 && nvs != 0) { 1 } else { 0 };
        }
        let fs = if after == 0 && (syl || bef != 0) { 1 } else { 0 };
        out(s);
        out(fs);
        out(if pfw != 0 { fs } else { 0 });
        out(bef);
        if syl {
            bef = 1;
        }
    }
}
