//! halfway: for each of K10 to K1 of a frame, the card of the filter gn and the card of the filter go side by side
//! in; m out, halfway between them, (gn + go) / 2 truncated, as front_ref.blend by 5 tenths (front_machines.f6_glide).
use cardiac::*;

include!("../shared/arith.rs");

fn main() {
    loop {
        let n = inp();
        let o = inp();
        out(blend(n, o, 5));
    }
}
