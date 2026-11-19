//! postd: postc's cards in; each rules word's phonemes out with their secondary stress (the second half of
//! text_ref.postc): in a word that isn't a function word, each long vowel (codes 3 to 12, 30 to 129 as cards) after
//! its primary-stressed vowel gets stress 2, but not IY (30) at the end. Each phoneme waits for the next card, which
//! says whether it was the last. The -30 and fn go. Anything else goes through.
use cardiac::*;

fn main() {
    loop {
        let x = inp();
        if x != -30 {
            out(x);
            continue;
        }
        let function = inp();
        let mut seen = function > 0; // the primary-stressed vowel has gone by (a function word gets none)
        let mut held = -1; // the phoneme waiting, none at first
        loop {
            let p = inp();
            if held > 0 {
                let mut q = held;
                if !seen {
                    seen = q < 190 && q % 10 == 1;
                } else if function < 1 && q < 130 && (q != 30 || p > 0) {
                    q += 2;
                }
                out(q);
            }
            if p < 0 {
                out(p);
                break;
            }
            held = p;
        }
    }
}
