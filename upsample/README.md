# cardiac-speech at 48 kHz

This folder is the third version of cardiac-speech. It speaks at 48 kHz. The first version, in the folder above,
works the speech out at 8 kHz on its 79 machines, and here seven more CARDIACs upsample it six times, to 48 kHz,
with an interpolating low-pass filter. The 79 machines are the first version's own, run from its listings and decks
where they are, and under the 48 kHz speech their 8 kHz samples are the same sample for sample. Each machine has one
card reader and one punch, and the host still only deals, copies, collates, merges in fixed orders and fetches table
records. All the arithmetic on the sound is done on CARDIACs.

The reason for it is playback. A browser or a sound card that is handed 8 kHz audio resamples it to its own rate,
often 48 kHz, and many do it badly, leaving the images of the speech above 4 kHz as tones and hiss that the 8 kHz
speech doesn't have. Resampling on the host would be arithmetic on the sound, so it is done here on CARDIACs.

## Running it

You need [Rust](https://rustup.rs). The machines' decks are kept in the repository, so building the host needs
nothing else:

    cd upsample
    cargo build --release
    target/release/talk "Hello, my name is cardiac and I was born in 1968 to D W Hagelbarger. And now I can talk." \
        | ffplay -nodisp -autoexit -f s16le -ar 48000 -ch_layout mono -

The samples come out raw, as the first version's do, but 48,000 of them a second. To save them as a WAV file:

    echo "Hello world." | target/release/talk | ffmpeg -f s16le -ar 48000 -ac 1 -i - hello.wav

`talk` takes the first version's options, `--phonemes`, `--frames` and `-v`, and one more, `--8k`, which writes the
8 kHz samples underneath instead, the output stage's cards as the upsampler reads them. `talk-frames` reads frame
cards and writes the 48 kHz samples, and takes `--8k`, `--values` (the samples' pairs of values, one a line) and
`-v`. It is there for testing.

To change a Rust machine, you need [cargo-cardiac](https://crates.io/crates/cargo-cardiac) as well.
[`build_machines.sh`](build_machines.sh) compiles the three in [`machines/`](machines/) to their decks, next to
their sources, and writes their sizes to [`machines/cells.txt`](machines/cells.txt). The filter tables are made by
[`../ref/up_table.py`](../ref/up_table.py).

On this Mac (an Apple M5 Ultra) the sentence above, 7.83 seconds of speech, takes 0.58 seconds to work out, a
real-time factor of about 0.074, where the first version takes 0.084 seconds, about 0.011.

## How it works

The output stage of the first version puts each 8 kHz sample out as two values, the thousands and the units of
20 yd, where yd is the de-emphasis filter's output. `yd` turns each pair back into yd, which fits in a cell. yd is
50 thousands + units / 20, and since the sample is a multiple of 20 its units are too, so units / 20 is exactly
5 units / 100, five ADDs and SFT 02. It is the same yd the output stage worked with, so the upsampler starts from
the speech before it was scaled to 16 bits.

The upsampling is done in two stages, each a polyphase FIR filter. Stage 1, `fir1`, takes 8 kHz to 16 kHz. For each
8 kHz sample it puts out two 16 kHz samples, one from each half of its 39-tap filter (the even taps and the odd
taps, 20 and 19 of them), each the sum of a tap's coefficient times one of the last 20 samples. This is the filter
that has to be sharp, since the speech reaches up to 4 kHz and its images start just above. Stage 2, `fir2`, takes
16 kHz to 48 kHz. For each 16 kHz sample it puts out three 48 kHz samples from the three thirds of its 19-tap
filter. What it has to remove are the images around 16 kHz of speech that now stops at 4 kHz, which leaves it room,
so it can be short. Its filter is a sinc cut at a third of the band, which is zero at every third tap from its
centre, so one of its three phases is the centre tap alone, 1, and that 48 kHz sample is the 16 kHz sample itself.
The other two have six taps each.

`fir1` and `fir2` run the same listing, [`hand/fir.cq`](hand/fir.cq), with different decks. A CARDIAC has no
multiply instruction, so a tap multiplies as the lattice machines do, by jumping into a row of nine ADD
instructions, once for each decimal digit of its coefficient. A coefficient c is three digits and a sign, 0.d1 d2
d3, and a tap works out 10 c x, in tenths of a unit, by Horner's rule from the last digit, d3 times x, then SFT 01,
then plus d2 times x, SFT 01 again, and plus d1 times x. Each SFT truncates towards zero, and each digit's product
stays in the accumulator, whose four digits hold up to 9,999. A tap reads its sample and then five cards, which go
straight into its routine as instructions. The first is a sign word, ADD t or SUB t, that puts the sample or less
the sample in the row's cell. The second is for the third digit, and is CLA z for 0, nothing (SFT 00) for 1, and
otherwise a jump into the row for one ADD fewer than the digit, since the accumulator holds the sample once already
after the sign word. The next two jump into the row for each of the other two digits, or do nothing for a 0. The
last jumps on to the next tap, or after a phase's last tap to the routine that puts the sum out.

A tap's product can pass a card, and so can the sum, so the sum is kept as thousands and units, hi and lo. Each
product is added to lo, STO keeps the units, SFT 03 gives the carry, and the carry is added to hi. At the end of a
phase, `fir1` rounds the sum to whole units of yd, half away from zero, and puts it out as one card, a 16 kHz sample
in a cell. `fir2` puts out twice the sum, which is the 48 kHz sample, since the sum is in tenths of yd and the
sample is 20 yd. That passes a card, so it goes out as the output stage's samples do, the thousands and then the
units from 0 to 999, the units summed on top of 2000 so that they never go negative, and the host joins each pair
into a 16-bit sample. The phase that is the 16 kHz sample itself is a tap whose words are ADD t and three SFT 10,
which make ten times the sample, in tenths, with nothing to round.

The five cards of each tap are made from the filter's table by two machines, `digits` and `words`, before the
speech starts, once for each stage, as `reduce` makes the cards of the lattice's multiply routine from each K.
`digits` finds the sign and the three digits of each coefficient by counting down, and `words` turns them into
`fir`'s instructions. The host then deals their cards to `fir` again and again, a tap's five cards beside the tap's
sample.

## The filters

Both filters are designed once, offline, by [`../ref/up_table.py`](../ref/up_table.py), and kept as tables of
coefficients in thousandths, [`tables/fir1.cards`](tables/fir1.cards) and [`tables/fir2.cards`](tables/fir2.cards).

Stage 1 is a least-squares low-pass of 39 taps at 16 kHz, with a gain of 2, made to pass 0 to 3,300 Hz and to stop
4,000 to 8,000 Hz, the stopband weighted a hundred times the passband. In thousandths, as `fir1` has it, it is
within 0.4 dB of flat up to 3 kHz, 1.3 dB down at 3.3 kHz, 6 dB down at 3.53 kHz, 12.5 dB down at 3.7 kHz, 37.7 dB
down at 4 kHz, 45.8 dB down at 4.2 kHz, and at least 52.7 dB down from 4.5 kHz on. The cutoff is a little under
4 kHz because the speech has much of its energy close to 4 kHz (its fricatives), and an image of what is at 3.9 kHz
lands at 4.1 kHz, so the filter has to be well down by 4 kHz itself. It takes away some of the top of the band with
it, and the 48 kHz speech of the three texts below has 1.2 dB less power than the 8 kHz speech it is made from.

Stage 2 is a sinc cut at 8 kHz under a Kaiser window for 55 dB, 19 taps at 48 kHz, with a gain of 3. It is within
0.1 dB of flat up to 4 kHz and at least 41.9 dB down from 12 kHz to 24 kHz, where the images of stage 1's output
lie, and those images are of speech stage 1 has already cut off at 4 kHz.

## How the host feeds the machines

Each tap of a stage reads its own copy of the samples, as many as there are taps, 39 for `fir1` and 13 for `fir2`.
Every card `yd` punches goes onto each of `fir1`'s copies, and every card `fir1` punches onto each of `fir2`'s, and
each copy starts with as many blank cards as its tap's sample is old, as a delay line starts out empty. The host
merges a stage's deck in a fixed order, the first tap's copy for one card and the routine for five, the second tap's
copy for one card and the routine for five, and so on, round and round, the routine's cards dealt again each time
they run out. Nothing in this depends on what a card says.

The order of `fir2`'s phases is chosen so that each round of its deck starts with the newest sample, so a 16 kHz
sample m makes the 48 kHz samples 3 m + 1, 3 m + 2 and 3 m + 3. Otherwise the merge, after the last sample, would
start a round it couldn't finish, and the machine would put one sample too many out. The 48 kHz sample 0 is left out
(it would be the 16 kHz sample three before the first). So there are exactly six 48 kHz samples for each 8 kHz one,
and the 48 kHz speech comes 65 samples, 1.35 ms, after the 8 kHz speech it is made from. The filters' last 65
samples are not put out, and they are silence, since the speech ends with a pause.

## What each machine does

These are the seven machines the third version adds, after the first version's 79 (whose table is in the
[README](../README.md#what-each-machine-does) above). Cells are what `cargo cardiac build` reports for a Rust
machine and the cells a listing fills for a hand-written one. Instructions are counted by `talk -v` for "Hello, my
name is cardiac and I was born in 1968 to D W Hagelbarger. And now I can talk.", 62,600 samples at 8 kHz and 375,600
at 48 kHz (7.83 seconds), and include each machine's loading of its deck. The last column gives the count per 8 kHz
sample.

| Machine | Source | What it does | Cells | Instructions | Per sample |
|---|---|---|---:|---:|---:|
| digits1, digits2 | [machines/digits.rs](machines/digits.rs) | each coefficient of a table as its sign word and its three digits, counted down | 49 | 2,141 and 935 | |
| words1, words2 | [machines/words.rs](machines/words.rs) | the digits as the five cards of fir's routine | 86 | 1,803 and 755 | |
| yd | [machines/yd.rs](machines/yd.rs) | each 8 kHz sample's thousands and units back into yd | 21 | 1,189,463 | 19.0 |
| fir1 | [hand/fir.cq](hand/fir.cq) | 8 kHz to 16 kHz, two phases of 20 and 19 taps | 69 | 69,068,968 | 1,103.3 |
| fir2 | [hand/fir.cq](hand/fir.cq) | 16 kHz to 48 kHz, two phases of six taps and the sample itself, each 48 kHz sample out as thousands and units | 69 | 56,089,813 | 896.0 |
| | | **7 machines** | | **126,353,878** | **2,018.4** |

All together the 86 machines ran 169,832,986 instructions for 7.83 seconds of speech, about 21.7 million a second of
speech. The first version's 79 run 43,479,108 of them, 5.56 million a second, so the upsampler takes 74 percent of
the work, 16.1 million instructions a second of speech. That is 452 instructions for each 48 kHz sample, against
695 for each 8 kHz sample of the first version. A tap costs 17 instructions of reading, signing, shifting and
carrying, and as many ADDs as its digits add up to (one fewer for the third digit), so `fir1` runs about 28
instructions a tap and `fir2`, whose coefficients are larger, about 32.

The cards add up as well. The 86 programs load 11,624 program cards, and running the sentence the machines read
25,654,960 cards with INP, where the first version's read 1,115,392. Each 8 kHz sample is read once by each of
`fir1`'s 39 taps, and each of `fir1`'s by each of `fir2`'s 13, with five cards of the routine for each tap. They put
out 1,979,067 values with OUT.

## Written in Rust, or by hand

`yd`, `digits` and `words` are written in Rust, and compiled with rust-cardiac 0.2.5. `yd` compiles to what one
would write by hand, five ADDs and SFT 10 for 50 thousands, five ADDs and SFT 02 for the units, 19 instructions a
sample. `digits` and `words` run once, before the speech, and their size mattered more than their speed. Written as
one machine, finding the digits and making the words, they came to between 109 and 134 cells in the ways tried, past
the 96 a program has, so they are two.

`fir` is written by hand, for the reason the lattice is, and the numbers are of the same kind. Its multiply jumps
into a row of ADDs that the deck's cards point into, which Rust can't write. Written in Rust the plain way, a tap's
product, `v * d1 + (v * d2 + v * d3 / 10) / 10`, calls rust-cardiac's multiply routine three times, and it ran about
130 instructions a product (over a thousand random samples and digits), where `fir`'s row and shifts run 15 for the
same digits. The routine also keeps the product it builds in a cell, so a digit times a sample past 999 comes out
wrong (below). A whole stage written that way was 114 cells, too big to fit. A tap in Rust would have to look its
products up in a table made for each coefficient, as the Rust lattice's [kmul](../rust/machines/voice/kmul.rs) does,
and the Rust lattice took 1.8 times the hand-written one's instructions that way.

## What's precomputed

The two filters are worked out ahead of time, as the phoneme table is. Designing a low-pass needs cosines and the
solution of a set of linear equations (the least-squares design), or a sine and a Bessel function (the Kaiser
window), and none of it depends on the text, so it is done once, in floating point, and kept as cards in
thousandths. Each table is the stage's number, then two cards a tap, phase by phase, which are the coefficient and
then 1 for a phase's last tap or else 0, with 0 and 2 for the phase that is the sample itself. Everything from there
on, the cards of the routine, the products, the sums, the rounding and the samples, is worked out by CARDIACs.

## What it gives

[`../ref/up_measure.py`](../ref/up_measure.py) measures how much of the 48 kHz speech lies above 4 kHz, where the
8 kHz speech has nothing, as energy against the energy below 4 kHz, from a spectrum averaged over the whole
utterance. It sets the upsampler's output beside the same 8 kHz samples each repeated six times, the naive way to
make 48 kHz of them. For the three texts below, in dB:

| Text | Upsampler, 4-24 kHz | 4-4.5 kHz | 4.5-8 kHz | 8-24 kHz | Each sample six times, 4-24 kHz |
|---|---:|---:|---:|---:|---:|
| "All your base are belong to us. You have no chance to survive. Make your time." | -46.6 | -52.1 | -49.3 | -54.1 | -7.0 |
| "It doesn't have to be like this. All we need to do is make sure. we keep. talking." | -45.0 | -51.3 | -47.4 | -52.4 | -6.9 |
| "for millions of years, mankind lived just like the animals. ..." | -44.7 | -51.0 | -47.0 | -52.1 | -6.8 |

So the images are 45 to 47 dB below the speech, where repeating each sample leaves them 7 dB below. Most of what is
left above 4 kHz isn't images but the rounding. With each 16 kHz sample kept unrounded, the first text's figure
would be -50.8 dB, and with each product worked out exactly too, -52.5 dB, which is what the filters themselves
leave with their coefficients in thousandths. Rounding the 16 kHz samples to whole units of yd is what lets a
sample pass from `fir1` to `fir2` on one card.

## How it was checked

[`../ref/up_ref.py`](../ref/up_ref.py) is the upsampler's integer arithmetic in Python, the same products, sums,
truncations and rounding as the machines, and [`../ref/check_up.py`](../ref/check_up.py) checks every 48 kHz sample
against it, and every 8 kHz sample underneath (`--8k`) against [`voice_ref`](../ref/voice_ref.py):

    cd upsample && cargo build --release && cd ../ref
    python3 check_up.py

It runs `talk-frames` on the four frame files in [`../ref/fixtures/`](../ref/fixtures/), and `talk` on the three
texts of `make_wavs.py`, with the references end to end from the text (`text_ref`, `front_ref`, `voice_ref`, then
`up_ref`). On the day this README was written it found all seven exact, at 48 kHz and at 8 kHz.

## Compiler findings

Two things in rust-cardiac 0.2.5 came up while writing `digits` and `words`, besides their size. A function that
returns a pair is refused (RCE0003, "unsupported place"), and so is a call to one marked `#[inline(never)]` that
returns a value, so a routine shared by the three digits had to be written out three times. And a product of two
variables past what a card holds comes out wrong. With v = 600 and d = 9, `v * d / 10` gives 40, not 540, because
the multiply routine keeps the product it builds in a cell. A sum past a card in one expression stays in the
accumulator, as the first version's README says, but a product doesn't. `yd` multiplies only by constants, which
compile to rows of ADDs in the accumulator, and gives the right answers.

## Known limits

The first version's limits hold here too. The upsampler adds two of its own. yd and each 16 kHz sample have to fit
in a cell, so the 48 kHz samples are right while |yd| stays within 999, a sample of 19,980; the output stage allows
yd up to 1,638, but over the first version's test sentences and passages yd peaks at 621. And the speech is a little
duller than the 8 kHz speech played perfectly would be, since the filter is 6 dB down at 3.53 kHz.