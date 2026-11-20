//! talk-frames: frame cards in (a file, or standard input), the voice box and the upsampler on CARDIACs, raw 48 kHz
//! signed 16-bit little-endian samples out on standard output. With --8k, the 8 kHz samples underneath instead; with
//! --values, the samples' pairs of values (thousands and units), one value a line; with -v, each machine's
//! instruction count on standard error.
use std::io::Read;

use cardiac_speech::net::cards;
use cardiac_speech_upsample::{report, speak, Rate};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let flag = |f: &str| args.iter().any(|a| a == f);
    let rate = if flag("--8k") { Rate::Eight } else { Rate::Up };
    let file = args.iter().find(|a| !a.starts_with('-') || *a == "-");
    let mut text = String::new();
    match file.map(|s| s.as_str()) {
        None | Some("-") => {
            std::io::stdin().read_to_string(&mut text).expect("standard input");
        }
        Some(f) => text = std::fs::read_to_string(f).unwrap_or_else(|e| panic!("{f}: {e}")),
    }
    let deck = cards(&text);
    let started = std::time::Instant::now();
    let stdout = std::io::stdout();
    let mut w = std::io::BufWriter::new(stdout.lock());
    let (samples, steps) = speak(&deck, rate, flag("--values"), &mut w);
    if flag("-v") {
        report(&steps, samples, rate, started.elapsed().as_secs_f64());
    }
}
