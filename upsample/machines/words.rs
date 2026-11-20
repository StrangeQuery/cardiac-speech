//! words: digits' cards in; the cards of fir's multiply routine out, five a tap, as reduce makes them for a lattice
//! coefficient (fir reads them straight into its routine):
//!
//! - the sign word, ADD t or SUB t, which puts the sample or less the sample into the row's cell, and leaves it in
//!   the accumulator too;
//! - for d3, CLA z when it is 0, nothing (SFT 00) when it is 1, and otherwise a jump into the row of ADDs for d3 - 1
//!   adds, since the accumulator holds the sample once already;
//! - for d2 and then d1, nothing when the digit is 0, and otherwise a jump into the row for d adds (JMP 99 - d);
//! - a jump to the next tap, or after the phase's last tap to the routine that puts the sum out: for stage 1 as one
//!   card, rounded to units, and for stage 2 twice the sum, as thousands and units.
//!
//! A tap marked 2 is the 16 kHz sample itself, a phase of its own: ADD t, then three SFT 10, ten times the sample, in
//! tenths, whatever its digits.
use cardiac::*;

// cells of fir (upsample/hand/fir.cq): the loop that reads a tap, the two ways of putting a sum out, and z
const TAP: i16 = 3;
const ONE: i16 = 23;
const PAIR: i16 = 38;
const Z: i16 = 59;

const NOTHING: i16 = 400;
const JMP: i16 = 800;

fn main() {
    let emit = JMP + if inp() < 2 { ONE } else { PAIR };
    loop {
        out(inp());
        let d1 = inp();
        let d2 = inp();
        let d3 = inp();
        let last = inp();
        if last > 1 {
            out(410);
            out(410);
            out(410);
        } else {
            out(if d3 < 1 {
                100 + Z
            } else if d3 < 2 {
                NOTHING
            } else {
                JMP + 100 - d3
            });
            out(if d2 < 1 { NOTHING } else { JMP + 99 - d2 });
            out(if d1 < 1 { NOTHING } else { JMP + 99 - d1 });
        }
        out(if last > 0 { emit } else { JMP + TAP });
    }
}
