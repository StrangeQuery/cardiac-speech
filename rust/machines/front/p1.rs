//! p1: run on the segments last first. Each segment's kind, wf and cls9, and after's after and imm, in; out a
//! vowel's factor for Klatt's rule 9 (p1, 0 for a consonant or a pause): the class of the consonants after it in
//! its word (the first obstruent's, else the first consonant's), or 120 at the end of the word and 100 before
//! another vowel (front_machines.f2b, front_ref.p2). Kinds: 1 a vowel, 2 a sonorant, 3 a nasal, 4 to 6 a stop,
//! fricative or affricate, 7 HH, 8 a pause.
use cardiac::*;

fn main() {
    let (mut run_cons, mut run_obs) = (0, 0);
    loop {
        let kind = inp();
        let wf = inp();
        let mut cls = inp();
        let after = inp();
        let imm = inp();
        let mut p1 = 0;
        if kind < 2 {
            p1 = run_obs;
            if p1 < 1 {
                p1 = run_cons;
            }
            if p1 < 1 {
                p1 = if after > 0 { 100 } else { 120 };
            }
        }
        out(p1);
        if kind < 2 || kind > 7 || wf > 0 {
            // a vowel, a pause or the start of a word: no consonants after what comes before
            run_cons = 0;
            run_obs = 0;
        } else {
            // a nasal counts 85 only unstressed, and it is stressed right before a stressed vowel of its word
            if kind == 3 && imm > 0 {
                cls = 100;
            }
            run_cons = cls;
            if kind > 3 && kind < 7 {
                run_obs = cls;
            }
        }
    }
}
