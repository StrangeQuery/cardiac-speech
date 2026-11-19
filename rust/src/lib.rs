//! Text to speech on CARDIACs, the machines written in Rust (machines/) but for the five lattice machines, written by
//! hand (hand/). Each machine has one reader and one punch; the host only deals, copies, collates, merges in fixed
//! orders and fetches table records (`net`).
pub mod net;
pub mod voice;
