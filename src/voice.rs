//! The voice box: frame cards in, samples out, on ten CARDIACs.
//!
//! interp -> steps -> excite -> L1 -> L2 -> L3 -> L4 -> L5 -> output
//!                 -> reduce (dealt ten cards a step to each of L1..L5)
//!
//! A frame is 13 cards: V, P, A, K10..K1; a card below zero ends the frames. Each sample comes out as two values,
//! the thousands and the units of the sample (as lubdub's decoder outputs them).
use crate::net::Net;

pub const INTERP: &str = include_str!("../voice/interp.cq");
pub const STEPS: &str = include_str!("../voice/steps.cq");
pub const REDUCE: &str = include_str!("../voice/reduce.cq");
pub const EXCITE: &str = include_str!("../voice/excite.cq");
pub const LATTICE_TOP: &str = include_str!("../voice/lattice_top.cq");
pub const LATTICE: &str = include_str!("../voice/lattice.cq");
pub const LATTICE_BOTTOM: &str = include_str!("../voice/lattice_bottom.cq");
pub const OUTPUT: &str = include_str!("../voice/output.cq");

/// Wire the voice box into `net`: it reads frame cards from pile `frames` and puts the output values on `out`. Its
/// own piles are named v_...
pub fn wire(net: &mut Net, frames: &str, out: &str) {
    net.add("interp", INTERP, &[("3", frames), ("6", frames), ("13", frames), ("27", frames), ("*", "v_iself")],
        &[("7", "v_iself"), ("35", "v_iself"), ("*", "v_tosteps")]);
    net.add("steps", STEPS, &[("3", "v_tosteps"), ("7", "v_tosteps"), ("*", "v_sself")],
        &[("18", "v_exc"), ("20", "v_exc"), ("28", "v_exc"), ("38", "v_kin"), ("*", "v_sself")]);
    net.add("reduce", REDUCE, &[("*", "v_kin")], &[("*", "v_coef")]);
    net.deal("v_coef", 10, &["v_c1", "v_c2", "v_c3", "v_c4", "v_c5"]);
    net.add("excite", EXCITE, &[("*", "v_exc")], &[("*", "v_e")]);
    net.add("L1", LATTICE_TOP, &[("go", "v_e"), ("getb", "v_b8"), ("*", "v_c1")], &[("*", "v_f9")]);
    net.add("L2", LATTICE, &[("go", "v_f9"), ("getb", "v_b6"), ("*", "v_c2")], &[("loop", "v_b8"), ("*", "v_f7")]);
    net.add("L3", LATTICE, &[("go", "v_f7"), ("getb", "v_b4"), ("*", "v_c3")], &[("loop", "v_b6"), ("*", "v_f5")]);
    net.add("L4", LATTICE, &[("go", "v_f5"), ("getb", "v_b2"), ("*", "v_c4")], &[("loop", "v_b4"), ("*", "v_f3")]);
    net.add("L5", LATTICE_BOTTOM, &[("go", "v_f3"), ("*", "v_c5")], &[("loop", "v_b2"), ("*", "v_f0")]);
    net.add("output", OUTPUT, &[("*", "v_f0")], &[("*", out)]);
}

/// A sample from its two values, the thousands and the units; none if they aren't a 16-bit sample.
pub fn sample(thousands: i32, units: i32) -> Option<i16> {
    if !(0..=999).contains(&units) {
        return None;
    }
    i16::try_from(thousands * 1000 + units).ok()
}
