//! posta: the phoneme cards in; a consonant (190 and up) the same as the card before it is dropped, one of each run
//! of the same consonant (the rules give LITTLE two Ts); a card below 0 clears what came before (text_ref.posta).
use cardiac::*;

fn main() {
    let mut prev = 0;
    loop {
        let c = inp();
        if c < 0 {
            prev = 0;
        } else if c == prev && c >= 190 {
            continue;
        } else {
            prev = c;
        }
        out(c);
    }
}
