//! gnorm: a frame's gn and w, and the record of the glide table for the filter go (three cards for each filter gn,
//! one for each glide weight 3, 5 and 9), in; the mode and factor for mulx5 out (front_machines.f8_gnorm): with no
//! glide (w 10) mode 0, else mode 4 and the card for gn and w, the factor in percent that brings the glided filter's
//! power back to the filter's own.
use cardiac::*;

/// The glide table's record for a filter: three cards for each of the filters.
const RECORD: i16 = 3 * 97;

fn main() {
    loop {
        let gn = inp();
        let w = inp();
        if w == 10 {
            skip_cards(RECORD);
            out(0);
            out(0);
            continue;
        }
        let at = 3 * gn + if w == 3 { 0 } else if w == 5 { 1 } else { 2 };
        skip_cards(at);
        let factor = inp();
        skip_cards(RECORD - at - 1);
        out(4);
        out(factor);
    }
}
