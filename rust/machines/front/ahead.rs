//! ahead: run on the segments last first. Each segment's kind and wf in; out the kind of the segment after it
//! (nextk: 0 a pause or none, 1 a vowel, 2 a consonant) and whether its word comes right before a pause (pfw)
//! (front_machines.f2b, front_ref.p2). Kinds: 1 a vowel, 2 a sonorant, 3 a nasal, 4 to 6 a stop, fricative or
//! affricate, 7 HH, 8 a pause.
use cardiac::*;

fn main() {
    let (mut nextk, mut pfw) = (0, 0);
    loop {
        let kind = inp();
        let wf = inp();
        out(nextk);
        out(pfw);
        if kind > 7 {
            nextk = 0;
            pfw = 1;
        } else {
            nextk = if kind < 2 { 1 } else { 2 };
            if wf > 0 {
                pfw = 0;
            }
        }
    }
}
