//! numw: a number of up to six digits in (-15, how many digits, and the six digits d5 to d0); its words out, as
//! groups for say3 (-16 and the group's hundreds, tens and ones) and words (700 + the word's record in the numbers
//! deck, 729 thousand), as text_ref.numg: zero for 0, else thousands and the rest by hundreds, tens and ones. Years
//! have gone already, through year. Anything else goes through as it is.
use cardiac::*;

fn main() {
    loop {
        let c = inp();
        if c != -15 {
            out(c);
            continue;
        }
        let n = inp();
        let d5 = inp();
        let d4 = inp();
        let d3 = inp();
        let d2 = inp();
        let d1 = inp();
        let d0 = inp();
        if n < 1 {
            out(700);
            continue;
        }
        if d5 + d4 + d3 > 0 {
            out(-16);
            out(d5);
            out(d4);
            out(d3);
            out(729);
        }
        out(-16);
        out(d2);
        out(d1);
        out(d0);
    }
}
