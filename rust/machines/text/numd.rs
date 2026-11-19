//! numd: scan's cards in; each number (500 + each digit, then -12) out by its digits after the leading zeros
//! (text_ref.numd), for unpack: with six or fewer, -15, how many, and the digits as two numbers of three digits,
//! the last six digits with zeros in front; with seven or more, at the seventh -17 and the first six as two numbers
//! the same way, then a card for each digit from the seventh on (700 + d). Anything else goes through as it is.
//! The digits are held back, each new one shifted in at the end, until it is known which.
use cardiac::*;

fn main() {
    let (mut hi, mut lo, mut count) = (0, 0, 0);
    loop {
        let c = inp();
        if c == -12 {
            if count < 7 {
                out(-15);
                out(count);
                out(hi);
                out(lo);
            }
            (hi, lo, count) = (0, 0, 0);
        } else if c < 500 || c > 509 {
            out(c);
        } else if count > 0 || c > 500 {
            // a digit, not a leading zero
            if count > 5 {
                if count < 7 {
                    out(-17);
                    out(hi);
                    out(lo);
                }
                out(c + 200);
            } else {
                hi = hi % 100 * 10 + lo / 100;
                lo = lo % 100 * 10 + c - 500;
            }
            count += 1;
        }
    }
}
