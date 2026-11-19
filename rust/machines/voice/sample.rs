//! sample: yd as tens t and units u in (from deemph); the sample 20 yd out as two values, its thousands and then
//! its units from 0 to 999, as the host joins them (ref/voice_ref.py, `voice`). 20 yd = 200 t + 20 u: the
//! thousands are floor(2 t / 10), and the units 100 (2 t mod 10) + 20 u, with a thousand borrowed when they come
//! out below 0.
use cardiac::*;

fn main() {
    loop {
        let t = inp();
        let u = inp();
        let t2 = t + t;
        let mut thousands = t2 / 10;
        let mut rem = t2 % 10;
        if rem < 0 {
            thousands -= 1;
            rem += 10;
        }
        let mut units = 100 * rem + 20 * u;
        if units < 0 {
            thousands -= 1;
            units += 500;
            units += 500;
        }
        out(thousands);
        out(units);
    }
}
