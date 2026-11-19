//! glideb: a frame's w, then for each of K10 to K1 halfway's m and glidea's K side by side, in; out K10 to K1
//! (front_machines.f6_glide): each K blended towards m, (m (10 - w) + K w) / 10. With w 10 there is no glide, and
//! K stays as it is.
use cardiac::*;

include!("../shared/arith.rs");

fn main() {
    loop {
        let w = inp();
        for _ in 0..10 {
            let m = inp();
            let k = inp();
            out(blend(m, k, w));
        }
    }
}
