//! say3: a group of three digits in (-16, the hundreds h, the tens t and the ones o); its number words out, each as
//! 700 + its record in the numbers deck (0 to 19 the ones, 20 to 27 twenty to ninety, 28 hundred): h and hundred
//! when h isn't 0, then the tens and ones as text_ref.words2 says them (text_ref.say3). Anything else goes through
//! as it is.
use cardiac::*;

fn main() {
    loop {
        let c = inp();
        if c != -16 {
            out(c);
            continue;
        }
        let h = inp();
        let t = inp();
        let o = inp();
        if h > 0 {
            out(700 + h);
            out(728);
        }
        if t == 1 {
            out(710 + o);
        } else {
            if t > 1 {
                out(718 + t);
            }
            if o > 0 {
                out(700 + o);
            }
        }
    }
}
