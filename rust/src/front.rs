//! The front end: phoneme cards in, frame cards out, on CARDIACs in five phases.
//!
//! 1. `seg` reads the phonemes and makes a record for each segment (and the pauses at the start and the end); the
//!    host puts each beside six cards of its row of the phoneme table.
//! 2. The host puts the records in the opposite order, and `after`, `ahead`, `p1` and `next` work out, last first,
//!    what lies ahead of each segment.
//! 3. The host puts those decks back in order, and a dozen machines work out each segment's stress, duration,
//!    frames and filters, and `sum` a summary of each sentence for the pitch.
//! 4. Last first again, `fill` hands each sentence's summary to all its segments.
//! 5. Forward, `framer` and the three `spread`s turn the segments into frames, and the rest work frame by frame
//!    to the frame cards.
//!
//! The host's work, under the one-reader rule: each machine's deck is collated from whole records of the decks it
//! reads (some cards, columns, of each), a record a segment or a record a frame, so that its order never depends on
//! what the cards say; table rows are fetched by a record number in a column; and four decks are merged a few cards
//! at a time in a fixed pattern (glidea, halfway and glideb read two filters side by side, gnorm a glide record
//! after its frame's cards, asm the next frame's snd and V after its own frame).
use std::rc::Rc;

use crate::net::{Net, Program};

macro_rules! decks {
    ($($name:ident = $file:literal),* $(,)?) => {
        $(const $name: &str = include_str!(concat!("../machines/front/", $file, ".cqb"));)*
    };
}

decks! {
    SEG = "seg", AFTER = "after", AHEAD = "ahead", P1 = "p1", NEXT = "next", STRESS = "stress", BASE = "base",
    RULES2 = "rules2", RULES5 = "rules5", RULES7 = "rules7", RULES9 = "rules9", MUL = "mul", DUR = "dur",
    NFRAMES = "nframes", BACK = "back", SUM = "sum", FILL = "fill", CLOSURE = "closure", MAIN = "main", EDGE = "edge",
    LOUD = "loud", FRAMER = "framer", WEIGHTS = "weights", SPREAD = "spread", CHOOSE = "choose", GLIDES = "glides",
    GLIDEA = "glidea", HALFWAY = "halfway", GLIDEB = "glideb", DECL = "decl", ONSET = "onset", RISE = "rise",
    TAILY = "taily", TAILT = "tailt", TAILF = "tailf", PERIOD = "period", LSEL = "lsel", VSEL = "vsel", PSEL = "psel",
    GNORM = "gnorm", SCALE = "scale", FALL = "fall", BOOST = "boost", KCARRY = "kcarry", ASM = "asm",
}

/// The phoneme table (one record of `FEAT_SIZE` cards a phoneme code), the filters (11 cards each: K10 to K1 and
/// the gain) and the glides' level factors (a record of three cards a filter for each filter a segment glides from):
/// precomputed once from the published figures (ref/table.py), the only precomputed part. The same decks as the
/// hand-written version's.
pub const FEATURES: &str = include_str!("../../front/features.cards");
pub const FILTERS: &str = include_str!("../../front/filters.cards");
pub const GLIDE_TABLE: &str = include_str!("../../front/glides.cards");
pub const FEAT_SIZE: usize = 17;
const FILTER: usize = 11;
// the phoneme table's columns (ref/table.py)
const F_BACK: usize = 6;
const F_TS: usize = 7;
const F_ASP: usize = 9;
const F_VOICED: usize = 10;
const F_LOUD: usize = 14;
const F_CINH: usize = 15;
/// AX's code: its row gives HH before no vowel its filter, and a sonorant with no vowel next to it its loudness.
const AX: usize = 18;

pub struct Tables {
    pub features: Rc<Vec<i32>>,
    pub filters: Rc<Vec<i32>>,
    pub glides: Rc<Vec<i32>>,
}

impl Tables {
    pub fn load() -> Tables {
        let read = |t: &str| Rc::new(crate::net::cards(t));
        Tables { features: read(FEATURES), filters: read(FILTERS), glides: read(GLIDE_TABLE) }
    }

    /// Cards `from` to `from + count` of the phoneme table's row for `code`.
    fn row(&self, code: usize, from: usize, count: usize) -> Vec<i32> {
        self.features[code * FEAT_SIZE + from..code * FEAT_SIZE + from + count].to_vec()
    }
}

