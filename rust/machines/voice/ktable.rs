//! ktable: reduce's five cards for each lattice coefficient k in (the sign word, the jumps for its second and first
//! digits, SFT 0L and the rounding half), and out the twelve cards kmul reads for it: n times 0 to 9, where n is
//! k's two digits as a number, negative when k is; the rounding half, negative when k is; and L less 2. An L of 3
//! goes out as 2, with n and the half a tenth as much (k's second digit is 0 then), which comes to the same product.
//! In a step whose A is 0 reduce sends the cards of k = 0, four SFT 00 and a half of 0; their SFT 00 for SFT 0L
//! gives an L of 0, and n stays 0 (d1 and d2 are 499 then, not digits).
use cardiac::*;

fn main() {
    loop {
        let neg = inp() > 500;
        let d2 = 899 - inp();
        let d1 = 899 - inp();
        let mut lead = inp() - 400;
        let mut half = inp();
        let mut n = 0;
        if lead > 2 {
            n = d1;
            half /= 10;
            lead = 2;
        } else if lead > 0 {
            n = d1 * 10 + d2;
        }
        if neg {
            n = -n;
            half = -half;
        }
        let mut v = 0;
        // Unrolled five times on purpose. As `for _ in 0..10 { out(v); v += n; }` it is 82 cells against 94, but on
        // the README's test sentence ktable runs 4,005,186 instructions against 2,725,222, about 40 more a
        // coefficient, and the all-Rust lattice 1,024 a sample against 1,004.
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
