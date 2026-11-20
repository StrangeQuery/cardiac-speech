//! dur: first the speaking rate in hundredths (front/rate.cards), then each segment's x and base (from base) and
//! its PRCNT (from mul) in; its duration in ms out, DUR = (x PRCNT / 100 + base) rate / 100
//! (front_machines.f3_mul, front_ref.p3). A pause has x 0 and its length as base, so the rate lengthens it too.
use cardiac::*;

include!("../shared/arith.rs");

fn main() {
    let rate = inp();
    loop {
        let x = inp();
        let base = inp();
        let pr = inp();
        out(mulf(mulf(x, pr) + base, rate));
    }
}
