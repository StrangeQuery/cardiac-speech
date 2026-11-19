//! fill: run on the segments last first. Each segment's three cards from sum in (send, L and the tail's start); its
//! sentence's summary out, taken from the segment that ends the sentence, which comes first when they run last
//! first (front_machines.f4_sum): L, the tail's start, M, the tail's length (L less its start, or 1 with no tail),
//! and the end, 1 for a statement and 2 for a question.
use cardiac::*;

fn main() {
    let (mut l, mut tail, mut m, mut end) = (0, 0, 0, 0);
    loop {
        let send = inp();
        let sl = inp();
        let st = inp();
        if send > 0 {
            (l, tail, m, end) = (sl, st, 1, 1);
            if st >= 0 {
                m = sl - st;
            }
            if send == 2 {
                end = 2;
            }
        }
        out(l);
        out(tail);
        out(m);
        out(end);
    }
}