// A segment's record, R1: pc s wf pms send (from seg) kind inh mn cls9 liq vls (its row of the phoneme table)
const PC: usize = 0;
const S: usize = 1;
const WF: usize = 2;
const PMS: usize = 3;
const SEND: usize = 4;
const KIND: usize = 5;
const INH: usize = 6;
const MN: usize = 7;
const CLS9: usize = 8;
const LIQ: usize = 9;
const VLS: usize = 10;
pub const R1: usize = 11;

fn records(cards: &[i32], size: usize) -> Vec<Vec<i32>> {
    assert_eq!(cards.len() % size, 0, "a deck of whole records");
    cards.chunks(size).map(|c| c.to_vec()).collect()
}

/// A deck of records in the opposite order.
pub fn reversed(cards: &[i32], size: usize) -> Vec<i32> {
    records(cards, size).into_iter().rev().flatten().collect()
}

/// Machine `name` reads its deck from pile `name<` and punches onto pile `name`.
fn machine(net: &mut Net, name: &str, deck: &str) {
    net.add(name, Program::Deck(deck), &format!("{name}<"), name);
}

/// A fetch: each card of column `col` of `src`'s records (of `size` cards) names a record of `table` (records of
/// `rec` cards), whose cards `from` to `from + count` go onto pile `to`.
#[allow(clippy::too_many_arguments)]
fn fetch(net: &mut Net, src: &str, size: usize, col: usize, table: &Rc<Vec<i32>>, rec: usize, from: usize, count: usize, to: &str) {
    let ask = format!("{to}?");
    net.collate(&ask, &[(src, size, &[col])]);
    net.fetch(&ask, table, rec, from, count, to);
}

fn all(n: usize) -> Vec<usize> {
    (0..n).collect()
}

/// Phase 1: phoneme cards in from `tokens`, a record of R1 cards a segment out onto `out`.
pub fn segments(net: &mut Net, t: &Tables, tokens: &str, out: &str) {
    net.add("seg", Program::Deck(SEG), tokens, "seg");
    net.fan("seg", &["rec", "row"]);
    fetch(net, "seg>row", 5, PC, &t.features, FEAT_SIZE, 0, 6, "seg_row");
    net.collate(out, &[("seg>rec", 5, &all(5)), ("seg_row", 6, &all(6))]);
}

/// Phase 2: the segment records, last first, in; out what lies ahead of each segment, last first: A (after imm nvs),
/// B (nextk pfw), P (p1) and C (nxtpc adjv nextv ts te nts).
pub fn ahead(net: &mut Net, t: &Tables, r1: &[i32]) {
    let rev = reversed(r1, R1);
    for reader in ["after", "ahead", "p1", "next", "next_row"] {
        net.put(&format!("r>{reader}"), &rev);
    }
    machine(net, "after", AFTER);
    net.collate("after<", &[("r>after", R1, &[KIND, S, WF])]);
    net.fan("after", &["out", "p1"]);
    net.copy("after>out", &["A"]);
    machine(net, "ahead", AHEAD);
    net.collate("ahead<", &[("r>ahead", R1, &[KIND, WF])]);
    net.copy("ahead", &["B"]);
    machine(net, "p1", P1);
    net.collate("p1<", &[("r>p1", R1, &[KIND, WF, CLS9]), ("after>p1", 3, &[0, 1])]);
    net.copy("p1", &["P"]);
    machine(net, "next", NEXT);
    net.put("next<", &t.row(AX, F_ASP, 1));
    fetch(net, "r>next_row", R1, PC, &t.features, FEAT_SIZE, F_TS, 3, "next_row");
    net.collate("next<", &[("r>next", R1, &[PC, KIND]), ("next_row", 3, &all(3))]);
    net.copy("next", &["C"]);
}

/// The decks phase 3 hands on: per segment, n (frames), st (s fs pf bef), bk (pte prevv pvls pnpk), sm (send L
/// tail), cl (c), mn (ma mb uon vm gl), ed (cf af) and ld (the loudness of a voiced and of a breathy frame).
pub const PHASE3: [(&str, usize); 8] = [("n", 1), ("st", 4), ("bk", 4), ("sm", 3), ("cl", 1), ("mn", 5), ("ed", 2), ("ld", 2)];

