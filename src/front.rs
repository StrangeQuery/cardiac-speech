//! The front end: phoneme cards in, frame cards out, on 36 CARDIACs in three phases.
//!
//! 1. `feat` reads the phonemes and makes a record for each segment (and the pauses at the start and the end).
//! 2. The host puts the records in the opposite order, and `after`, `ahead` and `next` work out, last first, what
//!    lies ahead of each segment.
//! 3. The host puts those decks back in order, and the rest run forward, frame by frame, to the frame cards.
//!
//! The host deals each machine the cards (columns) of the decks it reads, collated into one pile a port; the
//! phoneme table and the filters are fetched by record number (`table`).
use std::rc::Rc;

use crate::net::Net;

macro_rules! listings {
    ($($name:ident = $file:literal),* $(,)?) => {
        $(pub const $name: &str = include_str!(concat!("../front/", $file));)*
    };
}

listings! {
    FEAT = "feat.cq", AFTER = "after.cq", AHEAD = "ahead.cq", NEXT = "next.cq", STRESS = "stress.cq",
    BASE = "base.cq", RULES2 = "rules2.cq", RULES9 = "rules9.cq", MUL = "mul.cq", NFRAMES = "nframes.cq",
    BACK = "back.cq", SUM = "sum.cq", FRAMER = "framer.cq", CLOSURE = "closure.cq", MAIN = "main.cq",
    EDGE = "edge.cq", CHOOSE = "choose.cq", GLIDES = "glides.cq", GLIDEA = "glidea.cq", GLIDEB = "glideb.cq",
    DECL = "decl.cq", RISE = "rise.cq", TAILY = "taily.cq", TAILF = "tailf.cq", PERIOD = "period.cq",
    LSEL = "lsel.cq", VSEL = "vsel.cq", PSEL = "psel.cq", MULX = "mulx.cq", GNORM = "gnorm.cq", KCARRY = "kcarry.cq",
    ASM = "asm.cq",
}

/// The phoneme table (one record of `FEAT` cards a phoneme code), the filters (11 cards each) and the glides'
/// level factors (a record of three cards a filter for each filter a segment glides from): precomputed once from the
/// published figures (ref/table.py), the only precomputed part.
pub const FEATURES: &str = include_str!("../front/features.cards");
pub const FILTERS: &str = include_str!("../front/filters.cards");
pub const GLIDE_TABLE: &str = include_str!("../front/glides.cards");
pub const FEAT_SIZE: usize = 17;
// the table's columns (ref/table.py)
const F_BACK: usize = 6;
const F_TS: usize = 7;
const F_ASP: usize = 9;
const F_VOICED: usize = 10;
const F_LOUD: usize = 14;
const F_CINH: usize = 15;

pub struct Tables {
    pub features: Rc<Vec<i32>>,
    pub filters: Rc<Vec<i32>>,
    pub glides: Rc<Vec<i32>>,
}

impl Tables {
    pub fn load() -> Tables {
        let read = |t: &str| Rc::new(heartburn::tape::values(t).expect("a table of cards"));
        Tables { features: read(FEATURES), filters: read(FILTERS), glides: read(GLIDE_TABLE) }
    }
}

// R1's columns: pc s wf pms send kind inh mn cls9 liq vls
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

/// Some columns of each record, in the order given.
fn cols(recs: &[Vec<i32>], c: &[usize]) -> Vec<i32> {
    recs.iter().flat_map(|r| c.iter().map(move |&i| r[i])).collect()
}

/// Several decks' columns side by side, a record of each at a time.
fn side(parts: &[(&[Vec<i32>], &[usize])]) -> Vec<i32> {
    let n = parts[0].0.len();
    let mut out = vec![];
    for i in 0..n {
        for (recs, c) in parts {
            out.extend(c.iter().map(|&k| recs[i][k]));
        }
    }
    out
}

/// Phase 1: phoneme cards in, a record of R1 cards a segment out.
pub fn segments(net: &mut Net, t: &Tables, tokens: &str, out: &str) {
    net.add("feat", FEAT, &[("cp", "f1t"), ("*", tokens)], &[("rec", "f1ask"), ("*", out)]);
    net.fetch("f1ask", &t.features, FEAT_SIZE, 0, 6, "f1t");
}

