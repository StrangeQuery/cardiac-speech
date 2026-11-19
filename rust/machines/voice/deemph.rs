//! deemph: the lattice's output f in; the de-emphasis yd = f + 0.9 yd out, as its tens and units, both with yd's
//! sign (ref/voice_ref.py, `run`).
//!
//! The reference keeps yd as its thousands H and the rest L, and takes 0.9 yd as 900 H + 0.9 L, with 0.9 L rounded
//! half away from zero (truncated when f is 0, so that in a pause yd dies away to 0). yd reaches about 1,640, more
//! than a card holds, so here it is kept as tens t and units u. Then 900 H + 0.9 L is 9 t + g, where g is 0.9 of
//! the units, (9 |u| + 5) / 10 with yd's sign (the 5 left out when f is 0), and the new
//! yd = 9 t + g + f = 10 (t - t / 10 + f / 10) + (f % 10 - t % 10 + g).
use cardiac::*;

fn main() {
    let mut t: i16 = 0;
    let mut u: i16 = 0;
    loop {
        let f = inp();
        let half = if f != 0 { 5 } else { 0 };
        let mut g = (9 * u.abs() + half) / 10;
        if t < 0 || u < 0 {
            g = -g;
        }
        // the new units, -26 to 26, carried into the tens: 30 is added so that the shifts see a positive number
        let w = f % 10 - t % 10 + g + 30;
        t = t - t / 10 + f / 10 + w / 10 - 3;
        u = w % 10;
        if t < 0 && u > 0 {
            t += 1;
            u -= 10;
        }
        out(t);
        out(u);
    }
}
