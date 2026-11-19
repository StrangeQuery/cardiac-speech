//! rules2: Klatt's duration rules 2 to 4 (front_machines.f3_rules2, front_ref.p3). Each segment's kind and liq and
//! stress's fs and pf in; out four factors in hundredths, in the rules' order, 100 where a rule doesn't apply
//! (multiplying by 100 leaves PRCNT as it is: front_ref.mulf of x and 100 is x exactly), so that every segment has
//! the same number of cards. Kinds: 1 a vowel, 2 to 7 consonants, 8 a pause.
use cardiac::*;

fn main() {
    loop {
        let kind = inp();
        let liq = inp();
        let fs = inp();
        let pf = inp();
        let consonant = kind > 1;
        let sound = kind < 8;
        // rule 2: the last syllable before a pause; rule 3: a vowel not before one
        out(if sound && pf > 0 { 140 } else { 100 });
        out(if sound && !consonant && pf < 1 { 60 } else { 100 });
        // a liquid before a pause
        out(if sound && consonant && pf > 0 && liq > 0 { 140 } else { 100 });
        // rule 4: a vowel not in its word's last syllable
        out(if !consonant && fs < 1 { 85 } else { 100 });
    }
}