/// Phase 3: the segment records and what lies ahead of each (in order now) in; each segment's stress, duration,
/// frames and filters out, onto the piles named in PHASE3 with `out:` in front.
pub fn durations(net: &mut Net, t: &Tables, r1: &[i32], a: &[i32], b: &[i32], p: &[i32], c: &[i32]) {
    let decks: [(&str, &[i32], &[&str]); 5] = [
        ("r1", r1, &["stress", "base", "rules2", "rules5", "rules7", "rules9", "nframes", "back", "sum", "closure",
            "closure_row", "main", "main_row", "edge", "edge_row"]),
        ("A", a, &["stress", "rules5", "rules7"]),
        ("B", b, &["stress", "rules7", "rules9"]),
        ("P", p, &["rules9"]),
        ("C", c, &["back", "main", "main_row", "loud", "loud_adjv", "loud_nextv"]),
    ];
    for (name, deck, readers) in decks {
        for r in readers {
            net.put(&format!("{name}>{r}"), deck);
        }
    }
    machine(net, "stress", STRESS);
    net.collate("stress<", &[("r1>stress", R1, &[KIND, S, WF]), ("A>stress", 3, &all(3)), ("B>stress", 2, &[1])]);
    net.fan("stress", &["base", "rules2", "rules5", "rules7", "rules9", "sum", "out"]);
    machine(net, "base", BASE);
    net.collate("base<", &[("r1>base", R1, &[KIND, INH, MN, PMS, VLS]), ("stress>base", 4, &[0])]);
    machine(net, "rules2", RULES2);
    net.collate("rules2<", &[("r1>rules2", R1, &[KIND, LIQ]), ("stress>rules2", 4, &[1, 2])]);
    machine(net, "rules5", RULES5);
    net.collate("rules5<", &[("r1>rules5", R1, &[KIND, WF]), ("A>rules5", 3, &[0]), ("stress>rules5", 4, &[3])]);
    machine(net, "rules7", RULES7);
    net.collate("rules7<", &[("r1>rules7", R1, &[KIND]), ("A>rules7", 3, &[0]), ("stress>rules7", 4, &[3, 0]),
        ("B>rules7", 2, &[0])]);
    machine(net, "rules9", RULES9);
    net.collate("rules9<", &[("r1>rules9", R1, &[KIND]), ("B>rules9", 2, &[0]), ("P>rules9", 1, &[0]),
        ("stress>rules9", 4, &[2])]);
    machine(net, "mul", MUL);
    net.collate("mul<", &[("rules2", 4, &all(4)), ("rules5", 2, &all(2)), ("rules7", 1, &[0]), ("rules9", 3, &all(3))]);
    machine(net, "dur", DUR);
    net.collate("dur<", &[("base", 2, &all(2)), ("mul", 1, &[0])]);
    machine(net, "nframes", NFRAMES);
    net.collate("nframes<", &[("r1>nframes", R1, &[KIND]), ("dur", 1, &[0])]);
    net.fan("nframes", &["sum", "closure", "edge", "out"]);
    machine(net, "back", BACK);
    net.collate("back<", &[("r1>back", R1, &[PC, KIND, VLS]), ("C>back", 6, &[4])]);
    net.fan("back", &["edge", "loud", "loud_prevv", "out"]);
    machine(net, "sum", SUM);
    net.collate("sum<", &[("r1>sum", R1, &[KIND, SEND]), ("stress>sum", 4, &[0]), ("nframes>sum", 1, &[0])]);
    machine(net, "closure", CLOSURE);
    fetch(net, "r1>closure_row", R1, PC, &t.features, FEAT_SIZE, F_CINH, 2, "closure_row");
    net.collate("closure<", &[("r1>closure", R1, &[KIND]), ("nframes>closure", 1, &[0]), ("closure_row", 2, &all(2))]);
    machine(net, "main", MAIN);
    fetch(net, "r1>main_row", R1, PC, &t.features, FEAT_SIZE, F_VOICED, 3, "main_row");
    fetch(net, "C>main_row", 6, 0, &t.features, FEAT_SIZE, F_BACK, 1, "main_next");
    net.collate("main<", &[("r1>main", R1, &[KIND]), ("C>main", 6, &[3, 4]), ("main_row", 3, &all(3)),
        ("main_next", 1, &[0])]);
    machine(net, "edge", EDGE);
    fetch(net, "r1>edge_row", R1, PC, &t.features, FEAT_SIZE, F_ASP, 5, "edge_row");
    net.collate("edge<", &[("r1>edge", R1, &[KIND]), ("nframes>edge", 1, &[0]), ("back>edge", 4, &[2, 3]),
        ("edge_row", 5, &[0, 1, 4])]);
    machine(net, "loud", LOUD);
    net.put("loud<", &t.row(AX, F_LOUD, 1));
    fetch(net, "C>loud_adjv", 6, 1, &t.features, FEAT_SIZE, F_LOUD, 1, "loud_adjv");
    fetch(net, "back>loud_prevv", 4, 1, &t.features, FEAT_SIZE, F_LOUD, 1, "loud_prevv");
    fetch(net, "C>loud_nextv", 6, 2, &t.features, FEAT_SIZE, F_LOUD, 1, "loud_nextv");
    net.collate("loud<", &[("C>loud", 6, &[1]), ("back>loud", 4, &[1]), ("loud_adjv", 1, &[0]),
        ("loud_prevv", 1, &[0]), ("loud_nextv", 1, &[0])]);
    for (name, from) in [("n", "nframes>out"), ("st", "stress>out"), ("bk", "back>out"), ("sm", "sum"), ("cl", "closure"),
        ("mn", "main"), ("ed", "edge"), ("ld", "loud")] {
        net.copy(from, &[&format!("out:{name}")]);
    }
}

