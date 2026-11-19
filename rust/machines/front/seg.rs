//! seg: phoneme cards in, a record of five cards a segment out: pc (the phoneme's code, 0 for a pause), s (its
//! stress), wf (it starts a word), pms (a pause's length in ms) and send (it ends a sentence: 1 a statement, 2 a
//! question, 3 the end of everything). The first part of front_ref.p1: the host puts each record beside six cards
//! of the phoneme's row of the table (kind, inh, mn, cls9, liq, vls; row 0 is a pause's) to make the segment's
//! record of 11.
//!
//! A phoneme card is 10 x code + stress; -1 is a word boundary, -2 to -5 a pause (, . ? !) and -9 the end. A pause
//! of 50 ms comes first and one of 150 ms last.
use cardiac::*;

/// A pause's record: pc 0, stress 0.
#[inline(never)]
fn pause(wf: i16, pms: i16, send: i16) {
    out(0);
    out(0);
    out(wf);
    out(pms);
    out(send);
}

fn main() {
    pause(0, 50, 0);
    let mut wf = 1;
    loop {
        let t = inp();
        if t >= 0 {
            // a phoneme: its code and stress
            out(t / 10);
            out(t % 10);
            out(wf);
            out(0);
            out(0);
            wf = 0;
        } else if t > -2 {
            // a word boundary
            wf = 1;
        } else if t < -8 {
            break;
        } else {
            // a comma pauses 300 ms and goes on; . ! and ? pause 600 ms and end a sentence, ? as a question
            if t > -3 {
                pause(wf, 300, 0);
            } else {
                pause(wf, 600, if t == -4 { 2 } else { 1 });
            }
            wf = 1;
        }
    }
    pause(wf, 150, 3);
}
