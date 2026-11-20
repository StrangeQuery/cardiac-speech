//! framer: a segment's frames n and send in, a record of six cards a frame out (front_machines.f5_framer): j, the
//! frame's place in the segment; k, its place from the segment's end, n - 1 - j; n; u, its place in tenths,
//! (10 j + 5) / n, counted up by subtraction; whether it is the very last frame of all (the end pad's last); and
//! whether it is the first frame of a sentence.
use cardiac::*;

fn main() {
    let mut new_sentence = true;
    loop {
        let n = inp();
        let send = inp();
        let (mut u, mut r) = (0, 5);
        let mut j = 0;
        while j < n {
            while r >= n {
                r -= n;
                u += 1;
            }
            let k = n - 1 - j;
            out(j);
            out(k);
            out(n);
            out(u);
            out(if send == 3 && k < 1 { 1 } else { 0 });
            out(i16::from(new_sentence));
            new_sentence = false;
            r += 10;
            j += 1;
        }
        if send > 0 {
            new_sentence = true;
        }
    }
}
