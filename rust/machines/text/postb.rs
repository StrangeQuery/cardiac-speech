//! postb: posta's cards in; a rules word (its phonemes, then -21, or -22 for a function word) out as -30, fn,
//! whether it has no vowel but AX (ah: 1 when not a function word and with no phoneme below 180), its phonemes, then
//! -20 (text_ref.postb; postd finds the last phoneme itself). Anything else goes through as it is. The word is held
//! until its end card; phonemes past the 16th are dropped.
use cardiac::*;

fn main() {
    let mut buf = [0i16; 16];
    let mut n = 0;
    let mut ah = 1;
    loop {
        let c = inp();
        // phonemes are the only cards above 0 here
        if c > 0 {
            if n < 16 {
                buf[n] = c;
                n += 1;
            }
            if c < 180 {
                ah = 0;
            }
            continue;
        }
        let mut end = c;
        if c < -20 {
            out(-30);
            if c < -21 {
                // a function word: no AH
                ah = 0;
                out(1);
            } else {
                out(0);
            }
            out(ah);
            end = -20;
        }
        for i in 0..n {
            // SAFETY: n is 16 at most
            out(unsafe { *buf.get_unchecked(i) });
        }
        out(end);
        n = 0;
        ah = 1;
    }
}
