//! reduce: a step's A and a coefficient K (k = K / 1000) in, the five cards of a lattice machine's multiply
//! routine out (ref/voice_ref.py, `words`): the sign word, ADD t or SUB t (t is cell 86 in every lattice machine),
//! the jumps into the row of nine ADDs for k's second and first digits (JMP 99 - d, the card 899 - d), SFT 0L, and
//! the rounding half, 5 x 10^(L-1). k keeps two digits from its first nonzero one, L: L is 1 for |K| from 100 (the
//! second digit rounded, and 995 and up kept at 99), 2 from 10, and 3 below. In a step whose A is 0 the cards are
//! those of k = 0 whatever K is, four SFT 00 and a half of 0: every product is 0, so in a pause the lattice's state
//! drains away, and SFT 00 costs the lattice one instruction where JMP 99 costs two.
use cardiac::*;

const ADD_T: i16 = 286;
const SUB_T: i16 = 786;
const JMP_99: i16 = 899;
const SFT_00: i16 = 400;

fn main() {
    loop {
        let a = inp();
        let k = inp();
        if a <= 0 {
            out(SFT_00);
            out(SFT_00);
            out(SFT_00);
            out(SFT_00);
            out(0);
            continue;
        }
        let sign = if k < 0 { SUB_T } else { ADD_T };
        let m = k.abs();
        let (n, lead, half) = if m >= 100 {
            ((m.min(994) + 5) / 10, 1, 5)
        } else if m >= 10 {
            (m, 2, 50)
        } else {
            (10 * m, 3, 500)
        };
        out(sign);
        out(JMP_99 - n % 10);
        out(JMP_99 - n / 10);
        out(SFT_00 + lead);
        out(half);
    }
}
