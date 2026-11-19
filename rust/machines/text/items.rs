//! items: names's cards in; out a record of 17 cards for each run of cards 0 or more and the card below 0 that ends
//! it: that end card, how many cards the run has (n), and the run with an edge (28) on each side, padded with 0 to
//! 15 cards (a word's letters and -10, a spelled letter's phonemes and -1 or -20, a punctuation card with no run).
//! With every record the same size, the host can deal each one beside a deck or a table record. A run has at most
//! 13 cards; more are dropped.
use cardiac::*;

const EDGE: i16 = 28;

fn main() {
    let mut run = [0i16; 15];
    run[0] = EDGE;
    run[1] = EDGE;
    let mut n = 0;
    loop {
        let c = inp();
        if c >= 0 {
            if n < 13 {
                n += 1;
                run[n] = c;
                run[n + 1] = EDGE;
            }
            continue;
        }
        out(c);
        out(n as i16);
        for x in &run {
            out(*x);
        }
        for k in 2..n + 2 {
            run[k] = 0;
        }
        run[1] = EDGE;
        n = 0;
    }
}
