//! rules5: Klatt's duration rules 5 and 6 (front_machines.f3_rules2, front_ref.p3). Each segment's kind and wf,
//! after's after and stress's bef in; out two factors in hundredths, in the rules' order, 100 where a rule doesn't
//! apply. Kinds: 1 a vowel, 2 to 7 consonants, 8 a pause.
use cardiac::*;

fn main() {
    loop {
        let kind = inp();
        let wf = inp();
        let after = inp();
        let bef = inp();
        // rule 5: a vowel in a word of several syllables
        out(if kind < 2 && bef + after > 0 { 80 } else { 100 });
        // rule 6: a consonant not at the start of its word
        out(if kind > 1 && kind < 8 && wf < 1 { 85 } else { 100 });
    }
}
