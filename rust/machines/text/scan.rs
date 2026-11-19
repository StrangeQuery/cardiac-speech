//! scan: the text in, each character as its record of the ASCII table (text/ascii.cards: its class, 0 not part of
//! a word or number, 1 a capital, 2 a small letter, 3 an apostrophe, 4 a digit, 5 punctuation; and its value, the
//! letter's code, the digit, or the punctuation's card), ended by a record whose class is -1. Out (text_ref.scan):
//! its words (letters and apostrophes, then -10, then 1 if the word has a small letter), numbers (500 + each
//! digit, then -12), punctuation (-2 to -5), and -9 at the end.
use cardiac::*;

fn main() {
    let mut word = false;
    let mut number = false;
    let mut small = 0;
    loop {
        let class = inp();
        let value = inp();
        // a word ends at anything but a letter, a number at anything but a digit
        if word && (class < 1 || class > 3) {
            out(-10);
            out(small);
            word = false;
        }
        if number && class != 4 {
            out(-12);
            number = false;
        }
        if class < 0 {
            out(-9);
            break;
        }
        if class > 3 {
            if class < 5 {
                number = true;
                out(500 + value);
            } else {
                out(value);
            }
        } else if class > 0 {
            if !word {
                word = true;
                small = 0;
            }
            if class == 2 {
                small = 1;
            }
            out(value);
        }
    }
}
