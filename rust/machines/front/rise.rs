//! rise: a frame's u, decl's pitch and onset's r0 in; the pitch with a stressed vowel's rise out
//! (front_machines.f7_base): r0 at the vowel's onset, falling to 40 percent of it at its end, base + r0 - r0 6 u / 100.
//! The product is by repeated addition, not `*`: see shared/arith.rs.
use cardiac::*;

fn main() {
    loop {
        let u = inp();
        let base = inp();
        let r0 = inp();
        // r0 6 u / 100, adding 6 r0 u times, as tens and units since the product can pass a card
        let p = 6 * r0;
        let (mut tens, mut units) = (0, 0);
        for _ in 0..u {
            tens += p / 10;
            units += p % 10;
        }
        out(base + r0 - (tens + units / 10) / 10);
    }
}
