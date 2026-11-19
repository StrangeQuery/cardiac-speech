//! talk-phonemes: phoneme cards in (10 x code + stress, -1 a word boundary, -2 to -5 pauses, -9 the end; a file
//! or standard input), the front end on CARDIACs, frame cards out (one a line), for talk-frames. With -v, each
//! machine's instruction count on standard error.
use std::io::Read;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let verbose = args.iter().any(|a| a == "-v");
    let file = args.iter().find(|a| !a.starts_with('-') || *a == "-");
    let mut text = String::new();
    match file.map(|s| s.as_str()) {
        None | Some("-") => {
            std::io::stdin().read_to_string(&mut text).expect("standard input");
        }
        Some(f) => text = std::fs::read_to_string(f).unwrap_or_else(|e| panic!("{f}: {e}")),
    }
    let tokens = heartburn::tape::values(&text).expect("phoneme cards");
    let (frames, steps) = cardiac_speech::front::phonemes_to_frames(&tokens);
    for f in &frames {
        println!("{f}");
    }
    if verbose {
        let total: u64 = steps.iter().map(|(_, s)| s).sum();
        for (n, s) in &steps {
            eprintln!("{n:>8} {s:>10}");
        }
        eprintln!("{} machines, {total} instructions", steps.len());
    }
}
