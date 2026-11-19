//! fall: a frame's snd, V and level A, and a mode and factor y, in; snd, V and the new A out
//! (front_machines.f8_chain, mulx): mode 2, A less A y / 1000 (front_ref.mul3); mode 0, A as it was.
use cardiac::*;

include!("../shared/arith.rs");

fn main() {
    loop {
        let snd = inp();
        let v = inp();
        let mut a = inp();
        let mode = inp();
        let y = inp();
        if mode == 2 {
            a -= mul3(a, y);
        }
        out(snd);
        out(v);
        out(a);
    }
}
