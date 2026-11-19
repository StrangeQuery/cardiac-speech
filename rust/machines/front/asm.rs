//! asm: a frame's snd, V and A (from the level), its P, its K10 to K1 (from kcarry), and then the next frame's snd
//! and V (the host deals choose's cards again from the second frame on), in; the frame cards for the voice box out,
//! V, P, A, K10 to K1 a frame, then -1 (front_machines.f9_asm). A silent frame is unvoiced when a voiced sound comes
//! right after it (so that the sound isn't faded in), else voiced; an unvoiced frame's P is 0. The very last frame
//! (snd 9) goes out voiced, with A 0, and then -1.
use cardiac::*;

fn main() {
    let mut k = [0i16; 10];
    loop {
        let snd = inp();
        let mut v = inp();
        let mut a = inp();
        let p = inp();
        for x in k.iter_mut() {
            *x = inp();
        }
        if snd > 8 {
            v = 1;
            a = 0;
        } else {
            let next_snd = inp();
            let next_v = inp();
            if snd != 1 {
                v = if next_snd == 1 && next_v == 1 { 0 } else { 1 };
            }
        }
        out(v);
        out(if v > 0 { p } else { 0 });
        out(a);
        for x in &k {
            out(*x);
        }
        if snd > 8 {
            out(-1);
            break;
        }
    }
}
