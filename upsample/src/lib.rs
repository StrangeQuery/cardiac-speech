//! Text to speech on CARDIACs at 48 kHz. The first version's machines (the crate in the folder above, which this one
//! uses as it is) make the speech at 8 kHz, and then five more CARDIACs upsample it six times:
//!
//!   output -> yd -> fir1 (8 to 16 kHz) -> fir2 (16 to 48 kHz) -> the samples
//!   the tables -> digits -> words -> a deck of cards for fir1, and another for fir2
//!
//! yd and the two table machines are written in Rust (machines/), fir by hand (hand/fir.cq); fir1 and fir2 run the
//! same listing, with different decks. What the host does is in `wire`.
use std::rc::Rc;

use cardiac_speech::net::{cards, Net, Program};

pub const YD: &str = include_str!("../machines/yd.cqb");
pub const DIGITS: &str = include_str!("../machines/digits.cqb");
pub const WORDS: &str = include_str!("../machines/words.cqb");
pub const FIR: &str = include_str!("../hand/fir.cq");
pub const FIR1: &str = include_str!("../tables/fir1.cards");
pub const FIR2: &str = include_str!("../tables/fir2.cards");

/// Stage 1's phases, 8 to 16 kHz: for each phase, the age of the 8 kHz sample each of its taps reads (0 the newest).
/// The 159-tap filter's even taps are phase 0, its odd ones phase 1.
pub fn stage1() -> Vec<Vec<usize>> {
    vec![(0..80).collect(), (0..79).collect()]
}

/// Stage 2's phases, 16 to 48 kHz: the 19-tap filter's taps 1, 4, ... 16, then 2, 5, ... 17, and then its centre
/// alone, which is the 16 kHz sample two back. A 16 kHz sample m makes the 48 kHz samples 3 m + 1, 3 m + 2 and
/// 3 m + 3, so that each round of fir2's deck starts with the newest sample, as the merge needs (otherwise, after the
/// last sample, the merge would go on into a round it can't finish). The 48 kHz sample 0, which would be the 16 kHz
/// sample three before the first, is left out.
pub fn stage2() -> Vec<Vec<usize>> {
    vec![(0..6).collect(), (0..6).collect(), vec![2]]
}

/// The cards of fir's routine for a table: the table through digits and words, on two CARDIACs of their own,
/// before the speech starts. Returns the cards and the two machines' instruction counts.
pub fn routine(name: &str, table: &str) -> (Vec<i32>, Vec<(String, u64)>) {
    let mut net = Net::new();
    net.add(&format!("digits{name}"), Program::Deck(DIGITS), "table", "digits");
    net.add(&format!("words{name}"), Program::Deck(WORDS), "digits", "words");
    net.put("table", &cards(table));
    net.run();
    (net.take("words"), net.steps())
}

/// A stage's deck for fir: for each tap of each phase in turn, the sample it reads and its five cards of the routine
/// (the routine's cards dealt again each time round). Each tap reads its own copy of the samples, which starts with
/// as many blank cards as the age it reads, as a delay line starts empty.
fn window(net: &mut Net, samples: &str, deck: &str, phases: &[Vec<usize>], routine: &Rc<Vec<i32>>) {
    let mut copies = vec![];
    let mut pattern = vec![];
    for (p, taps) in phases.iter().enumerate() {
        for &age in taps {
            let copy = format!("{samples}_{p}_{age}");
            net.put(&copy, &vec![0; age]);
            copies.push(copy);
        }
    }
    let mut at = 0;
    for taps in phases {
        for _ in taps {
            pattern.push((copies[at].as_str(), 1));
            pattern.push(("deck:routine", 5));
            at += 1;
        }
    }
    let names: Vec<&str> = copies.iter().map(|s| s.as_str()).collect();
    net.copy(samples, &names);
    net.merge(deck, &pattern, &[("routine", routine)]);
}

