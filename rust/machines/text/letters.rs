//! letters: each item (17 cards, from excp: its end card, n and the run with an edge on each side) in; for a word
//! for the rules (an item ended by -21 or -22), a record of 19 cards for each of its letters out: the number of the
//! rule tables' record to fetch (the letter's code, or 0 for an apostrophe), the letter's place i, the word's length
//! n, its end card and the word with its edges (15 cards). Anything else goes out as one record, with 0 to fetch,
//! i and n 0, its end card and its cards. The host deals each record, but for its first card, with the records
//! fetched for it, to left, right and pick.
use cardiac::*;

const APOSTROPHE: i16 = 27;

fn main() {
    let mut word = [0i16; 15];
    loop {
        let end = inp();
        let mut n = inp();
        for x in word.iter_mut() {
            *x = inp();
        }
        if end > -21 {
            // not a word for the rules
            n = 0;
        }
        let mut i = 0;
        loop {
            let mut letter = 0;
            if n > 0 {
                letter = word[i as usize + 1];
                if letter == APOSTROPHE {
                    letter = 0;
                }
            }
            out(letter);
            out(i);
            out(n);
            out(end);
            for x in &word {
                out(*x);
            }
            i += 1;
            if i >= n {
                break;
            }
        }
    }
}
