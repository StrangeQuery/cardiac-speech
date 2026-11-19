//! glidea: a frame's uu, then the cards of its two target filters a and b side by side (each filter's record is 11
//! cards, K10 to K1 and the gain; the host deals a card of a's and then the same card of b's), in; out the frame's
//! filter, each card of a blended with b's by uu tenths, (x (10 - uu) + y uu) / 10 (front_machines.f6_glide).
use cardiac::*;

include!("../shared/arith.rs");

fn main() {
    loop {
        let u = inp();
        for _ in 0..11 {
            let x = inp();
            let y = inp();
            out(blend(x, y, u));
        }
    }
}
