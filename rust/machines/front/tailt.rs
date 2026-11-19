//! tailt: a frame's sentence end (1 a statement, 2 a question), taily's y and rise's pitch, in; out
//! t = (goal - base) y / 10, truncated toward zero, the goal 85 Hz for a statement and 160 Hz for a question, or 0
//! before the tail (y -1) (front_machines.f7_tail). |goal - base| y can pass a card, so y is taken as tens and
//! units.
use cardiac::*;

fn main() {
    loop {
        let end = inp();
        let y = inp();
        let base = inp();
        let mut t = 0;
        if y >= 0 {
            let delta = if end == 1 { 85 - base } else { 160 - base };
            let m = delta.abs();
            let (mut tens, mut units) = (0, 0);
            for _ in 0..y / 10 {
                tens += m;
            }
            for _ in 0..y % 10 {
                tens += m / 10;
                units += m % 10;
            }
            t = tens + units / 10;
            if delta < 0 {
                t = -t;
            }
        }
        out(t);
    }
}
