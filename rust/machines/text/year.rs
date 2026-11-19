//! year: numd's cards in; a number of four digits from 1100 to 1999 (-15, 4, and the digits d5 to d0) out in
//! pairs, as text_ref.numg says years: the groups for say3 (-16 and the group's hundreds, tens and ones) and words
//! (700 + their record in the numbers deck): nineteen hundred, nineteen oh five, nineteen sixty eight. Any other
//! number (and anything else) goes through as it is, for numw.
use cardiac::*;

/// A group of three digits for say3.
#[inline(never)]
fn group(t: i16, o: i16) {
    out(-16);
    out(0);
    out(t);
    out(o);
}

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
        if n == 4 && d3 == 1 && d2 > 0 {
            group(d3, d2);
            if d1 + d0 < 1 {
                out(728);
            } else if d1 < 1 {
                out(730);
                out(700 + d0);
            } else {
                group(d1, d0);
            }
        } else {
            out(-15);
            out(n);
            out(d5);
            out(d4);
            out(d3);
            out(d2);
            out(d1);
            out(d0);
        }
    }
}
