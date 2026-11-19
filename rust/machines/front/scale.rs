//! scale: a frame's snd, V and level A, and a mode and factor y, in; snd, V and the new A out
//! (front_machines.f8_chain, mulx): mode 1, A y / 1000 (front_ref.mul3); mode 3, 0; mode 0, A as it was.
use cardiac::*;

include!("../shared/arith.rs");

fn main() {
    loop {
        let snd = inp();
        let v = inp();
        let mut a = inp();
        let mode = inp();
        let y = inp();
        if mode == 1 {
            a = mul3(a, y);
        } else if mode == 3 {
            a = 0;
        }
        out(snd);
        out(v);
        out(a);
    }
}
