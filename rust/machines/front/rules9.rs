//! rules9: Klatt's duration rules 9 and 10 (front_machines.f3_rules9, front_ref.p3). Each segment's kind, ahead's
//! nextk and p1, and stress's pf in; out three factors in hundredths, 100 where none applies. A vowel: rule 9's
//! factor (p1 before a pause, else 70 + 0.3 p1), 120 before another vowel, 70 after one. A consonant: 50 between
//! two consonants, 70 next to one.
use cardiac::*;

fn main() {
    let mut pkind = 0; // the segment before's kind, 0 after a pause
    loop {
        let kind = inp();
        let nextk = inp();
        let p1 = inp();
        let pf = inp();
        let (mut f9, mut f10a, mut f10b) = (100, 100, 100);
        if kind < 2 {
            // a vowel
            f9 = if pf > 0 { p1 } else { 70 + 3 * p1 / 10 };
            if nextk == 1 {
                f10a = 120;
            }
            if pkind == 1 {
                f10b = 70;
            }
        } else if kind < 8 {
            // a consonant: next to a consonant, or between two
            if pkind > 1 {
                f9 = 70;
            }
            if nextk > 1 {
                f9 = if f9 < 100 { 50 } else { 70 };
            }
        }
        out(f9);
        out(f10a);
        out(f10b);
        pkind = if kind > 7 { 0 } else { kind };
    }
}
