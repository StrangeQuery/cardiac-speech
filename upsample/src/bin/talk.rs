//! talk: text in (the arguments, or standard input), speech out: raw 48 kHz signed 16-bit little-endian samples on
//! standard output, every step worked out by CARDIACs: the first version's machines to 8 kHz, then the upsampler.
//!
//!   --phonemes   print the phoneme cards (the text machines' output) instead, one a line
//!   --frames     print the frame cards (the front end's output) instead, one a line
//!   --8k         write the 8 kHz samples underneath instead (the output stage's, as the upsampler reads them)
//!   --filters    print each frame's filter as choose punches it instead, one a line (the high band's levels' keys)
//!   --no-hiband  write the 48 kHz samples without the high band
//!   -v           each machine's instruction count, the totals and the real-time factor on standard error
use std::io::Read;
use std::time::Instant;

use cardiac_speech::{front, net::Net, text};
use cardiac_speech_upsample::{report, speak, Rate};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let flag = |f: &str| args.iter().any(|a| a == f);
    let (verbose, phonemes, frames_only) = (flag("-v"), flag("--phonemes"), flag("--frames"));
    let rate = if flag("--8k") { Rate::Eight } else { Rate::Up };
    let (filters_only, hiband) = (flag("--filters"), !flag("--no-hiband"));
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

    // text to phonemes, and phonemes to segment records, as the first version's talk does
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
    let (frames, filters, more) = front::segments_to_frames_and_filters(&tables, &r1, true);
    steps.extend(more);
    if frames_only || filters_only {
        for c in if frames_only { &frames } else { &filters } {
            println!("{c}");
        }
        return;
    }
    // the voice box and the upsampler
    let stdout = std::io::stdout();
    let mut w = std::io::BufWriter::new(stdout.lock());
    let (samples, more) = speak(&frames, hiband.then_some(&filters[..]), rate, false, &mut w);
    steps.extend(more);
    if verbose {
        report(&steps, samples, rate, started.elapsed().as_secs_f64());
    }
}
