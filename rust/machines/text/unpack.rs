//! unpack: numd's cards in; a number's six digits held as two numbers of three digits out as the digits (the rest
//! of text_ref.numd): after -15 and the count, the six digits, for year and numw; after -17, the six digits as cards
//! of their own (700 + d), the first six of a number of seven digits or more. Anything else goes through as it is.
use cardiac::*;

fn main() {
    loop {
        let c = inp();
        let mut base = 700;
        if c > -16 {
            out(c);
            if c != -15 {
                continue;
            }
            out(inp());
            base = 0;
        }
        for _ in 0..2 {
            let x = inp();
            for k in 0..3 {
                out(base + digit(x, k));
            }
        }
    }
}
