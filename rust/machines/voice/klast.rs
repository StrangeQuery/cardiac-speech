//! klast: the last of three machines that multiply by a lattice coefficient k, for the all-Rust lattice that
//! `talk-frames --rust-lattice` runs. Every 20 samples (a step) reduce's SFT 0L for k; for each sample kmid's y, x,
//! t and its card for negating. Out x, and then y less k x, where |k x| is t / 10^(L - 1) (closedloop.rmul), negated
//! first if kfirst said so. A lattice stage is two multiplies: f = f - k b, then b' = b + k f.
use cardiac::*;

fn main() {
    loop {
        let lead = inp() - 400;
        for _ in 0..20 {
            let y = inp();
            let x = inp();
            let mut t = inp();
            let negate = inp();
            if lead > 1 {
                t /= 10;
            }
            if lead > 2 {
                t /= 10;
            }
            out(x);
            out(if negate > 0 { y + t } else { y - t });
        }
    }
}
