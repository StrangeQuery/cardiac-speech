//! back: each segment's pc, kind and vls, and its end filter te, in; out what came before it: the end filter of the
//! segment before (pte, 0 after a pause), the segment before that isn't a pause if it is a vowel (prevv), whether
//! the segment before is P, T or K (pvls), and the kind of the segment before that isn't a pause (pnpk)
//! (front_machines.f3_back).
use cardiac::*;

const VOWEL: i16 = 1;
const PAUSE: i16 = 8;

fn main() {
    let (mut pte, mut pvls, mut pnpk, mut pnpc) = (0, 0, 0, 0);
    loop {
        let pc = inp();
        let kind = inp();
        let vls = inp();
        let te = inp();
        out(pte);
        out(if pnpk == VOWEL { pnpc } else { 0 });
        out(pvls);
        out(pnpk);
        if kind == PAUSE {
            pte = 0;
            pvls = 0;
        } else {
            pte = te;
            pvls = vls;
            pnpk = kind;
            pnpc = pc;
        }
    }
}
