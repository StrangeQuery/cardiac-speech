// kmul: one multiply by a lattice coefficient k, for the all-Rust lattice that `talk-frames --all-rust` runs,
// included by kadd.rs and ksub.rs, which set SUB. Every 20 samples (a step) ktable's twelve cards for k; for each
// sample y and x in, then x out and y plus k x (kadd) or y less k x (ksub), k x rounded as closedloop.rmul does it.
// A lattice stage is two multiplies, f = f - k b and then b' = b + k f.

fn main() {
    loop {
        let tab = [inp(), inp(), inp(), inp(), inp(), inp(), inp(), inp(), inp(), inp()];
        let half = inp();
        // 0 for a coefficient of L 2, below 0 for L 1
        let shift = inp();
        for _ in 0..20 {
            let y = inp();
            let x = inp();
            // |k x| is n |x| / 10^(L + 1), rounded: |x|'s three digits looked up in the table of n times 0 to 9
            // and added a place apart, the half with them. Not a loop that adds |x| d times for each digit d of k:
            // rust-cardiac compiles that to a counter, a test and a jump for every add (rust-cardiac#33), where
            // hand code jumps into a row of ADDs. The sum before the last shift can pass a card, which is fine
            // inside one expression: it stays in the accumulator.
            let m = x.abs();
            let (h, t, u) = (m / 100, m / 10 % 10, m % 10);
            // SAFETY: x is a card, -999 to 999, so m is 0 to 999 and each of its digits is 0 to 9, as assume says
            // and as the three table reads below need
            unsafe { assume(h >= 0 && h < 10 && t >= 0 && t < 10 && u >= 0 && u < 10) };
            let (a, b, c) = unsafe { (*tab.get_unchecked(h as usize), *tab.get_unchecked(t as usize), *tab.get_unchecked(u as usize)) };
            let mut r = a + (b + c / 10 + half) / 10;
            if shift >= 0 {
                r /= 10;
            }
            out(x);
            // SUB is a constant, so each program keeps one of these
            if SUB {
                out(if x < 0 { y + r } else { y - r });
            } else {
                out(if x < 0 { y - r } else { y + r });
            }
        }
    }
}
