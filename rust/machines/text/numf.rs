//! numf: each card of say3's, and after it the record of the numbers deck it asks for (ten cards: a number word's
//! letters, -10, padded with 0), in; a number word (700 + its record) out as its letters, -10 and 2 (as for a word
//! in an all-capitals text), anything else as it is (text_ref.numf).
use cardiac::*;

fn main() {
    loop {
        let c = inp();
        if c >= 700 {
            for _ in 0..10 {
                let x = inp();
                if x != 0 {
                    out(x);
                }
            }
            out(2);
        } else {
            skip_cards(10);
            out(c);
        }
    }
}
