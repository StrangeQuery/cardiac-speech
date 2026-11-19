//! nframes: each segment's kind and duration in; its number of 25 ms frames out: the running time in frames,
//! rounded, less the frames handed out so far, but at least one for a sound and two for a stop or an affricate
//! (front_machines.f3_frames). The frames run past a card over a long text, so what is kept is the frames worked
//! out less those handed out.
use cardiac::*;

const STOP: i16 = 4;
const AFFRICATE: i16 = 6;
const PAUSE: i16 = 8;

fn main() {
    let mut rem = 0; // ms over the whole frames
    let mut owed = 0; // whole frames of time less the frames handed out
    loop {
        let kind = inp();
        rem += inp();
        while rem >= 25 {
            rem -= 25;
            owed += 1;
        }
        let mut n = owed;
        if rem >= 13 {
            n += 1;
        }
        let least = if kind == PAUSE {
            0
        } else if kind == STOP || kind == AFFRICATE {
            2
        } else {
            1
        };
        if n < least {
            n = least;
        }
        owed -= n;
        out(n);
    }
}
