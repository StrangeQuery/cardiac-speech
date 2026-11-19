//! left: whether each NRL rule's left context matches at a letter (text_ref.match_word). letters's record for the
//! letter (its place i, and its word with an edge, 28, on each side, padded to 15 cards) and then the letter's
//! record of the left table (rust/data/left.cards) in: each rule's left context, its elements, then -2; then 0s,
//! and -1. Out, for each rule, 1 if its context matches and 0 if not (a rule with no context matches).
//!
//! An element is four cards: the most letters it matches, the fewest, and the range of codes they can be. The left
//! context is read leftwards from the letter before.
use cardiac::*;

fn main() {
    let mut word = [0i16; 15];
    loop {
        let i = inp();
        for x in word.iter_mut() {
            *x = inp();
        }
        let mut pos = i;
        let mut ok = 1;
        loop {
            let most = inp();
            if most < 1 {
                if most < -1 {
                    // the end of a rule
                    out(ok);
                    pos = i;
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
                while start - pos < most {
                    // SAFETY: a context never reads past the edges of the word (checked against
                    // text_ref.match_word), and once an element fails the rest aren't tried
                    let c = unsafe { *word.get_unchecked(pos as usize) };
                    if c < lo || c > hi {
                        break;
                    }
                    pos -= 1;
                }
                if start - pos < least {
                    ok = 0;
                }
            }
        }
    }
}
