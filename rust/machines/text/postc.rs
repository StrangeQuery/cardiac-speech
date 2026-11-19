//! postc: postb's cards in (a rules word as -30, fn, ah, its phonemes, -20); each rules word out with its primary
//! stress (the first half of text_ref.postc): none in a function word; else the first vowel other than AX (below
//! 180), or with no such vowel the first AX, which becomes AH (ah 1). The word keeps its -30 and fn, for postd.
//! Anything else goes through.
use cardiac::*;

fn main() {
    loop {
        let x = inp();
        out(x);
        if x != -30 {
            continue;
        }
        let function = inp();
        out(function);
        let mut ah = inp();
        let mut primary = function > 0;
        loop {
            let mut p = inp();
            if !primary && p > 0 && p < 190 {
                if p < 180 {
                    p += 1;
                    primary = true;
                } else if ah > 0 {
                    p = 151;
                    ah = 0;
                }
            }
            out(p);
            if p < 0 {
                break;
            }
        }
    }
}
