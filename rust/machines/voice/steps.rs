//! steps: V, and the values and steps of P and A, of each frame in (interp's cards for them); the frame's ten steps
//! of 20 samples out, for the excitation: V, P and A for each step, P and A then moving on by their steps.
use cardiac::*;

fn main() {
    loop {
        let v = inp();
        let mut p = inp();
        let dp = inp();
        let mut a = inp();
        let da = inp();
        for _ in 0..10 {
            out(v);
            out(p);
            out(a);
            p += dp;
            a += da;
        }
    }
}
