//! psel: a frame's snd, V and P in; the mode and factor for mulx4 out (front_machines.f8_chain): a sounding voiced
//! frame mode 1 and 10 r, r = isqrt(60 P), so that one pulse a period carries the frame's power; else mode 0. The
//! root counts the odd numbers 1, 3, 5 ... that can be taken away from 60 P, which is kept as hundreds and units
//! since it can pass a card. Not `isqrt`: 60 P passes a card for P over 16, and Newton's method with `/` and `%`
//! is 148 cells, which doesn't fit.
use cardiac::*;

fn main() {
    loop {
        let snd = inp();
        let v = inp();
        let p = inp();
        if snd != 1 || v == 0 {
            out(0);
            out(0);
            continue;
        }
        let six = 6 * p; // 60 P = 10 (6 P)
        let mut hundreds = six / 10;
        let mut units = 10 * (six % 10);
        let (mut r, mut odd) = (0, 1);
        'root: loop {
            units -= odd;
            // the odd numbers pass 100, so this can take more than one hundred
            while units < 0 {
                if hundreds < 1 {
                    break 'root;
                }
                hundreds -= 1;
                units += 100;
            }
            r += 1;
            odd += 2;
        }
        out(1);
        out(10 * r);
    }
}
