//! talk: text in (the arguments, or standard input), speech out: raw 8 kHz signed 16-bit little-endian samples on
//! standard output, every step worked out by CARDIACs (65 of them, in three phases). The host deals and moves
//! cards: the text as character cards, the decks the machines read, the records put in the opposite order between
//! phases, and each output pair joined into a 16-bit sample.
//!
//!   --phonemes   print the phoneme cards (the text machines' output) instead, one a line
//!   --frames     print the frame cards (the front end's output) instead, one a line
//!   -v           each machine's instruction count, the totals and the real-time factor on standard error
use std::io::{Read, Write};
use std::time::Instant;

use cardiac_speech::{front, net::Net, text, voice};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let flag = |f: &str| args.iter().any(|a| a == f);
    let (verbose, phonemes, frames_only) = (flag("-v"), flag("--phonemes"), flag("--frames"));
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

    // phase 1: text to phonemes to segment records
    let mut net = Net::new();
    text::wire(&mut net, &decks, "chars", "tokens");
    if phonemes {
        net.put("chars", &text::text_cards(&input));
        net.run();
        for c in net.take("tokens") {
            println!("{c}");
        }
        return;
    }
    net.copy("tokens", &["tokens_f"]);
    front::segments(&mut net, &tables, "tokens_f", "r1");
    net.put("chars", &text::text_cards(&input));
    net.run();
    let r1 = net.take("r1");
    steps.extend(net.steps());
    // phase 2: what lies ahead, last first
    let mut net = Net::new();
    front::ahead(&mut net, &tables, &r1);
    net.run();
    let (a, b, c) = (net.take("A"), net.take("B"), net.take("C"));
    steps.extend(net.steps());
    // phase 3: frames, and the voice box, streaming
    let mut net = Net::new();
    front::frames(&mut net, &tables, &r1, &a, &b, &c, "frames");
    if frames_only {
        net.run();
        for c in net.take("frames") {
            println!("{c}");
        }
        return;
    }
    voice::wire(&mut net, "frames", "out");
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
        let (deck, read, out) = cardiac_speech::net::card_counts();
        eprintln!("cards: {deck} program cards loaded, {read} cards read by INPs, {out} values put out by OUTs");
    }
}
