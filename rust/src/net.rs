//! A network of CARDIACs and the piles of cards between them. Each machine has one card reader and one punch, as a
//! real CARDIAC has: it reads one pile, its deck, a card at a time, and everything it punches goes onto one pile.
//! The host never looks at a machine's program counter or its cells, nor at which instruction punched a card.
//!
//! What the host does with the piles is bookkeeping, and none of it depends on what a card says (except a fetch,
//! which uses a card as a record number, as a librarian uses a call number):
//!
//! - deal: the cards put on a pile go `n` at a time to several piles in turn;
//! - copy: every card put on a pile goes onto several piles (the same cards for several machines);
//! - collate: whole records are taken from several piles and put together onto one, some of each record's cards
//!   (columns) picked, as a collator merges decks;
//! - merge: several piles go into one in a fixed order, so many cards from this pile, then so many from that, over
//!   and over, a pile waiting its turn until it has its cards; a deck can be one of them, dealt again each time
//!   its turn comes round;
//! - fetch: a card put on a fetch pile names a record of a table deck (the phoneme table, the filters), and the
//!   host puts that record onto another pile.
use std::collections::VecDeque;
use std::rc::Rc;
use std::sync::atomic::{AtomicU64, Ordering::Relaxed};

use heartburn::assemble;
use heartburn::cardiac::{Console, Event, Machine};

/// A pile of cards, by number.
pub type Pile = usize;

/// Cards moved, over every network made in this run: program cards loaded, cards read by INPs, values put out by
/// OUTs. For `talk -v`.
static DECK_CARDS: AtomicU64 = AtomicU64::new(0);
static CARDS_READ: AtomicU64 = AtomicU64::new(0);
static VALUES_OUT: AtomicU64 = AtomicU64::new(0);

/// (program cards loaded, cards read by INPs, values put out by OUTs), over every network so far.
pub fn card_counts() -> (u64, u64, u64) {
    (DECK_CARDS.load(Relaxed), CARDS_READ.load(Relaxed), VALUES_OUT.load(Relaxed))
}

/// A machine's program: a deck that `cargo cardiac build` made from Rust, or a listing written by hand.
pub enum Program<'a> {
    Deck(&'a str),
    Listing(&'a str),
}

struct Node {
    name: String,
    cardiac: Machine,
    /// the pile its reader reads
    input: Pile,
    /// the pile its punch punches onto
    output: Pile,
    /// halted (HRS): it runs no more
    done: bool,
    /// waiting at an INP for a card
    waiting: bool,
    /// what it has punched, kept when the environment's CARDIAC_SPEECH_TAP names a folder (for finding a fault)
    punched: Option<Vec<i32>>,
}

/// What a pile does with the cards put on it.
enum Kind {
    Keep,
    Deal { n: usize, to: Vec<Pile>, dealt: usize },
    Copy(Vec<Pile>),
    Fetch { table: Rc<Vec<i32>>, size: usize, from: usize, count: usize, to: Pile },
    /// the first `n` cards put on it are set aside, and the rest go onto `to`: a deck dealt again from a later card
    After { n: usize, seen: usize, to: Pile },
}

/// Whole records from several piles put together onto one: (source, record size, the cards of it kept).
struct Collate {
    out: Pile,
    from: Vec<(Pile, usize, Vec<usize>)>,
}

/// Where a merge takes its cards from: a pile, or a deck dealt again and again.
enum Source {
    Pile(Pile),
    Deck { deck: Rc<Vec<i32>>, at: usize },
}

/// Several sources into one pile in a fixed order: `pattern` is (source, how many cards), round and round.
struct Merge {
    out: Pile,
    sources: Vec<Source>,
    pattern: Vec<(usize, usize)>,
    at: usize,
    taken: usize,
}

pub struct Net {
    nodes: Vec<Node>,
    piles: Vec<VecDeque<i32>>,
    kinds: Vec<Kind>,
    names: Vec<String>,
    collates: Vec<Collate>,
    merges: Vec<Merge>,
}

fn put(piles: &mut [VecDeque<i32>], kinds: &mut [Kind], pile: Pile, card: i32) {
    match &mut kinds[pile] {
        Kind::Keep => piles[pile].push_back(card),
        Kind::Deal { n, to, dealt } => {
            let p = to[(*dealt / *n) % to.len()];
            *dealt += 1;
            put(piles, kinds, p, card);
        }
        Kind::Copy(to) => {
            for p in to.clone() {
                put(piles, kinds, p, card);
            }
        }
        Kind::Fetch { table, size, from, count, to } => {
            let (table, at, count, to) = (table.clone(), card as usize * *size + *from, *count, *to);
            assert!(card >= 0 && at + count <= table.len(), "no record {card} in the table");
            for &c in &table[at..at + count] {
                put(piles, kinds, to, c);
            }
        }
        Kind::After { n, seen, to } => {
            *seen += 1;
            if *seen > *n {
                let to = *to;
                put(piles, kinds, to, card);
            }
        }
    }
}

/// What a machine punches, onto its one pile.
struct Punch<'a> {
    out: Pile,
    tap: &'a mut Option<Vec<i32>>,
    piles: &'a mut Vec<VecDeque<i32>>,
    kinds: &'a mut Vec<Kind>,
}

