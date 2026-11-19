//! Text to phonemes on CARDIACs: ASCII character cards in, phoneme cards out for the front end (10 x code +
//! stress, -1 between words, -2 to -5 pauses, -9 the end), as prototype/text_to_phonemes.py makes them.
//!
//! scan -> numd -> unpack -> numw -> say3 -> ask -> numf -> spcls -> spell -> ask -> names -> items -> excl, excx ->
//! excp -> letters -> left, right -> first -> pick -> posta -> postb -> posth -> postc -> join
//!
//! What the host does, under the one-reader rule: it deals the text to scan twice, the second time each character
//! followed by its record of the ASCII table (the character's code is the record's number); it fetches the record
//! each of the two ask machines asks for (a number word's letters, a letter's name) and deals it after the card it
//! is for; it deals the function words and the exceptions again after each word's record, to excl and excx, and
//! fetches the exception's phonemes for excp; and for each letter it fetches the letter's records of the three rule
//! tables for left, right and pick, and deals left's and right's verdicts side by side to first.
use std::rc::Rc;

use crate::net::{cards, Net, Program};

macro_rules! listings {
    ($($name:ident = $file:literal),* $(,)?) => {
        $(pub const $name: &str = include_str!(concat!("../text/", $file));)*
    };
}

listings! {
    SCAN = "scan.cq", NUMD = "numd.cq", UNPACK = "unpack.cq", NUMW = "numw.cq", SAY3 = "say3.cq", ASK = "ask.cq",
    NUMF = "numf.cq", SPCLS = "spcls.cq", SPELL = "spell.cq", NAMES = "names.cq", ITEMS = "items.cq",
    EXCL = "excl.cq", EXCX = "excx.cq", EXCP = "excp.cq", LETTERS = "letters.cq", LEFT = "left.cq",
    RIGHT = "right.cq", FIRST = "first.cq", PICK = "pick.cq", POSTA = "posta.cq", POSTB = "postb.cq",
    POSTH = "posth.cq", POSTC = "postc.cq", JOIN = "join.cq",
}

/// The decks the text machines read, in text/ (made by ref/text_tables.py): the ASCII table, the number words, the
/// letters' names, the exceptions' phonemes, the function words and the exceptions, and the NRL rules as three
/// tables of one record a letter.
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
            ascii: read(include_str!("../text/ascii.cards")),
            numbers: read(include_str!("../text/numbers.cards")),
            letters: read(include_str!("../text/letters.cards")),
            exphon: read(include_str!("../text/exphon.cards")),
            function: read(include_str!("../text/function.cards")),
            exceptions: read(include_str!("../text/exception_words.cards")),
            left: read(include_str!("../text/rules_left.cards")),
            right: read(include_str!("../text/rules_right.cards")),
            phonemes: read(include_str!("../text/rules_phonemes.cards")),
        }
    }
}

/// The text as cards: each character's ASCII code (anything that isn't ASCII a space).
pub fn text_cards(text: &str) -> Vec<i32> {
    text.chars().map(|c| if c.is_ascii() { c as i32 } else { 32 }).collect()
}

/// Machine `name` runs `listing`, reading its deck from pile `name<` and punching onto pile `name`.
fn machine(net: &mut Net, name: &str, listing: &str) {
    net.add(name, Program::Listing(listing), &format!("{name}<"), name);
}

/// The letters' record for left or right: the letter's place i and the word.
const LETTER: usize = 19;

/// left or right: each letter's place and word (from letters's record), and after them the letter's record of the
/// machine's rule table, fetched by the record's first card.
fn rule_machine(net: &mut Net, name: &str, listing: &str, table: &Rc<Vec<i32>>) {
    let word: Vec<usize> = [1].into_iter().chain(4..LETTER).collect();
    let size = table.len() / LETTER_RECORDS;
    net.collate(&format!("t_{name}w"), &[(&format!("letters>{name}"), LETTER, &word)]);
    net.collate(&format!("t_{name}?"), &[(&format!("letters>{name}?"), LETTER, &[0])]);
    net.fetch(&format!("t_{name}?"), table, size, 0, size, &format!("t_{name}r"));
    machine(net, name, listing);
    net.merge(&format!("{name}<"), &[(&format!("t_{name}w"), word.len()), (&format!("t_{name}r"), size)], &[]);
}

