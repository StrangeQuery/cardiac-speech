//! mul: each segment's ten factors in hundredths (rules2's four, rules5's two, rules7's one and rules9's three) in;
//! its PRCNT out: 100, multiplied by each factor in turn (front_ref.mulf; a factor of 100 leaves it as it is)
//! (front_machines.f3_mul, front_ref.p3).
use cardiac::*;

include!("../shared/arith.rs");

fn main() {
    loop {
        let mut pr = 100;
        for _ in 0..10 {
            let f = inp();
            if f != 100 {
                pr = mulf(pr, f);
            }
        }
        out(pr);
    }
}
