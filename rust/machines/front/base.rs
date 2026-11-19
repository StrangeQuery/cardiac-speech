//! base: each segment's kind, inh, mn, pms and vls and its stress in; out x and base, so that its duration is
//! x pr / 100 + base (front_machines.f3_base). An unstressed segment's minimum duration is halved (Klatt's rule 7),
//! a stressed vowel or sonorant right after P, T or K gets 25 ms more (rule 11), and a pause is its own length.
use cardiac::*;

const SONORANT: i16 = 2;
const PAUSE: i16 = 8;

fn main() {
    let mut pvls = 0;
    loop {
        let kind = inp();
        let inh = inp();
        let mut mn = inp();
        let pms = inp();
        let vls = inp();
        let s = inp();
        if kind == PAUSE {
            out(0);
            out(pms);
            pvls = 0;
            continue;
        }
        if s == 0 {
            mn = 5 * mn / 10;
        }
        let mut base = mn;
        if s >= 1 && kind <= SONORANT && pvls != 0 {
            base += 25;
        }
        out(inh - mn);
        out(base);
        pvls = vls;
    }
}