/// Wire the upsampler into `net`: it reads the output stage's pairs (thousands and units of each 8 kHz sample) from
/// the pile `pairs`, and puts each 48 kHz sample on `out` as its thousands and units. `r1` and `r2` are the
/// routine's cards for the two stages (`routine`). Its own piles are named u_...
///
/// What the host does: yd's cards (one an 8 kHz sample) go to a copy for each tap of fir1, each starting with as many
/// blank cards as that tap's sample is old; fir1's deck is merged from them in a fixed order, the sample for a tap and
/// then the tap's five cards of the routine; and the same for fir2 from fir1's cards (one a 16 kHz sample).
pub fn wire(net: &mut Net, pairs: &str, out: &str, r1: &Rc<Vec<i32>>, r2: &Rc<Vec<i32>>) {
    net.add("yd", Program::Deck(YD), pairs, "u_yd");
    window(net, "u_yd", "u_fir1<", &stage1(), r1);
    net.add("fir1", Program::Listing(FIR), "u_fir1<", "u_y16");
    window(net, "u_y16", "u_fir2<", &stage2(), r2);
    net.add("fir2", Program::Listing(FIR), "u_fir2<", out);
}

/// Which samples to write.
#[derive(Clone, Copy, PartialEq)]
pub enum Rate {
    /// the 48 kHz samples, fir2's pairs
    Up,
    /// the 8 kHz samples underneath, the output stage's pairs as yd reads them
    Eight,
}

/// The whole voice box and upsampler on `deck`, a deck of frame cards: run until nothing moves, the samples written
/// to `w` as they come (as raw s16le, or with `values` the pairs one value a line). Returns the number of samples
/// written and the instruction counts of every machine, the table machines' first.
pub fn speak(deck: &[i32], rate: Rate, values: bool, w: &mut impl std::io::Write) -> (usize, Vec<(String, u64)>) {
    use cardiac_speech::voice;
    let (r1, mut steps) = routine("1", FIR1);
    let (r2, s2) = routine("2", FIR2);
    steps.extend(s2);
    let (r1, r2) = (Rc::new(r1), Rc::new(r2));
    let mut net = Net::new();
    voice::wire(&mut net, "frames", "frames2", "v_out");
    net.copy("v_out", &["out8", "u_pairs"]);
    wire(&mut net, "u_pairs", "out", &r1, &r2);
    voice::deal_frames(&mut net, deck, "frames", "frames2");
    let (keep, drop) = if rate == Rate::Up { ("out", "out8") } else { ("out8", "out") };
    let mut pending: Vec<i32> = vec![];
    let mut samples = 0usize;
    loop {
        let moved = net.round(200_000);
        pending.extend(net.take(keep));
        net.take(drop);
        let whole = pending.len() / 2 * 2;
        for pair in pending[..whole].chunks(2) {
            let ok = if values {
                writeln!(w, "{}\n{}", pair[0], pair[1])
            } else {
                let s = voice::sample(pair[0], pair[1]).unwrap_or_else(|| panic!("not a sample: {pair:?}"));
                w.write_all(&s.to_le_bytes())
            };
            if ok.is_err() {
                return (samples, steps);
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
    (samples, steps)
}

/// `-v`'s report on standard error: each machine's instruction count, the totals, and the cards moved.
pub fn report(steps: &[(String, u64)], samples: usize, rate: Rate, secs: f64) {
    let hz = if rate == Rate::Up { 48000.0 } else { 8000.0 };
    let speech = samples as f64 / hz;
    let total: u64 = steps.iter().map(|(_, s)| s).sum();
    for (n, s) in steps {
        eprintln!("{n:>8} {s:>12}");
    }
    eprintln!(
        "{} machines; {samples} samples at {} kHz ({speech:.2} s of speech); {total} instructions, {:.0} a second of speech; {secs:.3} s: real-time factor {:.4}",
        steps.len(), hz / 1000.0, total as f64 / speech, secs / speech
    );
    let (deck, read, out) = cardiac_speech::net::card_counts();
    eprintln!("cards: {deck} program cards loaded, {read} cards read by INPs, {out} values put out by OUTs");
}