/// Phase 4: sum's records, last first, in; each segment's sentence summary out, last first, onto `out`.
pub fn fill(net: &mut Net, sm: &[i32], out: &str) {
    net.put("fill<", &reversed(sm, 3));
    machine(net, "fill", FILL);
    net.copy("fill", &[out]);
}

/// Phase 5: per segment, the records and decks of phases 1 to 4 (in order), in; the frame cards out onto `frames`.
#[allow(clippy::too_many_arguments)]
pub fn frames(net: &mut Net, t: &Tables, r1: &[i32], c: &[i32], n: &[i32], st: &[i32], bk: &[i32], cl: &[i32], mn: &[i32],
    ed: &[i32], ld: &[i32], fl: &[i32], frames: &str) {
    for (name, deck, readers) in [
        ("r1", r1, &["framer", "spreadb"][..]),
        ("C", c, &["spreadb"]),
        ("n", n, &["framer", "spreada", "spreadb", "spreadc"]),
        ("st", st, &["spreadb"]),
        ("bk", bk, &["spreadb"]),
        ("cl", cl, &["spreada"]),
        ("mn", mn, &["spreada"]),
        ("ed", ed, &["spreada"]),
        ("ld", ld, &["spreadc"]),
        ("fl", fl, &["spreadc"]),
    ] {
        for r in readers {
            net.put(&format!("{name}>{r}"), deck);
        }
    }
    // the segments, frame by frame
    machine(net, "framer", FRAMER);
    net.collate("framer<", &[("n>framer", 1, &[0]), ("r1>framer", R1, &[SEND])]);
    net.fan("framer", &["weights", "choose", "decl", "rise", "taily", "vsel"]);
    // spreada: c ma mb uon vm gl cf af, for choose
    machine(net, "spreada", SPREAD);
    net.put("spreada<", &[8]);
    net.collate("spreada<", &[("n>spreada", 1, &[0]), ("cl>spreada", 1, &[0]), ("mn>spreada", 5, &all(5)),
        ("ed>spreada", 2, &[0, 1])]);
    // spreadb: pte nts kind s, for glides, the pitch and the level
    machine(net, "spreadb", SPREAD);
    net.put("spreadb<", &[4]);
    net.collate("spreadb<", &[("n>spreadb", 1, &[0]), ("bk>spreadb", 4, &[0]), ("C>spreadb", 6, &[5]),
        ("r1>spreadb", R1, &[KIND]), ("st>spreadb", 4, &[0])]);
    net.fan("spreadb", &["glides", "onset", "lsel", "vsel"]);
    // spreadc: L, the tail's start, M, the end, and the two loudnesses, for the pitch and the level
    machine(net, "spreadc", SPREAD);
    net.put("spreadc<", &[6]);
    net.collate("spreadc<", &[("n>spreadc", 1, &[0]), ("fl>spreadc", 4, &all(4)), ("ld>spreadc", 2, &all(2))]);
    net.fan("spreadc", &["decl", "taily", "tailt", "tailf", "lsel"]);
    // the filters
    machine(net, "weights", WEIGHTS);
    net.collate("weights<", &[("framer>weights", 6, &[0, 1, 2])]);
    // choose: a b uu snd V g
    const CH: usize = 6;
    machine(net, "choose", CHOOSE);
    net.collate("choose<", &[("framer>choose", 6, &[0, 3, 4]), ("spreada", 8, &all(8))]);
    net.fan("choose", &["glides", "glidea", "rowa", "rowb", "lsel", "vsel", "psel", "scale1", "kcarry", "next"]);
    machine(net, "glides", GLIDES);
    net.collate("glides<", &[("weights", 2, &all(2)), ("spreadb>glides", 4, &[0, 1]), ("choose>glides", CH, &[0, 1, 5])]);
    net.fan("glides", &["gn", "go", "glideb", "gnorm", "grec"]);
    machine(net, "glidea", GLIDEA);
    fetch(net, "choose>rowa", CH, 0, &t.filters, FILTER, 0, FILTER, "rowa");
    fetch(net, "choose>rowb", CH, 1, &t.filters, FILTER, 0, FILTER, "rowb");
    net.collate("glidea_u", &[("choose>glidea", CH, &[2])]);
    let mut side = vec![("glidea_u", 1)];
    side.extend([("rowa", 1), ("rowb", 1)].repeat(FILTER));
    net.merge("glidea<", &side, &[]);
    net.fan("glidea", &["k", "g"]);
    machine(net, "halfway", HALFWAY);
    fetch(net, "glides>gn", 3, 0, &t.filters, FILTER, 0, 10, "rown");
    fetch(net, "glides>go", 3, 1, &t.filters, FILTER, 0, 10, "rowo");
    net.merge("halfway<", &[("rown", 1), ("rowo", 1)], &[]);
    machine(net, "glideb", GLIDEB);
    net.collate("glideb_w", &[("glides>glideb", 3, &[2])]);
    net.collate("glideb_k", &[("glidea>k", FILTER, &all(10))]);
    let mut side = vec![("glideb_w", 1)];
    side.extend([("halfway", 1), ("glideb_k", 1)].repeat(10));
    net.merge("glideb<", &side, &[]);
    // the pitch
    machine(net, "decl", DECL);
    net.collate("decl<", &[("framer>decl", 6, &[5]), ("spreadc>decl", 6, &[0])]);
    net.fan("decl", &["onset", "rise"]);
    machine(net, "onset", ONSET);
    net.collate("onset<", &[("spreadb>onset", 4, &[2, 3]), ("decl>onset", 1, &[0])]);
    machine(net, "rise", RISE);
    net.collate("rise<", &[("framer>rise", 6, &[3]), ("decl>rise", 1, &[0]), ("onset", 1, &[0])]);
    net.fan("rise", &["tailt", "tailf"]);
    machine(net, "taily", TAILY);
    net.collate("taily<", &[("framer>taily", 6, &[5]), ("spreadc>taily", 6, &[1, 2])]);
    machine(net, "tailt", TAILT);
    net.collate("tailt<", &[("spreadc>tailt", 6, &[3]), ("taily", 1, &[0]), ("rise>tailt", 1, &[0])]);
    machine(net, "tailf", TAILF);
    net.collate("tailf<", &[("spreadc>tailf", 6, &[3]), ("rise>tailf", 1, &[0]), ("tailt", 1, &[0])]);
    machine(net, "period", PERIOD);
    net.copy("tailf", &["period<"]);
    net.fan("period", &["psel", "asm"]);
    // the level
    machine(net, "lsel", LSEL);
    net.collate("lsel<", &[("choose>lsel", CH, &[3, 4]), ("spreadb>lsel", 4, &[2]), ("spreadc>lsel", 6, &[4, 5])]);
    machine(net, "vsel", VSEL);
    net.collate("vsel<", &[("choose>vsel", CH, &[3, 4]), ("spreadb>vsel", 4, &[2, 3]), ("framer>vsel", 6, &[3])]);
    net.fan("vsel", &["scale2", "fall"]);
    machine(net, "psel", PSEL);
    net.collate("psel<", &[("choose>psel", CH, &[3, 4]), ("period>psel", 1, &[0])]);
    machine(net, "gnorm", GNORM);
    net.collate("gnorm_gw", &[("glides>gnorm", 3, &[0, 2])]);
    let record = 3 * t.filters.len() / FILTER;
    fetch(net, "glides>grec", 3, 1, &t.glides, record, 0, record, "grec");
    net.merge("gnorm<", &[("gnorm_gw", 2), ("grec", record)], &[]);
    machine(net, "scale1", SCALE);
    net.collate("scale1<", &[("choose>scale1", CH, &[3, 4]), ("glidea>g", FILTER, &[10]), ("lsel", 2, &all(2))]);
    machine(net, "scale2", SCALE);
    net.collate("scale2<", &[("scale1", 3, &all(3)), ("vsel>scale2", 4, &[0, 1])]);
    machine(net, "fall", FALL);
    net.collate("fall<", &[("scale2", 3, &all(3)), ("vsel>fall", 4, &[2, 3])]);
    machine(net, "scale4", SCALE);
    net.collate("scale4<", &[("fall", 3, &all(3)), ("psel", 2, &all(2))]);
    machine(net, "boost", BOOST);
    net.collate("boost<", &[("scale4", 3, &all(3)), ("gnorm", 2, &all(2))]);
    // the silences' filters, and the frame cards
    machine(net, "kcarry", KCARRY);
    net.collate("kcarry<", &[("choose>kcarry", CH, &[3]), ("glideb", 10, &all(10))]);
    machine(net, "asm", ASM);
    net.collate("asm_next", &[("choose>next", CH, &[3, 4])]);
    net.after("asm_next", 2, "asm_next2");
    net.merge("asm<", &[("boost", 3), ("period>asm", 1), ("kcarry", 10), ("asm_next2", 2)], &[]);
    net.copy("asm", &[frames]);
}

