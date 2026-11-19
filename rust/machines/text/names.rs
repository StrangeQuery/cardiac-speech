//! names: each card of spell's, and after it the record of the letters deck it asks for (eight cards: a letter
//! name's phoneme codes, then 0), in (text_ref.spell). A spelled letter (100 + its code, 200 + its code for the
//! last) goes out as its name's phonemes, 10 x code + stress: the first vowel other than AX (codes 3 to 17) stressed,
//! 1 for the last letter and 2 for the others; then -1 after each letter but the last. -11 becomes -20, the end of
//! the spelled word; anything else goes through as it is.
use cardiac::*;

fn main() {
    loop {
        let c = inp();
        // a spelled letter is the only card above 100 here; its hundreds say whether it is the last
        let letter = c > 100;
        let mut stress = 3 - c / 100;
        let mut name = letter;
        for _ in 0..8 {
            let p = inp();
            if p < 1 {
                name = false;
            }
            if name {
                let mut s = 0;
                if p > 2 && p < 18 {
                    s = stress;
                    stress = 0;
                }
                out(10 * p + s);
            }
        }
        if !letter {
            out(if c == -11 { -20 } else { c });
        } else if c < 200 {
            out(-1);
        }
    }
}
