//! first: first how many rules each letter has a verdict for; then for each letter, left's and right's verdicts on
//! each rule side by side (1 a context matches, 0 not) in; out the number of the first rule whose contexts both
//! match (text_ref.match_word: the first rule that matches wins), -1 if none does.
use cardiac::*;

fn main() {
    let rules = inp();
    loop {
        let mut chosen = -1;
        for r in 0..rules {
            let both = inp() + inp();
            if chosen < 0 && both > 1 {
                chosen = r;
            }
        }
        out(chosen);
    }
}