/// Phoneme cards to frame cards, phase by phase, every machine run to the end. Returns the frame cards and each
/// machine's instruction count.
pub fn phonemes_to_frames(tokens: &[i32]) -> (Vec<i32>, Vec<(String, u64)>) {
    let t = Tables::load();
    let mut steps = vec![];
    let mut net = Net::new();
    segments(&mut net, &t, "tokens", "r1");
    net.put("tokens", tokens);
    net.run();
    let r1 = net.take("r1");
    steps.extend(net.steps());
    let (frames, more) = segments_to_frames(&t, &r1);
    steps.extend(more);
    (frames, steps)
}

/// Phases 2 to 5: the segment records to frame cards. Returns the frame cards and each machine's instruction count.
pub fn segments_to_frames(t: &Tables, r1: &[i32]) -> (Vec<i32>, Vec<(String, u64)>) {
    let mut steps = vec![];
    let mut net = Net::new();
    ahead(&mut net, t, r1);
    net.run();
    let back = |net: &mut Net, pile: &str, size: usize| reversed(&net.take(pile), size);
    let (a, b, p, c) = (back(&mut net, "A", 3), back(&mut net, "B", 2), back(&mut net, "P", 1), back(&mut net, "C", 6));
    steps.extend(net.steps());
    let mut net = Net::new();
    durations(&mut net, t, r1, &a, &b, &p, &c);
    net.run();
    let d: Vec<Vec<i32>> = PHASE3.iter().map(|(name, _)| net.take(&format!("out:{name}"))).collect();
    steps.extend(net.steps());
    let mut net = Net::new();
    fill(&mut net, &d[3], "fl");
    net.run();
    let fl = reversed(&net.take("fl"), 4);
    steps.extend(net.steps());
    let mut net = Net::new();
    frames(&mut net, t, r1, &c, &d[0], &d[1], &d[2], &d[4], &d[5], &d[6], &d[7], &fl, "frames");
    net.run();
    steps.extend(net.steps());
    (net.take("frames"), steps)
}
