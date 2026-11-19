//! join: finished words (phonemes, -20), the boundaries inside spelled words (-1), punctuation and -9 in; the front
//! end's tokens out (text_ref.join): -1 between words and a pause card for punctuation, then -9. The period at the
//! end, if the text didn't end a sentence, is put in by end.
use cardiac::*;

fn main() {
    let mut pending = false; // a boundary is owed before the next phoneme
    let mut phoneme = false; // the last card out is a phoneme
    let mut started = false; // inside a word
    loop {
        let c = inp();
        if c >= 30 {
            if !started {
                started = true;
                if phoneme {
                    pending = true;
                }
            }
            if pending {
                out(-1);
                pending = false;
            }
            out(c);
            phoneme = true;
        } else if c == -20 {
            if !started && phoneme {
                pending = true;
            }
            started = false;
        } else {
            // -1, a pause, or -9 (the owed boundary goes out before the end, but not before a pause)
            if c < -8 && pending {
                out(-1);
            }
            if c < -1 {
                pending = false;
            }
            out(c);
            phoneme = false;
            if c < -8 {
                break;
            }
        }
    }
}
