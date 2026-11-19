//! boost: a frame's snd, V and level A, and a mode and factor y, in; snd, V and the new A out
//! (front_machines.f8_chain, mulx): mode 4, A y / 100 (front_ref.mulf), at most 999; mode 0, A as it was. Horner
//! over y's digits c and b as in mulf (each digit's product taken on A's tens and units), and then A for each
//! hundred, stopping at 999.
use cardiac::*;

fn main() {
    loop {
        let snd = inp();
        let v = inp();
        let mut a = inp();
        let mode = inp();
        let y = inp();
        if mode == 4 {
            let (x1, x0) = (a / 10, a % 10);
            let mut t = 0;
            let mut d = y % 10;
            for _ in 0..2 {
                let (mut tens, mut units) = (0, t);
                for _ in 0..d {
                    tens += x1;
                    units += x0;
                }
                t = tens + units / 10;
                d = y / 10 % 10;
            }
            for _ in 0..y / 100 {
                t = if t > 999 - a { 999 } else { t + a };
            }
            a = t;
        }
        out(snd);
        out(v);
        out(a);
    }
}
