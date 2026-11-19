//! right: whether each NRL rule's right context matches at a letter (text_ref.match_word). letters's record for the
//! letter (its place i, and its word with an edge, 28, on each side, padded to 15 cards) and then the letter's
//! record of the right table (rust/data/right.cards) in: each rule's right context, its elements, then -2; then 0s,
//! and -1. Out, for each rule, 1 if its context matches and 0 if not (a rule with no context matches).
//!
//! An element is four cards: the most letters it matches, the fewest, and the range of codes they can be. The right
//! context is read rightwards from the letter itself.
use cardiac::*;

fn main() {
    let mut word = [0i16; 15];
    loop {
        let i = inp();
        for x in word.iter_mut() {
            *x = inp();
        }
        let mut pos = i + 1;
        let mut ok = 1;
        loop {
            let most = inp();
            if most < 1 {
                if most < -1 {
                    // the end of a rule
                    out(ok);
                    pos = i + 1;
                    ok = 1;
                } else if most < 0 {
                    break;
                }
                continue;
            }
            let least = inp();
            let lo = inp();
            let hi = inp();
            if ok > 0 {
                let start = pos;
                while pos - start < most {
                    // SAFETY: a context never reads past the edges of the word (checked against
                    // text_ref.match_word), and once an element fails the rest aren't tried
                    let c = unsafe { *word.get_unchecked(pos as usize) };
                    if c < lo || c > hi {
                        break;
                    }
                    pos += 1;
                }
                if pos - start < least {
                    ok = 0;
                }
            }
        }
    }
}
