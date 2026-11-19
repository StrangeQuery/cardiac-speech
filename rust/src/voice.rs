//! The voice box: frame cards in, samples out, on 13 CARDIACs.
//!
//! interp -> steps -> excite -> L1 -> L2 -> L3 -> L4 -> L5 -> deemph -> sample
//!        -> ksteps -> reduce (dealt ten cards a step to each of L1..L5)
//!
//! A frame is 13 cards: V, P, A, K10..K1; the frames end with a card below zero. Each sample comes out as two
//! values, the thousands and the units of the sample (as lubdub's decoder outputs them).
//!
//! What the host does, under the one-reader rule:
//! - interp reads the frames twice over, merged a card at a time: the frames, and the frames again from the
//!   second one on, so that each card of a frame comes beside the same card of the next frame. The host deals
//!   twelve blank cards after the end card, so that the end is a whole record.
//! - interp punches a record of 25 cards a frame; the host collates its first five (V, P and A with their steps)
//!   for steps and its last 22 (A and the Ks with their steps) for ksteps.
//! - reduce's cards are dealt ten at a time to L1, L2, L3, L4 and L5 in turn: two coefficients a machine a step.
//! - each lattice machine's deck is merged: its ten coefficient cards, then twenty times one card from the machine
//!   above (the excitation, for L1) and one from the machine below (none for L5).
//! - L2 to L5 punch two cards a sample, b for the machine above and then f for the one below, dealt a card at a time
//!   to the two.
use crate::net::{Net, Program};

macro_rules! decks {
    ($($name:ident = $file:literal),* $(,)?) => {
        $(pub const $name: &str = include_str!(concat!("../machines/voice/", $file, ".cqb"));)*
    };
}

decks! {
    INTERP = "interp", STEPS = "steps", KSTEPS = "ksteps", REDUCE = "reduce", EXCITE = "excite",
    DEEMPH = "deemph", SAMPLE = "sample",
}
pub const LATTICE_TOP: &str = include_str!("../hand/lattice_top.cq");
pub const LATTICE: &str = include_str!("../hand/lattice.cq");
pub const LATTICE_BOTTOM: &str = include_str!("../hand/lattice_bottom.cq");

/// Frame cards: V, P, A and K10 to K1 a frame.
pub const FRAME: usize = 13;

/// Wire the voice box into `net`: it reads frame cards from the piles `frames` (the deck) and `frames2` (the deck
/// from its second frame on), and puts the output values on `out`. Its own piles are named v_...
pub fn wire(net: &mut Net, frames: &str, frames2: &str, out: &str) {
    net.merge("v_pairs", &[(frames, 1), (frames2, 1)], &[]);
    net.add("interp", Program::Deck(INTERP), "v_pairs", "v_int");
    net.copy("v_int", &["v_int_p", "v_int_k"]);
    let all: Vec<usize> = (0..25).collect();
    net.collate("v_steps", &[("v_int_p", 25, &all[..5])]);
    net.collate("v_ksteps", &[("v_int_k", 25, &all[3..])]);
    net.add("steps", Program::Deck(STEPS), "v_steps", "v_exc");
    net.add("ksteps", Program::Deck(KSTEPS), "v_ksteps", "v_kin");
    net.add("reduce", Program::Deck(REDUCE), "v_kin", "v_coef");
    net.deal("v_coef", 10, &["v_c1", "v_c2", "v_c3", "v_c4", "v_c5"]);
    net.add("excite", Program::Deck(EXCITE), "v_exc", "v_e");
    let lattice = |net: &mut Net, name: &str, listing: &str, coef: &str, above: &str, below: Option<&str>, input: &str| {
        let mut pattern = vec![(coef, 10)];
        for _ in 0..20 {
            pattern.push((above, 1));
            if let Some(b) = below {
                pattern.push((b, 1));
            }
        }
        net.merge(input, &pattern, &[]);
        net.add(name, Program::Listing(listing), input, &format!("{input}_out"));
    };
    lattice(net, "L1", LATTICE_TOP, "v_c1", "v_e", Some("v_b8"), "v_l1");
    net.copy("v_l1_out", &["v_f9"]);
    lattice(net, "L2", LATTICE, "v_c2", "v_f9", Some("v_b6"), "v_l2");
    net.deal("v_l2_out", 1, &["v_b8", "v_f7"]);
    lattice(net, "L3", LATTICE, "v_c3", "v_f7", Some("v_b4"), "v_l3");
    net.deal("v_l3_out", 1, &["v_b6", "v_f5"]);
    lattice(net, "L4", LATTICE, "v_c4", "v_f5", Some("v_b2"), "v_l4");
    net.deal("v_l4_out", 1, &["v_b4", "v_f3"]);
    lattice(net, "L5", LATTICE_BOTTOM, "v_c5", "v_f3", None, "v_l5");
    net.deal("v_l5_out", 1, &["v_b2", "v_f0"]);
    net.add("deemph", Program::Deck(DEEMPH), "v_f0", "v_yd");
    net.add("sample", Program::Deck(SAMPLE), "v_yd", out);
}

/// Deal a deck of frame cards (ending with a card below zero) to the voice box's two frame piles: the deck with
/// twelve blank cards after its end card, and the same from the second frame on.
pub fn deal_frames(net: &mut Net, deck: &[i32], frames: &str, frames2: &str) {
    let mut whole = deck.to_vec();
    whole.extend([0; FRAME - 1]);
    net.put(frames, &whole);
    net.put(frames2, &whole[FRAME.min(whole.len())..]);
}

/// A sample from its two values, the thousands and the units; none if they aren't a 16-bit sample.
pub fn sample(thousands: i32, units: i32) -> Option<i16> {
    if !(0..=999).contains(&units) {
        return None;
    }
    i16::try_from(thousands * 1000 + units).ok()
}
