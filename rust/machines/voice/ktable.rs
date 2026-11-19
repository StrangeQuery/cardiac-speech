//! ktable: reduce's five cards for each lattice coefficient k in (the sign word, the jumps for its second and first
//! digits, SFT 0L and the rounding half), and out the twelve cards kmul reads for it: n times 0 to 9, where n is
//! k's two digits as a number, negative when k is; the rounding half, negative when k is; and L less 2. An L of 3
//! goes out as 2, with n and the half a tenth as much (k's second digit is 0 then), which comes to the same product.
use cardiac::*;

fn main() {
    loop {
        let neg = inp() > 500;
        let d2 = 899 - inp();
        let d1 = 899 - inp();
        let mut lead = inp() - 400;
        let mut half = inp();
        let mut n = d1 * 10 + d2;
        if lead > 2 {
            n = d1;
            half /= 10;
            lead = 2;
        }
        if neg {
            n = -n;
            half = -half;
        }
        let mut v = 0;
        for _ in 0..2 {
            out(v);
            v += n;
            out(v);
            v += n;
            out(v);
            v += n;
            out(v);
            v += n;
            out(v);
            v += n;
        }
        out(half);
        out(lead - 2);
    }
}