/// Phase 2: the segment records, last first, in; out what lies ahead of each segment, three decks: A (after imm
/// nvs), B (nextk pfw p1) and C (nxtpc adjv nextv ts te nts), last first.
pub fn ahead(net: &mut Net, t: &Tables, r1: &[i32]) {
    let rev: Vec<Vec<i32>> = records(r1, R1).into_iter().rev().collect();
    net.add("after", AFTER, &[("*", "pa")], &[("*", "aout")]);
    net.add("ahead", AHEAD, &[("*", "pb")], &[("*", "B")]);
    net.add("next", NEXT, &[("gts", "nt"), ("gte", "nt"), ("gasp", "nt"), ("*", "pc")], &[("ask", "nask"), ("*", "C")]);
    net.fetch("nask", &t.features, FEAT_SIZE, F_TS, 3, "nt");
    net.copy("aout", &["A", "a2b"]);
    net.put("pa", &cols(&rev, &[KIND, S, WF]));
    net.put("pb0", &cols(&rev, &[KIND, WF, CLS9]));
    net.collate("pb", &[("pb0", 3, &[0, 1, 2]), ("a2b", 3, &[0, 1])]);
    net.put("pc", &cols(&rev, &[PC, KIND]));
}

/// Phase 3: the segment records and what lies ahead of each (in order now) in; frame cards out onto `frames`.
pub fn frames(net: &mut Net, t: &Tables, r1: &[i32], a: &[i32], b: &[i32], c: &[i32], frames: &str) {
    let r1 = records(r1, R1);
    let rev = |d: &[i32], n: usize| -> Vec<Vec<i32>> { records(d, n).into_iter().rev().collect() };
    let (a, b, c) = (rev(a, 3), rev(b, 3), rev(c, 6));
    let (r1, a, b, c) = (&r1[..], &a[..], &b[..], &c[..]);
    net.add("stress", STRESS, &[("*", "st_in")], &[("*", "st")]);
    net.put("st_in", &side(&[(r1, &[KIND, S, WF]), (a, &[0, 1, 2]), (b, &[1])]));
    net.copy("st", &["st_base", "st_r2", "st_r9", "st_sum", "st_rise", "st_vsel"]);
    net.add("base", BASE, &[("*", "base_in")], &[("*", "xb")]);
    net.put("base_s", &cols(r1, &[KIND, INH, MN, PMS, VLS]));
    net.collate("base_in", &[("base_s", 5, &[0, 1, 2, 3, 4]), ("st_base", 4, &[0])]);
    net.add("rules2", RULES2, &[("*", "r2_in")], &[("*", "fa")]);
    net.put("r2_s", &side(&[(r1, &[KIND, WF, LIQ]), (a, &[0])]));
    net.put("r2_b", &cols(b, &[0]));
    net.collate("r2_in", &[("r2_s", 4, &[0, 1, 2, 3]), ("st_r2", 4, &[1, 2, 3, 0]), ("r2_b", 1, &[0])]);
    net.add("rules9", RULES9, &[("*", "r9_in")], &[("*", "fb")]);
    net.put("r9_s", &side(&[(r1, &[KIND]), (b, &[0, 2])]));
    net.collate("r9_in", &[("r9_s", 3, &[0, 1, 2]), ("st_r9", 4, &[2])]);
    net.add("mul", MUL, &[("la", "fa"), ("lb", "fb"), ("*", "xb")], &[("*", "dur")]);
    net.add("nframes", NFRAMES, &[("*", "nf_in")], &[("*", "n")]);
    net.put("nf_s", &cols(r1, &[KIND]));
    net.collate("nf_in", &[("nf_s", 1, &[0]), ("dur", 1, &[0])]);
    net.copy("n", &["n_sum", "n_fr", "n_cl", "n_ed", "n_ch", "n_gl", "n_decl", "n_rise", "n_ty", "n_ls", "n_vs"]);
    net.add("back", BACK, &[("*", "bk_in")], &[("*", "bk")]);
    net.put("bk_in", &side(&[(r1, &[PC, KIND, VLS]), (c, &[4])]));
    net.copy("bk", &["bk_ed", "bk_gl", "bk_ls"]);
    net.add("sum", SUM, &[("*", "sum_in")], &[("*", "sums")]);
    net.put("sum_s", &cols(r1, &[KIND, SEND]));
    net.collate("sum_in", &[("sum_s", 2, &[0, 1]), ("st_sum", 4, &[0]), ("n_sum", 1, &[0])]);
    net.copy("sums", &["sum_decl", "sum_ty"]);
    net.add("framer", FRAMER, &[("*", "fr_in")], &[("up", "u_rise"), ("ul", "u_vs"), ("*", "frm")]);
    net.put("fr_s", &cols(r1, &[SEND]));
    net.collate("fr_in", &[("n_fr", 1, &[0]), ("fr_s", 1, &[0])]);
    net.copy("frm", &["frm_ch", "frm_gl"]);
    net.add("closure", CLOSURE, &[("gci", "clt"), ("gct", "clt"), ("*", "cl_in")], &[("ask", "clask"), ("*", "cl")]);
    net.fetch("clask", &t.features, FEAT_SIZE, F_CINH, 2, "clt");
    net.put("cl_s", &cols(r1, &[PC, KIND]));
    net.collate("cl_in", &[("cl_s", 2, &[0, 1]), ("n_cl", 1, &[0])]);
    net.add("main", MAIN, &[("gv", "mnt"), ("gn", "mnt"), ("ga", "mnt"), ("gb", "mnb"), ("*", "mn_in")],
        &[("ask", "mnask"), ("askb", "mnaskb"), ("*", "mn")]);
    net.fetch("mnask", &t.features, FEAT_SIZE, F_VOICED, 3, "mnt");
    net.fetch("mnaskb", &t.features, FEAT_SIZE, F_BACK, 1, "mnb");
    net.put("mn_in", &side(&[(r1, &[PC, KIND]), (c, &[3, 4, 0])]));
    net.add("edge", EDGE, &[("g1", "edt"), ("g2", "edt"), ("g3", "edt"), ("g4", "edt"), ("g5", "edt"), ("*", "ed_in")],
        &[("ask", "edask"), ("*", "ed")]);
    net.fetch("edask", &t.features, FEAT_SIZE, F_ASP, 5, "edt");
    net.put("ed_s", &cols(r1, &[PC, KIND]));
    net.collate("ed_in", &[("ed_s", 2, &[0, 1]), ("n_ed", 1, &[0]), ("bk_ed", 4, &[2, 3])]);
    net.add("choose", CHOOSE, &[("fj", "ch_f"), ("fu", "ch_f"), ("fe", "ch_f"), ("*", "ch_s")],
        &[("ls", "sv"), ("lv", "sv"), ("*", "abug")]);
    net.collate("ch_s", &[("n_ch", 1, &[0]), ("cl", 1, &[0]), ("mn", 5, &[0, 1, 2, 3, 4]), ("ed", 2, &[0, 1])]);
    net.collate("ch_f", &[("frm_ch", 5, &[0, 1, 4])]);
    net.copy("sv", &["sv_ls", "sv_vs", "sv_ps", "sv_m1", "sv_kc"]);
    net.add("glides", GLIDES, &[("ca", "gl_f"), ("cb", "gl_f"), ("cu", "gl_f"), ("cg", "gl_f"), ("fl", "gl_f"),
        ("fr", "gl_f"), ("*", "gl_s")], &[("*", "kplan")]);
    net.put("gl_c", &cols(c, &[5]));
    net.collate("gl_s", &[("n_gl", 1, &[0]), ("bk_gl", 4, &[0]), ("gl_c", 1, &[0])]);
    net.collate("gl_f", &[("abug", 4, &[0, 1, 2, 3]), ("frm_gl", 5, &[2, 3])]);
    net.copy("kplan", &["kp_a", "kp_b", "kp_c"]);
    net.add("glidea", GLIDEA, &[("lp", "ga_x"), ("gg", "ga_x"), ("gb", "ga_y"), ("gb2", "ga_y"), ("*", "ga_in")],
        &[("aska", "gaska"), ("askb", "gaskb"), ("og", "gain"), ("*", "kp")]);
    net.fetch("gaska", &t.filters, 11, 0, 11, "ga_x");
    net.fetch("gaskb", &t.filters, 11, 0, 11, "ga_y");
    net.collate("ga_in", &[("kp_a", 6, &[0, 1, 2])]);
    net.add("glideb", GLIDEB, &[("lp", "gb_x"), ("gg", "gb_x"), ("gy", "gb_y"), ("gy2", "gb_y"), ("gk", "kp"),
        ("*", "gb_in")], &[("askn", "gbaskn"), ("asko", "gbasko"), ("*", "kq")]);
    net.fetch("gbaskn", &t.filters, 11, 0, 11, "gb_x");
    net.fetch("gbasko", &t.filters, 11, 0, 11, "gb_y");
    net.collate("gb_in", &[("kp_b", 6, &[3, 4, 5])]);
    let sum4 = [("gl", "sum_decl"), ("g2", "sum_decl"), ("g3", "sum_decl"), ("g4", "sum_decl"), ("*", "dc_s")];
    net.add("decl", DECL, &sum4, &[("*", "b0")]);
    net.put("dc_x", &cols(r1, &[SEND]));
    net.collate("dc_s", &[("n_decl", 1, &[0]), ("dc_x", 1, &[0])]);
    net.add("rise", RISE, &[("gu", "u_rise"), ("gb", "b0"), ("*", "rs_s")], &[("*", "b1")]);
    net.put("rs_k", &cols(r1, &[KIND]));
    net.collate("rs_s", &[("rs_k", 1, &[0]), ("st_rise", 4, &[0]), ("n_rise", 1, &[0])]);
    let sumy = [("gl", "sum_ty"), ("g2", "sum_ty"), ("g3", "sum_ty"), ("g4", "sum_ty"), ("*", "ty_s")];
    net.add("taily", TAILY, &sumy, &[("*", "ty")]);
    net.put("ty_x", &cols(r1, &[SEND]));
    net.collate("ty_s", &[("n_ty", 1, &[0]), ("ty_x", 1, &[0])]);
    net.add("tailf", TAILF, &[("gy", "ty"), ("ge", "ty"), ("*", "b1")], &[("*", "f0")]);
    net.add("period", PERIOD, &[("*", "f0")], &[("pa", "p_asm"), ("*", "p_ps")]);
    net.add("lsel", LSEL, &[("gs", "ls_f"), ("gv", "ls_f"), ("gl", "lst"), ("*", "ls_s")], &[("ask", "lsask"), ("*", "md1")]);
    net.fetch("lsask", &t.features, FEAT_SIZE, F_LOUD, 1, "lst");
    net.put("ls_k", &cols(r1, &[KIND]));
    net.put("ls_c", &cols(c, &[1]));
    net.put("ls_c2", &cols(c, &[2]));
    net.collate("ls_s", &[("ls_k", 1, &[0]), ("n_ls", 1, &[0]), ("ls_c", 1, &[0]), ("bk_ls", 4, &[1]), ("ls_c2", 1, &[0])]);
    net.collate("ls_f", &[("sv_ls", 2, &[0, 1])]);
    net.add("vsel", VSEL, &[("gs", "vs_f"), ("gv", "vs_f"), ("gu", "vs_f"), ("*", "vs_s")],
        &[("m3", "md3"), ("oy3", "md3"), ("*", "md2")]);
    net.put("vs_k", &cols(r1, &[KIND]));
    net.collate("vs_s", &[("vs_k", 1, &[0]), ("st_vsel", 4, &[0]), ("n_vs", 1, &[0])]);
    net.collate("vs_f", &[("sv_vs", 2, &[0, 1]), ("u_vs", 1, &[0])]);
    net.add("psel", PSEL, &[("*", "ps_f")], &[("*", "md4")]);
    net.collate("ps_f", &[("sv_ps", 2, &[0, 1]), ("p_ps", 1, &[0])]);
    net.add("mulx1", MULX, &[("gm", "md1"), ("gy", "md1"), ("*", "m1_in")], &[("*", "lv1")]);
    net.collate("m1_in", &[("sv_m1", 2, &[0, 1]), ("gain", 1, &[0])]);
    net.add("mulx2", MULX, &[("gm", "md2"), ("gy", "md2"), ("*", "lv1")], &[("*", "lv2")]);
    net.add("mulx3", MULX, &[("gm", "md3"), ("gy", "md3"), ("*", "lv2")], &[("*", "lv3")]);
    net.add("mulx4", MULX, &[("gm", "md4"), ("gy", "md4"), ("*", "lv3")], &[("*", "lv4")]);
    net.add("gnorm", GNORM, &[("gc", "gnt"), ("*", "gn_in")], &[("ask", "gnask"), ("*", "md5")]);
    let grec = 3 * t.filters.len() / 11;
    net.fetch("gnask", &t.glides, grec, 0, grec, "gnt");
    net.collate("gn_in", &[("kp_c", 6, &[3, 4, 5])]);
    net.add("mulx5", MULX, &[("gm", "md5"), ("gy", "md5"), ("*", "lv4")], &[("*", "lv5")]);
    net.add("kcarry", KCARRY, &[("frm", "kc_s"), ("gx", "kq"), ("*", "kself")], &[("pz", "kself"), ("wb", "kself"), ("*", "kout")]);
    net.collate("kc_s", &[("sv_kc", 2, &[0])]);
    net.add("asm", ASM, &[("gp", "p_asm"), ("gk", "kout"), ("*", "lv5")], &[("*", frames)]);
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
    let mut net = Net::new();
    ahead(&mut net, &t, &r1);
    net.run();
    let (a, b, c) = (net.take("A"), net.take("B"), net.take("C"));
    steps.extend(net.steps());
    let mut net = Net::new();
    frames(&mut net, &t, &r1, &a, &b, &c, "frames");
    net.run();
    steps.extend(net.steps());
    (net.take("frames"), steps)
}
