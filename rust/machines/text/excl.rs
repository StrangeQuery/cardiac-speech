//! excl: each item (17 cards, from items: its end card, n, and its run with an edge on each side) and after it the
//! function words (each its letters and -52, then -99) in; out 1 if the item is a word (ended by -10) that is a
//! function word, else 0 (text_ref.excl). The word is matched against each function word as they go by.
use cardiac::*;

fn main() {
    let mut word = [0i16; 15];
    loop {
        let end = inp();
        let mut n = inp();
        for x in word.iter_mut() {
            *x = inp();
        }
        if end != -10 {
            n = -1; // not a word: nothing matches
        }
        let mut found = 0;
        let mut at = 1; // the next letter of the word to match (1 the first), 99 once one has failed
        loop {
            let d = inp();
            if d >= 0 {
                // SAFETY: at is 13 at most (an item holds 13 letters) while it is under 99
                at = if at <= n && unsafe { *word.get_unchecked(at as usize) } == d { at + 1 } else { 99 };
            } else if d < -98 {
                // -99, the end of the deck
                break;
            } else {
                // the end of a word of the deck: the item's word, if it matched all of it
                if at == n + 1 {
                    found = 1;
                }
                at = 1;
            }
        }
        out(found);
    }
}
