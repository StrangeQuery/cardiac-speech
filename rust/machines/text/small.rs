//! small: the text in, each character as its record of the ASCII table (text/ascii.cards: its class, 2 a small
//! letter, and its value), ended by a record whose class is -1; out one card, 1 if the text has a small letter and
//! 0 if not (the first part of text_ref.scan). The host deals it ahead of scan's cards, for spcls.
use cardiac::*;

fn main() {
    let mut small = false;
    loop {
        let class = inp();
        let _value = inp();
        if class < 0 {
            break;
        }
        if class == 2 {
            small = true;
        }
    }
    out(i16::from(small));
}
