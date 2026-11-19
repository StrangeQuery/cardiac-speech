//! closure: each segment's kind and frames, and the CINH and CTOT cards of its row of the phoneme table, in;
//! out how many of its frames are its closure (front_machines.f5_closure): all of a pause, all but the last of a
//! stop, and of an affricate n CINH / CTOT of them, rounded, by adding CINH and taking away CTOT, at least one and
//! not all; none otherwise.
use cardiac::*;

const STOP: i16 = 4;
const AFFRICATE: i16 = 6;
const PAUSE: i16 = 8;

fn main() {
    loop {
        let kind = inp();
        let n = inp();
        let cinh = inp();
        let ctot = inp();
        let mut c = 0;
        if kind == PAUSE {
            c = n;
        } else if kind == STOP {
            c = n - 1;
        } else if kind == AFFRICATE {
            let mut rem = 5 * ctot / 10;
            for _ in 0..n {
                rem += cinh;
                while rem >= ctot {
                    rem -= ctot;
                    c += 1;
                }
            }
            c = c.max(1).min(n - 1);
        }
        out(c);
    }
}
