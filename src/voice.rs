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

/// Wire the voice box into `net`: it reads frame cards from pile `frames` and puts the output values on `out`.
pub fn wire(net: &mut Net, frames: &str, out: &str) {
    net.add("interp", INTERP, &[("3", frames), ("6", frames), ("13", frames), ("27", frames), ("*", "iself")],
        &[("7", "iself"), ("35", "iself"), ("*", "tosteps")]);
    net.add("steps", STEPS, &[("3", "tosteps"), ("7", "tosteps"), ("*", "sself")],
        &[("18", "exc"), ("20", "exc"), ("28", "exc"), ("38", "kin"), ("*", "sself")]);
    net.add("reduce", REDUCE, &[("*", "kin")], &[("*", "coef")]);
    net.deal("coef", 10, &["c1", "c2", "c3", "c4", "c5"]);
    net.add("excite", EXCITE, &[("*", "exc")], &[("*", "e")]);
    net.add("L1", LATTICE_TOP, &[("go", "e"), ("getb", "b8"), ("*", "c1")], &[("*", "f9")]);
    net.add("L2", LATTICE, &[("go", "f9"), ("getb", "b6"), ("*", "c2")], &[("loop", "b8"), ("*", "f7")]);
    net.add("L3", LATTICE, &[("go", "f7"), ("getb", "b4"), ("*", "c3")], &[("loop", "b6"), ("*", "f5")]);
    net.add("L4", LATTICE, &[("go", "f5"), ("getb", "b2"), ("*", "c4")], &[("loop", "b4"), ("*", "f3")]);
    net.add("L5", LATTICE_BOTTOM, &[("go", "f3"), ("*", "c5")], &[("loop", "b2"), ("*", "f0")]);
    net.add("output", OUTPUT, &[("*", "f0")], &[("*", out)]);
}

/// A sample from its two values, the thousands and the units; none if they aren't a 16-bit sample.
pub fn sample(thousands: i32, units: i32) -> Option<i16> {
    if !(0..=999).contains(&units) {
        return None;
    }
    i16::try_from(thousands * 1000 + units).ok()
}
