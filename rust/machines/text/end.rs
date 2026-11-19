//! end: join's tokens in, the same out, with a period (-3) before the end (-9) if the last card before it doesn't
//! end a sentence (-3, -4 or -5) (text_ref.join).
use cardiac::*;

fn main() {
    let mut ended = false;
    loop {
        let c = inp();
        if c < -8 {
            if !ended {
                out(-3);
            }
            out(c);
            break;
        }
        out(c);
        ended = c < -2;
    }
}
