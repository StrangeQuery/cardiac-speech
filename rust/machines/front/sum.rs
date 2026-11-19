//! sum: each segment's kind and send, its stress and its frames in; for the pitch, three cards a segment out: send,
//! and at the segment that ends a sentence (send not 0) L, the sentence's frames up to the end of its last sound,
//! and the start of its tail, the frame of its last primary-stressed vowel (else 0 if the sentence starts with a
//! vowel, else -1); 0s at the other segments (front_machines.f4_sum). fill works out the rest of the summary and
//! hands it back to the sentence's segments.
use cardiac::*;

fn main() {
    let (mut f, mut first_vowel, mut tail, mut last_sound) = (0, -1, -1, -1);
    loop {
        // kind: 1 a vowel, 8 a pause
        let kind = inp();
        let send = inp();
        let s = inp();
        let n = inp();
        if f < 1 {
            first_vowel = if kind < 2 { 0 } else { -1 };
        }
        if kind < 2 && s == 1 {
            tail = f;
        }
        if kind < 8 {
            last_sound = f + n;
        }
        f += n;
        out(send);
        if send > 0 {
            out(if last_sound < 0 { f } else { last_sound });
            out(if tail < 0 { first_vowel } else { tail });
            (f, last_sound, tail) = (0, -1, -1);
        } else {
            out(0);
            out(0);
        }
    }
}