impl Console for Punch<'_> {
    fn output(&mut self, card: i32) {
        VALUES_OUT.fetch_add(1, Relaxed);
        if let Some(t) = self.tap.as_mut() {
            t.push(card);
        }
        put(self.piles, self.kinds, self.out, card);
    }
}

/// A listing assembled, as carc assembles it: its deck.
fn assemble(name: &str, listing: &str) -> Vec<i32> {
    let asm = assemble::assemble(listing);
    let errors: Vec<_> = asm.diagnostics.iter().filter(|d| !d.warning).collect();
    assert!(errors.is_empty(), "{name} doesn't assemble: {errors:?}");
    assemble::deck(&asm, asm.start.expect("a listing with cells"))
}

/// A deck of cards written one a line, as `cargo cardiac build` writes a program's deck and as the tables are kept.
pub fn cards(text: &str) -> Vec<i32> {
    heartburn::tape::values(text).expect("a deck of cards")
}

impl Default for Net {
    fn default() -> Self {
        Net::new()
    }
}

impl Net {
    pub fn new() -> Net {
        Net { nodes: vec![], piles: vec![], kinds: vec![], names: vec![], collates: vec![], merges: vec![] }
    }

    /// The pile named `name`, made if there is none.
    pub fn pile(&mut self, name: &str) -> Pile {
        if let Some(i) = self.names.iter().position(|n| n == name) {
            return i;
        }
        self.names.push(name.to_string());
        self.piles.push(VecDeque::new());
        self.kinds.push(Kind::Keep);
        self.names.len() - 1
    }

    /// Cards put on `pile` from now on are dealt `n` at a time to `to`, in turn.
    pub fn deal(&mut self, pile: &str, n: usize, to: &[&str]) {
        let p = self.pile(pile);
        let to = to.iter().map(|t| self.pile(t)).collect();
        self.kinds[p] = Kind::Deal { n, to, dealt: 0 };
    }

    /// Every card put on `pile` from now on goes onto each of `to`.
    pub fn copy(&mut self, pile: &str, to: &[&str]) {
        let p = self.pile(pile);
        let to = to.iter().map(|t| self.pile(t)).collect();
        self.kinds[p] = Kind::Copy(to);
    }

    /// A card put on `pile` from now on names a record of `table` (records of `size` cards), whose cards `from` to
    /// `from + count` go onto `to`.
    pub fn fetch(&mut self, pile: &str, table: &Rc<Vec<i32>>, size: usize, from: usize, count: usize, to: &str) {
        let p = self.pile(pile);
        let to = self.pile(to);
        self.kinds[p] = Kind::Fetch { table: table.clone(), size, from, count, to };
    }

