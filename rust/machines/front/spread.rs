//! spread: a segment's cards, again for each of its frames. First a card saying how many cards a segment has
//! besides its frames n, at most 10; then for each segment n and those cards. Out, for each of its n frames, the
//! cards again, so that the machines that work frame by frame read each frame's segment beside it.
use cardiac::*;

fn main() {
    let width = inp();
    let mut cards = [0i16; 10];
    loop {
        let n = inp();
        for i in 0..width as usize {
            cards[i] = inp();
        }
        for _ in 0..n {
            for i in 0..width as usize {
                out(cards[i]);
            }
        }
    }
}
