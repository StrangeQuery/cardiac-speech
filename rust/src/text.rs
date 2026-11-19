//! Text to phonemes on CARDIACs: ASCII character cards in, phoneme cards out for the front end (10 x code +
//! stress, -1 between words, -2 to -5 pauses, -9 the end), as prototype/text_to_phonemes.py makes them.
//!
//! scan -> numd -> unpack -> year -> numw -> say3 -> ask -> numf -> spinfo -> spcls -> spell -> ask -> names ->
//! items -> excl, excx -> excp -> letters -> left, right -> first -> pick -> posta -> postb -> postc -> postd ->
//! join -> end, with small beside scan.
//!
//! What the host does, under the one-reader rule: it deals the text as each character's record of the ASCII table
//! (the character's code is the record's number), to small and to scan; it deals small's one card ahead of numf's
//! cards to spinfo; it fetches the record each of the two ask machines asks for (a number word's letters, a
//! letter's name) and deals it after the card it is for; it deals the function words and the exceptions again
//! after each item, to excl and excx, and fetches the exception's phonemes for excp; and for each letter it
//! fetches the letter's records of the three rule tables for left, right and pick, and deals left's and right's
//! verdicts side by side to first.
use std::rc::Rc;

use crate::net::{cards, Net, Program};

macro_rules! decks {
    ($($name:ident = $file:literal),* $(,)?) => {
        $(const $name: &str = include_str!(concat!("../machines/text/", $file, ".cqb"));)*
    };
}

decks! {
    SMALL = "small", SCAN = "scan", NUMD = "numd", UNPACK = "unpack", YEAR = "year", NUMW = "numw", SAY3 = "say3",
    ASK = "ask", NUMF = "numf", SPINFO = "spinfo", SPCLS = "spcls", SPELL = "spell", NAMES = "names", ITEMS = "items",
    EXCL = "excl", EXCX = "excx", EXCP = "excp", LETTERS = "letters", LEFT = "left", RIGHT = "right",
    FIRST = "first", PICK = "pick", POSTA = "posta", POSTB = "postb", POSTC = "postc", POSTD = "postd",
    JOIN = "join", END = "end",
}

/// The decks the text machines read: the hand-written version's (text/: ASCII, the number words, the letters'
/// names, the exceptions' phonemes), and this version's layout of the rules and the exceptions (rust/data/, made
/// from text/ by rust/tables.py).
pub struct Decks {
    pub ascii: Rc<Vec<i32>>,
    pub numbers: Rc<Vec<i32>>,
    pub letters: Rc<Vec<i32>>,
    pub exphon: Rc<Vec<i32>>,
    pub function: Rc<Vec<i32>>,
    pub exceptions: Rc<Vec<i32>>,
    pub left: Rc<Vec<i32>>,
    pub right: Rc<Vec<i32>>,
    pub phonemes: Rc<Vec<i32>>,
}

/// The rule tables' records: one a letter code, 0 to 26.
const LETTER_RECORDS: usize = 27;

impl Decks {
    pub fn load() -> Decks {
        let read = |t: &str| Rc::new(cards(t));
        Decks {
            ascii: read(include_str!("../../text/ascii.cards")),
            numbers: read(include_str!("../../text/numbers.cards")),
            letters: read(include_str!("../../text/letters.cards")),
            exphon: read(include_str!("../../text/exphon.cards")),
            function: read(include_str!("../data/function.cards")),
            exceptions: read(include_str!("../data/exceptions.cards")),
            left: read(include_str!("../data/left.cards")),
            right: read(include_str!("../data/right.cards")),
            phonemes: read(include_str!("../data/phonemes.cards")),
        }
    }
}

/// The text as cards: each character's ASCII code (anything that isn't ASCII a space). The host deals each as its
/// record of the ASCII table.
pub fn text_cards(text: &str) -> Vec<i32> {
    text.chars().map(|c| if c.is_ascii() { c as i32 } else { 32 }).collect()
}

/// Machine `name` reads its deck from pile `name<` and punches onto pile `name`.
fn machine(net: &mut Net, name: &str, deck: &str) {
    net.add(name, Program::Deck(deck), &format!("{name}<"), name);
}

