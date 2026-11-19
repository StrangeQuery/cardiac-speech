//! ksteps: the value and step of A and of each of K10 to K1, of each frame in (interp's cards for them); for each
//! of the frame's ten steps, each K after the step's A, for reduce (A says whether the multiplies round or
//! truncate). Each value then moves on by its step.
use cardiac::*;

fn main() {
    let mut k = [0i16; 10];
    let mut dk = [0i16; 10];
    loop {
        let mut a = inp();
        let da = inp();
        for i in 0..10 {
            k[i] = inp();
            dk[i] = inp();
        }
        for _ in 0..10 {
            for i in 0..10 {
                out(a);
                out(k[i]);
                k[i] += dk[i];
            }
            a += da;
        }
    }
}
