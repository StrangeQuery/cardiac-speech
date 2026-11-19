//! period: f0 in Hz in, the pitch period out: P = (8000 + f0 / 2) / f0 samples rounded down, by taking f0 away as
//! often as it goes (front_ref.period). 8000 + f0 / 2 is more than a card holds, so it is kept as thousands and
//! units, a thousand borrowed when the units go below 0.
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
                units += 500;
                units += 500;
                thousands -= 1;
            }
            p += 1;
        }
        out(p);
    }
}
