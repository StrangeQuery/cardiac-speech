//! spell: spcls's cards in; a word to be spelled out (ended by -11) out as its letters without apostrophes, each as
//! 100 + its code and the last as 200 + its code, then -11 (text_ref.spmark). Other words (ended by -10) and
//! anything else go through as they are. The word is held until its end card says which; letters past the 13th
//! are dropped (the rules take words of 13 letters at most).
use cardiac::*;

const APOSTROPHE: i16 = 27;

fn main() {
    let mut word = [0i16; 13];
    let (mut n, mut last) = (0, 0);
    loop {
        let c = inp();
        // a letter (1 to 26, or 27 an apostrophe) is the only card above 0 here
        if c > 0 {
            if n < 13 {
                word[n] = c;
                n += 1;
                if c < APOSTROPHE {
                    last = n;
                }
            }
            continue;
        }
        // what goes on each letter: nothing, or 100 (200 for the last) for a spelled word, which drops apostrophes
        // (-11 is the only card below -10 here)
        let mut add = 0;
        if c < -10 {
            add = 100;
        }
        for i in 0..n {
            let x = word[i];
            // after the last letter that isn't an apostrophe come only apostrophes
            if add < 1 || x < APOSTROPHE {
                out(x + if i + 1 >= last { add + add } else { add });
            }
        }
        out(c);
        n = 0;
    }
}