/// Wire the text machines: the text (`deal_text`) onto the piles `chars` and `chars2`, phoneme cards onto `out`.
/// The text's piles are named t_...
pub fn wire(net: &mut Net, d: &Decks, chars2: &str, out: &str) {
    // scan: the text, then the text again with each character's ASCII record after it
    let records = d.ascii.len() / 128;
    machine(net, "scan", SCAN);
    net.copy(chars2, &["t_raw", "t_asc?"]);
    net.fetch("t_asc?", &d.ascii, records, 0, records, "t_asc");
    net.merge("scan<", &[("t_raw", 1), ("t_asc", records)], &[]);
    net.copy("scan", &["numd<"]);
    machine(net, "numd", NUMD);
    net.copy("numd", &["unpack<"]);
    machine(net, "unpack", UNPACK);
    net.copy("unpack", &["numw<"]);
    machine(net, "numw", NUMW);
    net.copy("numw", &["say3<"]);
    machine(net, "say3", SAY3);
    // ask: each number word's record of the numbers deck, dealt after it to numf
    net.put("ask1<", &[700]);
    net.copy("say3", &["ask1<"]);
    net.add("ask1", Program::Listing(ASK), "ask1<", "ask1");
    let number = d.numbers.len() / 31;
    net.split("ask1", &[("t_nf?", 1), ("t_nfc", 1)]);
    net.fetch("t_nf?", &d.numbers, number, 0, number, "t_nf");
    machine(net, "numf", NUMF);
    net.merge("numf<", &[("t_nfc", 1), ("t_nf", number)], &[]);
    net.copy("numf", &["spcls<"]);
    machine(net, "spcls", SPCLS);
    net.copy("spcls", &["spell<"]);
    machine(net, "spell", SPELL);
    // ask: each spelled letter's record of the letters deck, dealt after it to names
    net.put("ask2<", &[100]);
    net.copy("spell", &["ask2<"]);
    net.add("ask2", Program::Listing(ASK), "ask2<", "ask2");
    let letter = d.letters.len() / 27;
    net.split("ask2", &[("t_ln?", 1), ("t_lnc", 1)]);
    net.fetch("t_ln?", &d.letters, letter, 0, letter, "t_ln");
    machine(net, "names", NAMES);
    net.merge("names<", &[("t_lnc", 1), ("t_ln", letter)], &[]);
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
    let all = |n: usize| (0..n).collect::<Vec<_>>();
    net.collate("excp<", &[("excl", 1, &[0]), ("excx>excp", 1, &[0]), ("items>excp", ITEM, &all(ITEM)),
        ("t_xph", exphon, &all(exphon))]);
    net.copy("excp", &["letters<"]);
    machine(net, "letters", LETTERS);
    // the rules: for each letter its records of the three tables
    net.fan("letters", &["left", "left?", "right", "right?", "pick", "pick?"]);
    rule_machine(net, "left", LEFT, &d.left);
    rule_machine(net, "right", RIGHT, &d.right);
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
    net.copy("postb", &["posth<"]);
    machine(net, "posth", POSTH);
    net.copy("posth", &["postc<"]);
    machine(net, "postc", POSTC);
    net.copy("postc", &["join<"]);
    machine(net, "join", JOIN);
    net.copy("join", &[out]);
}

/// Deal the text: to scan, its characters and the end card -1; and onto `chars2`, the characters again (the host
/// deals each as its ASCII record after it), then -1 (the end, dealt to scan with no record after it).
pub fn deal_text(net: &mut Net, chars2: &str, text: &str) {
    let chars = text_cards(text);
    net.put("scan<", &chars);
    net.put("scan<", &[-1]);
    net.put(chars2, &chars);
    net.put("t_raw", &[-1]);
}
