//! Text to phonemes on 19 CARDIACs: ASCII character cards in (the text dealt twice, each time ended by -1),
//! phoneme cards out for the front end (10 x code + stress, -1 between words, -2 to -5 pauses, -9 the end), as
//! tools/lpc/text_to_phonemes.py makes them.
//!
//! scan -> numd -> numw -> say3 -> numf -> spcls -> spell -> names -> excl -> excp -> loader -> filter -> rule ->
//! posta -> postb -> postc -> join, with two ctx machines beside loader and rule for the NRL rules' contexts.
//! The decks they read (text/*.cards) are transcriptions of text_to_phonemes.py's tables and of ASCII.
use std::rc::Rc;

use crate::net::Net;

macro_rules! listings {
    ($($name:ident = $file:literal),* $(,)?) => {
        $(pub const $name: &str = include_str!(concat!("../text/", $file));)*
    };
}

listings! {
    SCAN = "scan.cq", NUMD = "numd.cq", NUMW = "numw.cq", SAY3 = "say3.cq", NUMF = "numf.cq", SPCLS = "spcls.cq",
    SPELL = "spell.cq", NAMES = "names.cq", EXCL = "excl.cq", EXCP = "excp.cq", LOADER = "loader.cq",
    FILTER = "filter.cq", RULE = "rule.cq", CTX = "ctx.cq", POSTA = "posta.cq", POSTB = "postb.cq",
    POSTC = "postc.cq", JOIN = "join.cq",
}

pub struct Decks {
    pub ascii: Rc<Vec<i32>>,
    pub numbers: Rc<Vec<i32>>,
    pub letters: Rc<Vec<i32>>,
    pub exceptions: Rc<Vec<i32>>,
    pub exphon: Rc<Vec<i32>>,
    pub rules: Rc<Vec<i32>>,
}

impl Decks {
    pub fn load() -> Decks {
        let read = |t: &str| Rc::new(heartburn::tape::values(t).expect("a deck of cards"));
        Decks {
            ascii: read(include_str!("../text/ascii.cards")),
            numbers: read(include_str!("../text/numbers.cards")),
            letters: read(include_str!("../text/letters.cards")),
            exceptions: read(include_str!("../text/exceptions.cards")),
            exphon: read(include_str!("../text/exphon.cards")),
            rules: read(include_str!("../text/rules.cards")),
        }
    }
}

/// The text as cards: each character's ASCII code, then -1, twice (scan reads it through twice).
pub fn text_cards(text: &str) -> Vec<i32> {
    let once: Vec<i32> = text.chars().map(|c| if c.is_ascii() { c as i32 } else { 32 }).chain([-1]).collect();
    [once.clone(), once].concat()
}

/// Wire the text machines: character cards from `chars`, phoneme cards onto `out`.
pub fn wire(net: &mut Net, d: &Decks, chars: &str, out: &str) {
    net.add("scan", SCAN, &[("gc", "t_asc"), ("gv", "t_asc"), ("*", chars)], &[("ask", "t_aska"), ("*", "t1")]);
    net.fetch("t_aska", &d.ascii, 2, 0, 2, "t_asc");
    net.add("numd", NUMD, &[("gb", "t_nd"), ("gs", "t_nd"), ("*", "t1")], &[("keep", "t_nd"), ("*", "t2")]);
    net.add("numw", NUMW, &[("*", "t2")], &[("*", "t3")]);
    net.add("say3", SAY3, &[("*", "t3")], &[("*", "t4")]);
    net.add("numf", NUMF, &[("gf", "t_nf"), ("*", "t4")], &[("ask", "t_askn"), ("*", "t5")]);
    net.fetch("t_askn", &d.numbers, 10, 0, 10, "t_nf");
    net.add("spcls", SPCLS, &[("*", "t5")], &[("*", "t6")]);
    net.add("spell", SPELL, &[("gp", "t_sp"), ("gp2", "t_sp"), ("*", "t6")], &[("keep", "t_sp"), ("*", "t7")]);
    net.add("names", NAMES, &[("gn", "t_ln"), ("*", "t7")], &[("ask", "t_askl"), ("*", "t8")]);
    net.fetch("t_askl", &d.letters, 8, 0, 8, "t_ln");
    net.add("excl", EXCL, &[("gw", "t_xl"), ("gy", "t_xl"), ("gz", "t_xl"), ("gd", "t_xdeck"), ("*", "t8")],
        &[("keep", "t_xl"), ("kw", "t_xl"), ("ky", "t_xl"), ("*", "t9")]);
    net.cycle("t_xdeck", &d.exceptions);
    net.add("excp", EXCP, &[("gw", "t_xp"), ("gp", "t_xph"), ("*", "t9")], &[("keep", "t_xp"), ("ask", "t_askx"), ("*", "t10")]);
    net.fetch("t_askx", &d.exphon, 12, 0, 12, "t_xph");
    net.add("loader", LOADER, &[("ga", "t_adv"), ("*", "t10")], &[("let", "t_wl"), ("lend", "t_wl"), ("el", "t_pl"),
        ("pl1", "t_pl"), ("pl2", "t_pl"), ("er", "t_pr"), ("pr1", "t_pr"), ("pr2", "t_pr"), ("*", "t_flt")]);
    net.copy("t_wl", &["t_wl_l", "t_wl_r"]);
    net.add("filter", FILTER, &[("gd", "t_rdeck"), ("fwd", "t_rdeck"), ("*", "t_flt")], &[("*", "t_rin")]);
    net.cycle("t_rdeck", &d.rules);
    net.add("rule", RULE, &[("vd", "t_vl"), ("gr", "t_vr"), ("*", "t_rin")], &[("ol", "t_cl"), ("dl", "t_cl"),
        ("or", "t_cr"), ("dr", "t_cr"), ("al", "t_adv"), ("no", "t_adv"), ("*", "t11")]);
    net.add("ctxl", CTX, &[("gw", "t_wl_l"), ("lett", "t_pl"), ("gdir", "t_pl"), ("*", "t_cl")], &[("*", "t_vl")]);
    net.add("ctxr", CTX, &[("gw", "t_wl_r"), ("lett", "t_pr"), ("gdir", "t_pr"), ("*", "t_cr")], &[("*", "t_vr")]);
    net.add("posta", POSTA, &[("*", "t11")], &[("*", "t12")]);
    net.add("postb", POSTB, &[("gy", "t_pb"), ("gw", "t_pb"), ("*", "t12")], &[("keep", "t_pb"), ("*", "t13")]);
    net.add("postc", POSTC, &[("*", "t13")], &[("*", "t14")]);
    net.add("join", JOIN, &[("*", "t14")], &[("*", out)]);
}
