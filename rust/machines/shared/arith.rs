// Decimal arithmetic the front end's machines share (included by the ones that use it), each as the reference
// ref/front_ref.py does it. A product of a card and a digit can pass a card, where the hand-written machines kept
// it in the accumulator's fourth digit, so here the card is split into its tens and units, and a digit's product
// is that many additions of each.
//
// Why not x * f / 100 and its like. First, these are not the same functions: each truncates at every shift, as
// the reference does, and the speech is checked sample for sample against the reference, so rounding once at the
// end would change frames. Second, a product of two cards can pass a card, which nothing on CARDIAC can hold.
// Third, rust-cardiac's multiply and divide routines are 53 to 62 of a program's 96 cells: mulf with a digit-split
// `*` is 124 cells and doesn't fit, and a plain Horner `*` fits (93 cells) but passes a card and runs ten times the
// instructions (395,664 against 39,931 for mul on the README's sentence). The machines that count by repeated
// addition or subtraction (rise, tailt, closure, period, psel) do it for the same reasons.

/// x f / 100 for a factor f in hundredths (front_ref.mulf): Horner over f's three digits a, b and c, truncating at
/// each shift: t = c x / 10, t = (t + b x) / 10, t + a x. x and f are 0 or more, and the product fits on a card.
/// Each step is d x1 + (t + d x0) / 10, with x = 10 x1 + x0, since d x can pass a card.
#[allow(dead_code)]
#[inline(never)]
fn mulf(x: i16, f: i16) -> i16 {
    let (x1, x0) = (x / 10, x % 10);
    let mut t = 0;
    let mut d = f % 10;
    for _ in 0..2 {
        let (mut tens, mut units) = (0, t);
        for _ in 0..d {
            tens += x1;
            units += x0;
        }
        t = tens + units / 10;
        d = f / 10 % 10;
    }
    for _ in 0..f / 100 {
        t += x;
    }
    t
}

/// x y / 1000 (front_ref.mul3): Horner over y's three digits, truncating at each shift, each step as in mulf. x
/// and y are 0 or more.
#[allow(dead_code)]
#[inline(never)]
fn mul3(x: i16, y: i16) -> i16 {
    let (x1, x0) = (x / 10, x % 10);
    let (mut t, mut g) = (0, y);
    for _ in 0..3 {
        let (mut tens, mut units) = (0, t);
        for _ in 0..g % 10 {
            tens += x1;
            units += x0;
        }
        t = tens + units / 10;
        g /= 10;
    }
    t
}

/// (x (10 - u) + y u) / 10, truncated toward zero (front_ref.blend): the glide from x to y, u in tenths, 0 to 10.
/// That is (10 s + e) / 10 with s = x + u (y / 10 - x / 10), which stays on a card, and e = u (y % 10 - x % 10).
/// 200 is added to e to keep it positive, so that carrying it into s gives the quotient rounded down; it is one
/// more when it is negative with units left over.
#[allow(dead_code)]
#[inline(never)]
fn blend(x: i16, y: i16, u: i16) -> i16 {
    let (dh, dl) = (y / 10 - x / 10, y % 10 - x % 10);
    let (mut s, mut e) = (x, 200);
    for _ in 0..u {
        s += dh;
        e += dl;
    }
    let mut q = s + e / 10 - 20;
    if q < 0 && e % 10 != 0 {
        q += 1;
    }
    q
}
