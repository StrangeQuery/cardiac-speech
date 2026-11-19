//! rules7: Klatt's duration rule 7, for an unstressed segment (front_machines.f3_rules2, front_ref.p3). Each
//! segment's kind, after's after, stress's bef and s, and ahead's nextk in; out a factor in hundredths, 100 where
//! the rule doesn't apply: an unstressed vowel 50 between other syllables of its word, else 70; an unstressed
//! sonorant before a vowel 10, any other unstressed consonant 70. Kinds: 1 a vowel, 2 a sonorant, 3 to 7 other
//! consonants, 8 a pause.
use cardiac::*;

fn main() {
    loop {
        let kind = inp();
        let after = inp();
        let bef = inp();
        let s = inp();
        let nextk = inp();
        let mut f = 70;
        if s == 1 || kind > 7 {
            f = 100;
        } else if kind < 2 {
            if bef > 0 && after > 0 {
                f = 50;
            }
        } else if kind == 2 && nextk == 1 {
            f = 10;
        }
        out(f);
    }
}
