//! decl: a frame's new-sentence card (from framer) and its sentence's L, in; the pitch's declination out, 130 Hz
//! less q, where q goes from 0 to 30 over the sentence's L frames, q = 30 f / L by Bresenham's method: 30 added to
//! a remainder each frame and L taken away as often as it goes, no division (front_machines.f7_base).
use cardiac::*;

fn main() {
    let (mut q, mut rem) = (0, 0);
    loop {
        let new_sentence = inp();
        let l = inp();
        if new_sentence > 0 {
            q = 0;
            rem = 0;
        }
        out(130 - q);
        if q < 30 {
            rem += 30;
            while rem >= l {
                rem -= l;
                q += 1;
            }
            if q > 30 {
                q = 30;
            }
        }
    }
}
