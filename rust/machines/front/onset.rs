//! onset: a frame's segment's kind and s, and decl's pitch, in; out r0, the rise at a stressed vowel's onset: 15
//! percent of the pitch for primary stress and 7 for secondary (front_ref.mulf), or 0 (front_machines.f7_base).
use cardiac::*;

include!("../shared/arith.rs");

fn main() {
    loop {
        let kind = inp();
        let s = inp();
        let base = inp();
        let mut r0 = 0;
        if kind < 2 && s > 0 {
            r0 = mulf(base, if s == 1 { 15 } else { 7 });
        }
        out(r0);
    }
}
