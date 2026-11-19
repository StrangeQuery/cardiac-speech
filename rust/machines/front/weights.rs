//! weights: a frame's j, k and n (from framer) in; the glide weights at its segment's two ends out, wl and wr: the
//! share of the segment's own filter in its first and last frames, in tenths (front_ref.glide_weight; 0 for none).
//! A segment of four frames or more glides over two frames at each end (3 and then 9), of three over one (3), and
//! of two over one, its first (5).
use cardiac::*;

/// The weight for the frame k from one end of a segment of n frames.
#[inline(never)]
fn weight(k: i16, n: i16) -> i16 {
    let mut w = 0;
    if k < 1 {
        if n > 2 {
            w = 3;
        } else if n > 1 {
            w = 5;
        }
    } else if k < 2 && n > 3 {
        w = 9;
    }
    w
}

fn main() {
    loop {
        let j = inp();
        let k = inp();
        let n = inp();
        out(weight(j, n));
        out(weight(k, n));
    }
}
