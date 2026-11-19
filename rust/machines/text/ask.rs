//! ask: first a card T; then a deck of cards in, and for each card two out: the number of the table record it asks
//! for, its last two digits when it is T or more (the number words are 700 + their record, a spelled letter 100 or
//! 200 + its code), else 0, and the card itself. The host fetches the record and deals it after the card to the
//! machine that needs it (numf, names).
use cardiac::*;

fn main() {
    let t = inp();
    loop {
        let c = inp();
        out(if c >= t { c % 100 } else { 0 });
        out(c);
    }
}
