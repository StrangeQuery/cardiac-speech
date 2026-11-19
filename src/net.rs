//! A network of CARDIACs and the piles of cards between them. The host only moves cards: a machine waiting at an
//! INP is given the next card of the pile wired to that INP's cell, and each value a machine outputs goes onto the
//! pile wired to the OUT's cell. A pile can also be dealt: its cards go a few at a time to several piles in turn.
//! Nothing here looks at a card's value.
use std::collections::VecDeque;

use heartburn::assemble;
use heartburn::cardiac::{At, Console, Event, Machine};

/// A pile of cards, by number.
pub type Pile = usize;

/// Where a machine's INPs read and its OUTs punch: a pile for each cell, and one for the cells not named.
struct Wiring {
    inp: [Pile; 100],
    out: [Pile; 100],
}

struct Node {
    name: String,
    cardiac: Machine,
    wiring: Wiring,
    /// halted (HRS): it runs no more
    done: bool,
    /// waiting at an INP for a card
    waiting: bool,
}

/// What a pile does with the cards put on it: keeps them, or deals them `n` at a time to the piles in turn.
#[derive(Clone)]
enum Kind {
    Keep,
    Deal { n: usize, to: Vec<Pile>, dealt: usize },
}

pub struct Net {
    nodes: Vec<Node>,
    piles: Vec<VecDeque<i32>>,
    kinds: Vec<Kind>,
    names: Vec<String>,
}

/// The values a machine outputs, onto the piles its OUTs are wired to.
struct Punch<'a> {
    out: &'a [Pile; 100],
    piles: &'a mut Vec<VecDeque<i32>>,
    kinds: &'a mut Vec<Kind>,
}

fn put(piles: &mut [VecDeque<i32>], kinds: &mut [Kind], pile: Pile, card: i32) {
    match &mut kinds[pile] {
        Kind::Keep => piles[pile].push_back(card),
        Kind::Deal { n, to, dealt } => {
            let p = to[(*dealt / *n) % to.len()];
            *dealt += 1;
            piles[p].push_back(card);
        }
    }
}

impl Console for Punch<'_> {
    fn output(&mut self, _card: i32) {
        unreachable!("outputs go by their cell")
    }

    fn output_at(&mut self, card: i32, at: At) {
        put(self.piles, self.kinds, self.out[at.cell], card);
    }
}

/// A listing assembled, as carc assembles it: its deck and its labels.
pub fn assemble(name: &str, listing: &str) -> (Vec<i32>, Vec<(String, usize)>) {
    let asm = assemble::assemble(listing);
    let errors: Vec<_> = asm.diagnostics.iter().filter(|d| !d.warning).collect();
    assert!(errors.is_empty(), "{name} doesn't assemble: {errors:?}");
    let deck = assemble::deck(&asm, asm.start.expect("a listing with cells"));
    let labels = asm.rows.iter().filter_map(|r| r.label.clone().map(|l| (l, r.addr))).collect();
    (deck, labels)
}

impl Default for Net {
    fn default() -> Self {
        Net::new()
    }
}

impl Net {
    pub fn new() -> Net {
        Net { nodes: vec![], piles: vec![], kinds: vec![], names: vec![] }
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

    /// A machine running `listing`. `inp` and `out` wire cells to piles: a cell by its label or its number, and
    /// `*` for every other cell.
    pub fn add(&mut self, name: &str, listing: &str, inp: &[(&str, &str)], out: &[(&str, &str)]) {
        let (deck, labels) = assemble(name, listing);
        let cell = |k: &str| -> usize {
            k.parse()
                .ok()
                .or_else(|| labels.iter().find(|(l, _)| l == k).map(|&(_, a)| a))
                .unwrap_or_else(|| panic!("{name}: no cell {k}"))
        };
        let mut wire = |pairs: &[(&str, &str)]| -> [Pile; 100] {
            let rest = pairs.iter().find(|(k, _)| *k == "*").map(|(_, p)| *p).unwrap_or("-");
            let rest = self.pile(rest);
            let mut w = [rest; 100];
            for (k, p) in pairs.iter().filter(|(k, _)| *k != "*") {
                w[cell(k)] = self.pile(p);
            }
            w
        };
        let wiring = Wiring { inp: wire(inp), out: wire(out) };
        let mut cardiac = Machine::new();
        cardiac.push(&deck);
        self.nodes.push(Node { name: name.into(), cardiac, wiring, done: false, waiting: false });
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

    /// How many cards a pile holds.
    pub fn len(&mut self, pile: &str) -> usize {
        let p = self.pile(pile);
        self.piles[p].len()
    }

    /// One round: each machine in turn runs for as long as it has cards (at most `budget` instructions each).
    /// Returns whether anything ran.
    pub fn round(&mut self, budget: u64) -> bool {
        let mut moved = false;
        for node in self.nodes.iter_mut() {
            if node.done {
                continue;
            }
            let mut spent = 0;
            loop {
                if node.waiting {
                    let p = node.wiring.inp[node.cardiac.pc()];
                    let Some(card) = self.piles[p].pop_front() else { break };
                    node.cardiac.push(&[card]);
                    node.waiting = false;
                }
                let before = node.cardiac.steps();
                let mut punch = Punch { out: &node.wiring.out, piles: &mut self.piles, kinds: &mut self.kinds };
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

    /// Run every machine until none can go on.
    pub fn run(&mut self) {
        while self.round(u64::MAX) {}
    }

    /// Each machine's name and the instructions it has run (the loader's among them).
    pub fn steps(&self) -> Vec<(String, u64)> {
        self.nodes.iter().map(|n| (n.name.clone(), n.cardiac.steps())).collect()
    }

    /// The machines, and whether each has halted.
    pub fn halted(&self) -> Vec<(String, bool)> {
        self.nodes.iter().map(|n| (n.name.clone(), n.done)).collect()
    }
}
