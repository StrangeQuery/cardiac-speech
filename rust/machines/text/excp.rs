//! excp: excl's fn and excx's k, the item (17 cards: its end card, n, and its run with an edge on each side), and
//! the record of the exceptions' phonemes for k (12 cards, 10 x code + stress, padded with 0) in; out an item of 17
//! cards (text_ref.excp): an exception as -20, 0 and its phonemes (stress 0 for a function word); another word as
//! -22 (a function word) or -21 and its letters, for the rules (text_ref.excp's -14 and -13; here below -20, so
//! that one test finds them); anything else as it was.
use cardiac::*;

fn main() {
    loop {
        let function = inp();
        let k = inp();
        let mut end = inp();
        if k > 0 {
            for _ in 0..16 {
                inp();
            }
            out(-20);
            out(0);
            for _ in 0..12 {
                let p = inp();
                out(if function > 0 { p - p % 10 } else { p });
            }
            for _ in 0..3 {
                out(0);
            }
            continue;
        }
        if end == -10 {
            end = if function > 0 { -22 } else { -21 };
        }
        out(end);
        for _ in 0..16 {
            out(inp());
        }
        for _ in 0..12 {
            inp();
        }
    }
}
