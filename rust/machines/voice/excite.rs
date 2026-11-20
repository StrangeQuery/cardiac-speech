//! excite: each step's V, P and A in, its 20 excitation values out, one a sample (ref/voice_ref.py, `excitation`).
//!
//! Voiced: a pulse of height A every P samples (the count goes on across steps), 0 between, through the one-pole
//! low-pass e = pulse + 0.5 e, truncated toward zero. Not voiced: +A or -A by the decimal random numbers
//! x = 21 x + 7 mod 1000 from 123, -A when x is below 500.
use cardiac::*;

fn main() {
    let mut count: i16 = 0;
    let mut x: i16 = 123;
    let mut e: i16 = 0;
    loop {
        let v = inp();
        let p = inp();
        let a = inp();
        for _ in 0..20 {
            let sample = if v > 0 {
                count += 1;
                let mut pulse = 0;
                if count >= p {
                    count = 0;
                    pulse = a;
                }
                // 0.5 e as 5 e / 10, by tens and units since 5 e can pass a card
                e = pulse + 5 * (e / 10) + 5 * (e % 10) / 10;
                e
            } else {
                // 21 x + 7 mod 1000: 20 x mod 1000 is 20 (x mod 50), and 1000 comes off a sum that reaches it
                let mut s = x % 100;
                if s >= 50 {
                    s -= 50;
                }
                x = x - 993 + 20 * s;
                if x < 0 {
                    // 1000 is past a card (RCE0009), so it goes on as two 500s
                    x += 500;
                    x += 500;
                }
                if x < 500 {
                    -a
                } else {
                    a
                }
            };
            out(sample);
        }
    }
}
