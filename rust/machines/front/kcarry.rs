//! kcarry: a frame's snd and glideb's K10 to K1 in; K10 to K1 out, a silent frame taking the filter of the frame
//! before it (zeros at the start) (front_machines.f9_kcarry).
use cardiac::*;

fn main() {
    let mut k = [0i16; 10];
    loop {
        let snd = inp();
        for x in k.iter_mut() {
            let card = inp();
            if snd == 1 {
                *x = card;
            }
        }
        for x in &k {
            out(*x);
        }
    }
}
