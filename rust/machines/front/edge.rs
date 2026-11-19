//! edge: each segment's kind and frames, back's pvls and pnpk, and the ASP, VOICED and VBAR cards of
//! its row of the phoneme table, in; out (front_machines.f5_edge) cf, a stop's closure filter (its voice bar when it
//! is voiced and a vowel, sonorant or nasal came before it, else 0 for silence), and af, the aspirated filter for a
//! vowel's or sonorant's first frame right after P, T or K when it has more than one frame (else 0).
use cardiac::*;

const SONORANT: i16 = 2;
const NASAL: i16 = 3;
const STOP: i16 = 4;

fn main() {
    loop {
        let kind = inp();
        let n = inp();
        let pvls = inp();
        let pnpk = inp();
        let asp = inp();
        let voiced = inp();
        let vbar = inp();
        let (mut cf, mut af) = (0, 0);
        if kind == STOP && voiced != 0 && pnpk >= 1 && pnpk <= NASAL {
            cf = vbar;
        }
        if kind >= 1 && kind <= SONORANT && pvls != 0 && n > 1 {
            af = asp;
        }
        out(cf);
        out(af);
    }
}
