//! loud: first the LOUD card of AX's row of the phoneme table; then for each segment next's adjv, back's prevv, and
//! the LOUD cards of the rows of adjv, prevv and next's nextv. Out the loudness a sonorant's frames take from the
//! vowel next to it (front_ref.frames): for a voiced frame that of the vowel after it in its word, else the one
//! before, else AX's; for the breathy first frame after P, T or K, that of the next vowel.
use cardiac::*;

fn main() {
    let ax_loud = inp();
    loop {
        let adjv = inp();
        let prevv = inp();
        let adjv_loud = inp();
        let prevv_loud = inp();
        let nextv_loud = inp();
        out(if adjv != 0 {
            adjv_loud
        } else if prevv != 0 {
            prevv_loud
        } else {
            ax_loud
        });
        out(nextv_loud);
    }
}
