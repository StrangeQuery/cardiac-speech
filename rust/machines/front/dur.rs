//! dur: each segment's x and base (from base) and its PRCNT (from mul) in; its duration in ms out,
//! DUR = x PRCNT / 100 + base (front_machines.f3_mul, front_ref.p3). A pause has x 0 and its length as base.
use cardiac::*;

include!("../shared/arith.rs");

fn main() {
    loop {
        let x = inp();
        let base = inp();
        let pr = inp();
        out(mulf(x, pr) + base);
    }
}
