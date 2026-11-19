//! spinfo: first whether the text has a small letter, then numf's cards in; out the same, but each word's card
//! after its -10 (1 if the word has a small letter, 2 for a number's word, else 0) is followed by three more for
//! spcls: how many letters the word has (apostrophes aside), its first letter, and whether it has a vowel A, E, I,
//! O or U (the part of text_ref.spdec that counts).
use cardiac::*;

const APOSTROPHE: i16 = 27;

fn main() {
    out(inp());
    let (mut letters, mut vowel, mut first) = (0, 0, 0);
    loop {
        let c = inp();
        out(c);
        if c > 0 && c < 29 {
            if c != APOSTROPHE {
                if letters < 1 {
                    first = c;
                }
                letters += 1;
                if c < 6 {
                    vowel = 1;
                }
            }
        } else if c == -10 {
            out(inp());
            out(letters);
            out(first);
            out(vowel);
            (letters, vowel) = (0, 0);
        }
    }
}