    /// The cards put on `pile` from now on go onto `to`, but for the first `n` of them: the same deck again from
    /// its card `n` on.
    pub fn after(&mut self, pile: &str, n: usize, to: &str) {
        let p = self.pile(pile);
        let to = self.pile(to);
        self.kinds[p] = Kind::After { n, seen: 0, to };
    }

    /// Every card put on `pile` goes onto a pile for each of `readers`, named `pile>reader`: the same cards for
    /// several readers.
    pub fn fan(&mut self, pile: &str, readers: &[&str]) {
        let to: Vec<String> = readers.iter().map(|r| format!("{pile}>{r}")).collect();
        let to: Vec<&str> = to.iter().map(|s| s.as_str()).collect();
        self.copy(pile, &to);
    }

    /// Whenever each of `from` holds a whole record (its size), the records are taken off and the cards picked
    /// from each put together onto `out`.
    pub fn collate(&mut self, out: &str, from: &[(&str, usize, &[usize])]) {
        let out = self.pile(out);
        let from = from.iter().map(|&(p, n, c)| (self.pile(p), n, c.to_vec())).collect();
        self.collates.push(Collate { out, from });
    }

    /// Cards go onto `out` from the piles in `pattern` in turn, so many from each, over and over (0 for every card
    /// from then on); a pile named `deck:NAME` is the deck given for NAME in `decks`, dealt again from its start
    /// each time its turn comes.
    pub fn merge(&mut self, out: &str, pattern: &[(&str, usize)], decks: &[(&str, &Rc<Vec<i32>>)]) {
        let out = self.pile(out);
        let mut names: Vec<&str> = vec![];
        let mut sources = vec![];
        let mut pat = vec![];
        for &(name, n) in pattern {
            let i = match names.iter().position(|m| *m == name) {
                Some(i) => i,
                None => {
                    names.push(name);
                    sources.push(match name.strip_prefix("deck:") {
                        Some(d) => {
                            let deck = decks.iter().find(|(k, _)| *k == d).unwrap_or_else(|| panic!("no deck {d}"));
                            Source::Deck { deck: deck.1.clone(), at: 0 }
                        }
                        None => Source::Pile(self.pile(name)),
                    });
                    sources.len() - 1
                }
            };
            pat.push((i, n));
        }
        assert!(sources.iter().any(|s| matches!(s, Source::Pile(_))), "a merge of decks alone never waits");
        self.merges.push(Merge { out, sources, pattern: pat, at: 0, taken: 0 });
    }

    fn collate_all(&mut self) -> bool {
        let mut moved = false;
        for c in 0..self.collates.len() {
            loop {
                let ready = self.collates[c].from.iter().all(|(p, n, _)| self.piles[*p].len() >= *n);
                if !ready {
                    break;
                }
                let mut rec = vec![];
                for (p, n, keep) in &self.collates[c].from {
                    let r: Vec<i32> = self.piles[*p].drain(..*n).collect();
                    rec.extend(keep.iter().map(|&k| r[k]));
                }
                let out = self.collates[c].out;
                for card in rec {
                    put(&mut self.piles, &mut self.kinds, out, card);
                }
                moved = true;
            }
        }
        moved
    }

    fn merge_all(&mut self) -> bool {
        let mut moved = false;
        for m in self.merges.iter_mut() {
            loop {
                let (s, n) = m.pattern[m.at];
                let card = match &mut m.sources[s] {
                    Source::Pile(p) => match self.piles[*p].pop_front() {
                        Some(c) => c,
                        None => break,
                    },
                    Source::Deck { deck, at } => {
                        let c = deck[*at];
                        *at = (*at + 1) % deck.len();
                        c
                    }
                };
                put(&mut self.piles, &mut self.kinds, m.out, card);
                moved = true;
                m.taken += 1;
                if m.taken == n && n > 0 {
                    m.taken = 0;
                    m.at = (m.at + 1) % m.pattern.len();
                }
            }
        }
        moved
    }

