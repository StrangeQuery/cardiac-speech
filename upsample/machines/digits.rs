//! digits: a filter's table in (upsample/tables/fir1.cards or fir2.cards: the stage, then two cards a tap, its
//! coefficient in thousandths and whether it ends its phase); for words, the stage, and then for each tap the sign
//! word that fir runs first, ADD t or SUB t, the coefficient's three digits d1, d2 and d3 (|c| = 0.d1 d2 d3), and
//! the card that says whether it ends its phase. The digits are found by counting down, as dividing takes more cells.
use cardiac::*;

// fir's cell t (upsample/hand/fir.cq), where it reads the sample
const T: i16 = 54;

fn main() {
    out(inp());
    loop {
        let mut m = inp();
        let last = inp();
        let mut sign = 200 + T;
        if m < 0 {
            m = -m;
            sign = 700 + T;
        }
        out(sign);
        let mut d1 = 0;
        while m >= 100 {
            m -= 100;
            d1 += 1;
        }
        let mut d2 = 0;
        while m >= 10 {
            m -= 10;
            d2 += 1;
        }
        out(d1);
        out(d2);
        out(m);
        out(last);
    }
}
