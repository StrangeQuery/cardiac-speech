//! pick: the NRL rules' last machine (text_ref.match_word). letters's record for a letter (its place i, its word's
//! length n, the word's end card, the letter's record number, 0 for an apostrophe, and the word, 15 cards), first's
//! rule, and the letter's record of the phonemes
//! table (rust/data/phonemes.cards: each rule's n, the letters it says, and its phonemes, then -2; then 0s, and -1)
//! in. Out, for each word, the phonemes of the first rule whose contexts both match at each letter, moving on by the
//! letters the rule says (the letters it passes over, and apostrophes, get none), then the word's end card; anything
//! that isn't a word for the rules (n 0) as its cards (phonemes, 30 and up; not the edges) and its end card.
use cardiac::*;

fn main() {
    let mut next = 0; // the next letter the rules start at
    loop {
        let i = inp();
        let n = inp();
        let end = inp();
        let letter = inp();
        for _ in 0..15 {
            let c = inp();
            if n < 1 && c > 29 {
                out(c);
            }
        }
        let mut chosen = inp();
        if i < 1 {
            next = 0;
        }
        if i < next || letter < 1 {
            chosen = -1;
        }
        let mut r = 0;
        loop {
            let c = inp();
            if c < -1 {
                r += 1;
            } else if c < 0 {
                break;
            } else if r == chosen {
                if c > 29 {
                    out(c);
                } else if c > 0 {
                    next = i + c;
                }
            }
        }
        if i + 1 >= n {
            out(end);
        }
    }
}
