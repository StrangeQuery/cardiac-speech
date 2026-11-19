//! talk: text in (the arguments, or standard input), speech out: raw 8 kHz signed 16-bit little-endian samples on
//! standard output, every step worked out by CARDIACs, in phases. The host deals and moves cards: the text as its
//! characters' records of the ASCII table, the decks and table records the machines read, the records put in the
//! opposite order between phases, and each output pair joined into a 16-bit sample.
//!
//!   --phonemes   print the phoneme cards (the text machines' output) instead, one a line
//!   --frames     print the frame cards (the front end's output) instead, one a line
//!   -v           each machine's instruction count, the totals and the real-time factor on standard error
//!   --all-rust   the voice box's six hand-written machines replaced by Rust ones, to compare
use std::io::{Read, Write};
use std::time::Instant;

use cardiac_speech_rust::{front, net::Net, text, voice};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let flag = |f: &str| args.iter().any(|a| a == f);
    let (verbose, phonemes, frames_only, all_rust) = (flag("-v"), flag("--phonemes"), flag("--frames"), flag("--all-rust"));
    let words: Vec<&String> = args.iter().filter(|a| !a.starts_with('-')).collect();
    let mut input = String::new();
    if words.is_empty() {
        std::io::stdin().read_to_string(&mut input).expect("standard input");
    } else {
        input = words.iter().map(|s| s.as_str()).collect::<Vec<_>>().join(" ");
    }
    let started = Instant::now();
    let decks = text::Decks::load();
    let tables = front::Tables::load();
    let mut steps: Vec<(String, u64)> = vec![];

    // text to phonemes, and phonemes to segment records
    let mut net = Net::new();
    text::wire(&mut net, &decks, "chars", "tokens");
    if phonemes {
        text::deal_text(&mut net, "chars", &input);
        net.run();
        for c in net.take("tokens") {
            println!("{c}");
        }
        return;
    }
    net.copy("tokens", &["tokens_f"]);
    front::segments(&mut net, &tables, "tokens_f", "r1");
    text::deal_text(&mut net, "chars", &input);
    net.run();
    let r1 = net.take("r1");
    steps.extend(net.steps());
    // the rest of the front end, phase by phase
    let (frames, more) = front::segments_to_frames(&tables, &r1);
    steps.extend(more);
    if frames_only {
        for c in &frames {
            println!("{c}");
        }
        return;
    }
    // the voice box
    let mut net = Net::new();
    voice::wire(&mut net, "frames", "frames2", "out", all_rust);
    voice::deal_frames(&mut net, &frames, "frames", "frames2");
    let stdout = std::io::stdout();
    let mut w = std::io::BufWriter::new(stdout.lock());
    let mut pending: Vec<i32> = vec![];
    let mut samples = 0usize;
    loop {
        let moved = net.round(200_000);
        pending.extend(net.take("out"));
        let whole = pending.len() / 2 * 2;
        for pair in pending[..whole].chunks(2) {
            let s = voice::sample(pair[0], pair[1]).unwrap_or_else(|| panic!("not a sample: {pair:?}"));
            if w.write_all(&s.to_le_bytes()).is_err() {
                return;
            }
            samples += 1;
        }
        pending.drain(..whole);
        if !moved {
            break;
        }
    }
    w.flush().ok();
    steps.extend(net.steps());
    if verbose {
        let secs = started.elapsed().as_secs_f64();
        let speech = samples as f64 / 8000.0;
        let total: u64 = steps.iter().map(|(_, s)| s).sum();
        for (n, s) in &steps {
            eprintln!("{n:>8} {s:>12}");
        }
        eprintln!(
            "{} machines; {samples} samples ({speech:.2} s of speech); {total} instructions, {:.0} a second of speech; {secs:.3} s: real-time factor {:.4}",
            steps.len(), total as f64 / speech, secs / speech
        );
        let (deck, read, out) = cardiac_speech_rust::net::card_counts();
        eprintln!("cards: {deck} program cards loaded, {read} cards read by INPs, {out} values put out by OUTs");
    }
}
