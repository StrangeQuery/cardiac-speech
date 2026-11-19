//! tailf: a frame's sentence end (1 a statement, 2 a question), rise's pitch and tailt's t in; f0 out
//! (front_machines.f7_tail): for a statement the pitch moves 0.8 of the way to its goal, base + (8 t) / 100, with
//! 8 t as tens and units; for a question all the way, base + t / 10; each division truncated toward zero.
use cardiac::*;

fn main() {
    loop {
        let end = inp();
        let base = inp();
        let t = inp();
        let a = t.abs();
        let mut d = if end == 1 { (8 * (a / 10) + 8 * (a % 10) / 10) / 10 } else { a / 10 };
        if t < 0 {
            d = -d;
        }
        out(base + d);
    }
}
