//! taily: a frame's new-sentence card (from framer), and its sentence's tail start and M, in; out how far the
//! frame is into the sentence's final fall or rise, y = 100 (f - tail) / M in hundredths by Bresenham's method, or
//! -1 before the tail starts (or when the sentence has none) (front_machines.f7_tail).
use cardiac::*;

fn main() {
    let (mut f, mut y, mut rem) = (0, 0, 0);
    loop {
        let new_sentence = inp();
        let tail = inp();
        let m = inp();
        if new_sentence > 0 {
            (f, y, rem) = (0, 0, 0);
        }
        out(if tail >= 0 && f >= tail { y } else { -1 });
        f += 1;
        if tail >= 0 && f > tail && y < 100 {
            rem += 100;
            while rem >= m {
                rem -= m;
                y += 1;
            }
            if y > 100 {
                y = 100;
            }
        }
    }
}
