//! period: f0 in Hz in, the pitch period out: P = (8000 + f0 / 2) / f0 samples rounded down, by taking f0 away as
//! often as it goes (front_ref.period). 8000 + f0 / 2 is more than a card holds, so it is kept as thousands and
//! units, a thousand borrowed when the units go below 0. Long division with `/` and `%` is 129 cells and doesn't fit
//! in one machine; split over three machines it would run 0.39 of the instructions (see the README), at the cost
//! of two more machines.
use cardiac::*;

fn main() {
    loop {
        let f0 = inp();
        let mut thousands = 8;
        let mut units = f0 / 2;
        let mut p = 0;
        while thousands > 0 || units >= f0 {
            units -= f0;
            if units < 0 {
                // 1000 is past a card (RCE0009), so it goes on as two 500s
                units += 500;
                units += 500;
                thousands -= 1;
            }
            p += 1;
        }
        out(p);
    }
}
