//! kmid: the second of three machines that multiply by a lattice coefficient k, for the all-Rust lattice that
//! `talk-frames --rust-lattice` runs. Every 20 samples (a step) two of reduce's cards for k, the jump for its first
//! digit d1 (899 - d1) and the rounding half; for each sample kfirst's y, x, q and its card for negating. Out the
//! same, but q replaced by (q + half + d1 |x|) / 10 truncated (closedloop.rmul), the sum taken as tens and units
//! since it can pass a card.
use cardiac::*;

fn main() {
    loop {
        let d1 = 899 - inp();
        let half = inp();
        for _ in 0..20 {
            let y = inp();
            let x = inp();
            let q = inp();
            let negate = inp();
            let m = x.abs();
            let (tens, units) = (m / 10, m % 10);
            let (mut t, mut u) = (q / 10 + half / 10, q % 10 + half % 10);
            for _ in 0..d1 {
                t += tens;
                u += units;
            }
            out(y);
            out(x);
            out(t + u / 10);
            out(negate);
        }
    }
}
