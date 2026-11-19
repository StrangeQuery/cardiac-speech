//! after: run on the segments last first. Each segment's kind, s and wf in; out what lies after it in its word:
//! whether a vowel comes later (after), the stress of the vowel right after it (imm), and the stress of the next
//! vowel (nvs) (front_machines.f2a, front_ref.p2).
use cardiac::*;

const VOWEL: i16 = 1;
const PAUSE: i16 = 8;

fn main() {
    let (mut after, mut imm, mut nvs) = (0, 0, 0);
    loop {
        let kind = inp();
        let s = inp();
        let wf = inp();
        out(after);
        out(imm);
        out(nvs);
        if kind == PAUSE || wf != 0 {
            // a pause, or the start of the word: what lies ahead of the segment before is in another word
            after = 0;
            imm = 0;
            nvs = 0;
        } else if kind == VOWEL {
            imm = s;
            nvs = s;
            after = 1;
        } else {
            imm = 0;
        }
    }
}
