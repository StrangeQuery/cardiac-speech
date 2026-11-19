//! kfirst: the first of three machines that multiply by a lattice coefficient k, for the all-Rust lattice that
//! `talk-frames --rust-lattice` runs to compare with the hand-written one (hand/lattice*.cq). First a card, 1 to add
//! the product and -1 to take it away; then every 20 samples (a step) two of reduce's cards for k, the sign word
//! (ADD t or SUB t) and the jump for its second digit d2 (899 - d2); and for each sample two cards, y and x. Out y,
//! x, the first step of Horner's rule on |x| (closedloop.rmul), d2 |x| / 10 truncated with |x| as tens and units
//! (d2 |x| can pass a card), and whether to negate the product before it is taken away from y (1) or not (0).
use cardiac::*;

fn main() {
    let add = inp();
    loop {
        // k x has k's sign times x's, and adding it is taking its negative away: for x 0 or more, negate when k
        // is negative and the product is taken away, or k positive and it is added
        let mut negate = if inp() > 500 { 1 } else { 0 };
        if add > 0 {
            negate = 1 - negate;
        }
        let d2 = 899 - inp();
        for _ in 0..20 {
            let y = inp();
            let x = inp();
            let m = x.abs();
            let (tens, units) = (m / 10, m % 10);
            let (mut t, mut u) = (0, 0);
            for _ in 0..d2 {
                t += tens;
                u += units;
            }
            out(y);
            out(x);
            out(t + u / 10);
            out(if x < 0 { 1 - negate } else { negate });
        }
    }
}