    /// A machine running `program`: its reader reads pile `input`, and its punch punches onto pile `output`.
    pub fn add(&mut self, name: &str, program: Program, input: &str, output: &str) {
        let deck = match program {
            Program::Deck(text) => cards(text),
            Program::Listing(text) => assemble(name, text),
        };
        let (input, output) = (self.pile(input), self.pile(output));
        let mut cardiac = Machine::new();
        cardiac.push(&deck);
        DECK_CARDS.fetch_add(deck.len() as u64, Relaxed);
        let punched = std::env::var_os("CARDIAC_SPEECH_TAP").map(|_| vec![]);
        self.nodes.push(Node { name: name.into(), cardiac, input, output, done: false, waiting: false, punched });
    }

    /// Put cards on a pile.
    pub fn put(&mut self, pile: &str, cards: &[i32]) {
        let p = self.pile(pile);
        for &c in cards {
            put(&mut self.piles, &mut self.kinds, p, c);
        }
    }

    /// Take every card off a pile.
    pub fn take(&mut self, pile: &str) -> Vec<i32> {
        let p = self.pile(pile);
        self.piles[p].drain(..).collect()
    }

    /// One round: the collators and merges move what they can, then each machine in turn runs for as long as its
    /// reader has cards (at most `budget` instructions each). Returns whether anything moved.
    pub fn round(&mut self, budget: u64) -> bool {
        let mut moved = self.collate_all();
        moved |= self.merge_all();
        for node in self.nodes.iter_mut() {
            if node.done {
                continue;
            }
            let mut spent = 0;
            loop {
                if node.waiting {
                    let Some(card) = self.piles[node.input].pop_front() else { break };
                    node.cardiac.push(&[card]);
                    CARDS_READ.fetch_add(1, Relaxed);
                    node.waiting = false;
                }
                let before = node.cardiac.steps();
                let mut punch =
                    Punch { out: node.output, tap: &mut node.punched, piles: &mut self.piles, kinds: &mut self.kinds };
                let event = node.cardiac.run(budget.saturating_sub(spent).max(1), &mut punch);
                spent += node.cardiac.steps() - before;
                moved = true;
                match event {
                    Event::Input => node.waiting = true,
                    Event::Halt => {
                        node.done = true;
                        break;
                    }
                    Event::Budget => break,
                    other => panic!("{}: stopped for {other:?}", node.name),
                }
                if spent >= budget {
                    break;
                }
            }
        }
        moved
    }

    /// Run every machine until none can go on. With CARDIAC_SPEECH_TAP set, what each machine punched is written
    /// out afterwards, or when something goes wrong.
    pub fn run(&mut self) {
        let run = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| while self.round(u64::MAX) {}));
        self.tap();
        if let Err(e) = run {
            std::panic::resume_unwind(e);
        }
    }

    /// With CARDIAC_SPEECH_TAP set to a folder, write what each machine punched there, a file a machine.
    pub fn tap(&self) {
        let Some(dir) = std::env::var_os("CARDIAC_SPEECH_TAP") else { return };
        std::fs::create_dir_all(&dir).expect("the tap folder");
        let piles: String = self.names.iter().zip(&self.piles).filter(|(_, p)| !p.is_empty())
            .map(|(n, p)| format!("{n} {}\n", p.len())).collect();
        std::fs::write(std::path::Path::new(&dir).join("_piles"), piles).expect("a tap file");
        for n in &self.nodes {
            let text: String = n.punched.iter().flatten().map(|c| format!("{c}\n")).collect();
            std::fs::write(std::path::Path::new(&dir).join(&n.name), text).expect("a tap file");
        }
    }

    /// Each machine's name and the instructions it has run (the loader's among them).
    pub fn steps(&self) -> Vec<(String, u64)> {
        self.nodes.iter().map(|n| (n.name.clone(), n.cardiac.steps())).collect()
    }
}
