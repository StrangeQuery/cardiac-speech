//! yd: each 8 kHz sample in as the output stage punches it, its thousands and then its units from 0 to 999; the
//! sample over 20 out, which is yd, the de-emphasis output, again. The sample is 20 yd, so the units are a multiple
//! of 20, and yd = 50 thousands + units / 20, exactly; units / 20 is 5 units / 100.
use cardiac::*;

fn main() {
    loop {
        let th = inp();
        let u = inp();
        out(50 * th + 5 * u / 100);
    }
}
