//! interp: each frame beside the next one in, each value of the frame and its step to the next frame's out
//! (closedloop.interp_steps, as ref/voice_ref.py uses it). A frame is 13 cards: V (1 voiced, 0 not), P (the pitch
//! period in samples), A (the excitation's amplitude) and K10 to K1 (each reflection coefficient times 1000). The
//! host deals the frames twice over, the second time from the second frame on, and merges the two a card from each
//! at a time, so that each card of a frame comes with the same card of the next frame. The frames end with a record
//! whose V is -1.
//!
//! For each frame it punches V, then for P, A and each K the value and its step, (next - this) / 10 truncated
//! toward zero, or 0 when the next frame's V differs (no glide across a change of voicing, and none after the last
//! frame).
use cardiac::*;

/// (x - c) / 10, truncated toward zero. x - c can pass a card, so it is taken as tens and units: the units, with
/// 20 added to keep them positive, are carried into the tens, which is the quotient rounded down; a negative
/// quotient with units left over is then one more.
fn step(c: i16, x: i16) -> i16 {
    let w = x % 10 - c % 10 + 20;
    let mut d = x / 10 - c / 10 - 2 + w / 10;
    if d < 0 && w % 10 != 0 {
        d += 1;
    }
    d
}

fn main() {
    loop {
        let v = inp();
        let next_v = inp();
        let glide = next_v == v;
        out(v);
        for _ in 0..12 {
            let this = inp();
            let next = inp();
            out(this);
            out(if glide { step(this, next) } else { 0 });
        }
    }
}