/// Wire the text machines: character cards (`text_cards`) from `chars`, phoneme cards onto `out`. The text's piles
/// are named t_...
pub fn wire(net: &mut Net, d: &Decks, chars: &str, out: &str) {
    let records = d.ascii.len() / 128;
    // the text, each character as its record of the ASCII table, to small and to scan; each ends with a record whose
    // class is -1, dealt when the text is (`deal_text`)
    net.copy(chars, &["t_small?", "t_scan?"]);
    net.fetch("t_small?", &d.ascii, records, 0, records, "small<");
    net.fetch("t_scan?", &d.ascii, records, 0, records, "scan<");
    machine(net, "small", SMALL);
    machine(net, "scan", SCAN);
    net.copy("scan", &["numd<"]);
    machine(net, "numd", NUMD);
    net.copy("numd", &["unpack<"]);
    machine(net, "unpack", UNPACK);
    net.copy("unpack", &["year<"]);
    machine(net, "year", YEAR);
    net.copy("year", &["numw<"]);
    machine(net, "numw", NUMW);
    net.copy("numw", &["say3<"]);
    machine(net, "say3", SAY3);
    // ask: each number word's record of the numbers deck, dealt after it to numf
    net.put("ask1<", &[700]);
    net.copy("say3", &["ask1<"]);
    net.add("ask1", Program::Deck(ASK), "ask1<", "ask1");
    let number = d.numbers.len() / 31;
    net.fan("ask1", &["card", "rec"]);
    net.collate("t_nf?", &[("ask1>rec", 2, &[0])]);
    net.fetch("t_nf?", &d.numbers, number, 0, number, "t_nf");
    machine(net, "numf", NUMF);
    net.collate("numf<", &[("ask1>card", 2, &[1]), ("t_nf", number, &(0..number).collect::<Vec<_>>())]);
    // spinfo: small's card first, then numf's
    machine(net, "spinfo", SPINFO);
    net.merge("spinfo<", &[("small", 1), ("numf", 0)], &[]);
    net.copy("spinfo", &["spcls<"]);
    machine(net, "spcls", SPCLS);
    net.copy("spcls", &["spell<"]);
    machine(net, "spell", SPELL);
    // ask: each spelled letter's record of the letters deck, dealt after it to names
    net.put("ask2<", &[100]);
    net.copy("spell", &["ask2<"]);
    net.add("ask2", Program::Deck(ASK), "ask2<", "ask2");
    let letter = d.letters.len() / 27;
    net.fan("ask2", &["card", "rec"]);
    net.collate("t_ln?", &[("ask2>rec", 2, &[0])]);
    net.fetch("t_ln?", &d.letters, letter, 0, letter, "t_ln");
    machine(net, "names", NAMES);
    net.collate("names<", &[("ask2>card", 2, &[1]), ("t_ln", letter, &(0..letter).collect::<Vec<_>>())]);
    net.copy("names", &["items<"]);
    machine(net, "items", ITEMS);
    // the exceptions: each item with the function words after it, and with the exceptions after it
    const ITEM: usize = 17;
    net.fan("items", &["excl", "excx", "excp"]);
    machine(net, "excl", EXCL);
    net.merge("excl<", &[("items>excl", ITEM), ("deck:function", d.function.len())], &[("function", &d.function)]);
    machine(net, "excx", EXCX);
    net.merge("excx<", &[("items>excx", ITEM), ("deck:exceptions", d.exceptions.len())],
        &[("exceptions", &d.exceptions)]);
    net.fan("excx", &["excp", "ask"]);
    let exphon = 12;
    net.fetch("excx>ask", &d.exphon, exphon, 0, exphon, "t_xph");
    machine(net, "excp", EXCP);
    net.collate("excp<", &[("excl", 1, &[0]), ("excx>excp", 1, &[0]), ("items>excp", ITEM, &(0..ITEM).collect::<Vec<_>>()),
        ("t_xph", exphon, &(0..exphon).collect::<Vec<_>>())]);
    net.copy("excp", &["letters<"]);
    machine(net, "letters", LETTERS);
    // the rules: for each letter its records of the three tables
    const LETTER: usize = 19;
    net.fan("letters", &["left", "left?", "right", "right?", "pick", "pick?"]);
    let word: Vec<usize> = [1].into_iter().chain(4..LETTER).collect();
    for (name, deck, table) in [("left", LEFT, &d.left), ("right", RIGHT, &d.right)] {
        let size = table.len() / LETTER_RECORDS;
        net.collate(&format!("t_{name}w"), &[(&format!("letters>{name}"), LETTER, &word)]);
        net.collate(&format!("t_{name}?"), &[(&format!("letters>{name}?"), LETTER, &[0])]);
        net.fetch(&format!("t_{name}?"), table, size, 0, size, &format!("t_{name}r"));
        machine(net, name, deck);
        net.merge(&format!("{name}<"), &[(&format!("t_{name}w"), word.len()), (&format!("t_{name}r"), size)], &[]);
    }
    let rules = d.left.iter().filter(|&&c| c == -2).count() / LETTER_RECORDS;
    machine(net, "first", FIRST);
    net.put("first<", &[rules as i32]);
    net.merge("first<", &[("left", 1), ("right", 1)], &[]);
    let size = d.phonemes.len() / LETTER_RECORDS;
    let record: Vec<usize> = [1, 2, 3, 0].into_iter().chain(4..LETTER).collect();
    net.collate("t_pickw", &[("letters>pick", LETTER, &record)]);
    net.collate("t_pick?", &[("letters>pick?", LETTER, &[0])]);
    net.fetch("t_pick?", &d.phonemes, size, 0, size, "t_pickr");
    machine(net, "pick", PICK);
    net.merge("pick<", &[("t_pickw", LETTER), ("first", 1), ("t_pickr", size)], &[]);
    // stress and the joins
    net.copy("pick", &["posta<"]);
    machine(net, "posta", POSTA);
    net.copy("posta", &["postb<"]);
    machine(net, "postb", POSTB);
    net.copy("postb", &["postc<"]);
    machine(net, "postc", POSTC);
    net.copy("postc", &["postd<"]);
    machine(net, "postd", POSTD);
    net.copy("postd", &["join<"]);
    machine(net, "join", JOIN);
    net.copy("join", &["end<"]);
    machine(net, "end", END);
    net.copy("end", &[out]);
}

/// Deal the text: its characters onto `chars` (the host deals each as its record of the ASCII table), and after
/// them, to small and to scan, a record whose class is -1, the end.
pub fn deal_text(net: &mut Net, chars: &str, text: &str) {
    net.put(chars, &text_cards(text));
    for pile in ["small<", "scan<"] {
        net.put(pile, &[-1, 0]);
    }
}
