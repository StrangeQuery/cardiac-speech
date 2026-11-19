//! next: run on the segments last first. First the ASP card of AX's row of the phoneme table; then for each segment
//! its pc and kind and the TS, TE and ASP cards of its row. Out: the next segment that isn't a pause (nxtpc), the
//! segment after if it is a vowel (adjv), the next vowel anywhere ahead (nextv, AX if none), the segment's start
//! and end filters (ts, te) and the start filter of the segment after (nts, 0 for a pause) (front_machines.f2c,
//! front_ref.p2). HH's filter is the aspirated form of the vowel after it, or of AX.
use cardiac::*;

const VOWEL: i16 = 1;
const ASPIRATE: i16 = 7;
const PAUSE: i16 = 8;
const AX: i16 = 18;

fn main() {
    let ax_asp = inp();
    let (mut nxtpc, mut adjv, mut nts, mut next_vowel) = (0, 0, 0, false);
    let mut nextv = AX;
    let mut next_asp = 0; // the ASP card of nxtpc's row
    loop {
        let pc = inp();
        let kind = inp();
        let mut ts = inp();
        let mut te = inp();
        let asp = inp();
        out(nxtpc);
        out(adjv);
        out(nextv);
        if kind == PAUSE {
            out(0);
            out(0);
            out(nts);
            adjv = 0;
            nts = 0;
            continue;
        }
        if kind == ASPIRATE {
            ts = if next_vowel { next_asp } else { ax_asp };
            te = ts;
        }
        out(ts);
        out(te);
        out(nts);
        nxtpc = pc;
        nts = ts;
        next_asp = asp;
        next_vowel = kind == VOWEL;
        adjv = 0;
        if next_vowel {
            adjv = pc;
            nextv = pc;
        }
    }
}
