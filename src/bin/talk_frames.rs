//! talk-frames: frame cards in (a file, or standard input), the voice box on ten CARDIACs, raw 8 kHz signed 16-bit
//! little-endian samples out on standard output. With -v, each machine's instruction count on standard error.
//! With --values, the output values themselves, one a line, instead of samples.
use std::io::{Read, Write};

use cardiac_speech::net::Net;
use cardiac_speech::voice;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let verbose = args.iter().any(|a| a == "-v");
    let values = args.iter().any(|a| a == "--values");
    let file = args.iter().find(|a| !a.starts_with('-') || *a == "-");
    let mut text = String::new();
    match file.map(|s| s.as_str()) {
        None | Some("-") => {
            std::io::stdin().read_to_string(&mut text).expect("standard input");
        }
        Some(f) => text = std::fs::read_to_string(f).unwrap_or_else(|e| panic!("{f}: {e}")),
    }
    let cards = heartburn::tape::values(&text).expect("frame cards");
    let started = std::time::Instant::now();
    let mut net = Net::new();
    voice::wire(&mut net, "frames", "out");
    net.put("frames", &cards);
    let stdout = std::io::stdout();
    let mut w = std::io::BufWriter::new(stdout.lock());
    let mut pending: Vec<i32> = vec![];
    let mut samples = 0usize;
    loop {
        let moved = net.round(200_000);
        pending.extend(net.take("out"));
        let whole = pending.len() / 2 * 2;
        for pair in pending[..whole].chunks(2) {
            if values {
                writeln!(w, "{}\n{}", pair[0], pair[1]).unwrap();
            } else {
                let s = voice::sample(pair[0], pair[1]).unwrap_or_else(|| panic!("not a sample: {pair:?}"));
                w.write_all(&s.to_le_bytes()).unwrap();
            }
            samples += 1;
        }
        pending.drain(..whole);
        if !moved {
            break;
        }
    }
    w.flush().unwrap();
    if verbose {
        let secs = started.elapsed().as_secs_f64();
        let total: u64 = net.steps().iter().map(|(_, s)| s).sum();
        let speech = samples as f64 / 8000.0;
        for (n, s) in net.steps() {
            eprintln!("{n:>8} {s:>12}");
        }
        eprintln!("{samples} samples ({speech:.2} s of speech), {total} instructions ({:.0} a second of speech), {secs:.3} s: real-time factor {:.4}",
            total as f64 / speech, secs / speech);
    }
}
