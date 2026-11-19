//! spcls: first whether the text has a small letter, then spinfo's cards in; out each word's letters and -11 if it
//! is to be spelled out, else -10 (text_ref.spdec). After a word's -10 come its card (1 if it has a small letter, 2
//! for a number's word, else 0), how many letters it has, its first letter and whether it has a vowel. It is
//! spelled when it has no small letter and has a letter, and is one letter other than A and I, or two or more with
//! no vowel A E I O U or in a text that isn't all capitals (a number's words count as all capitals). Anything else
//! goes through as it is.
use cardiac::*;

fn main() {
    let lower_text = inp();
    loop {
        let c = inp();
        if c != -10 {
            out(c);
            continue;
        }
        let lw = inp();
        let letters = inp();
        let first = inp();
        let vowel = inp();
        let mut spelled = false;
        if lw != 1 && letters > 0 {
            spelled = if letters < 2 { first != 1 && first != 5 } else { lw != 2 && lower_text > 0 || vowel < 1 };
        }
        out(if spelled { -11 } else { -10 });
    }
}
