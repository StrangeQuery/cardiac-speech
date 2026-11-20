# cardiac-speech at 48 kHz

This folder is the third version of cardiac-speech. It speaks at 48 kHz. The first version, in the folder above,
works the speech out at 8 kHz on its 79 machines, and here seven more CARDIACs upsample it six times, to 48 kHz,
with an interpolating low-pass filter, and three more add the high band of the fricatives, the hiss from 4 kHz up
that speech at 8 kHz can't carry. The 79 machines are the first version's own, run from its listings and decks
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

`talk` takes the first version's options, `--phonemes`, `--frames`, `--rate=N` and `-v`, and three more. `--8k` writes the
8 kHz samples underneath instead, the output stage's cards as the upsampler reads them. `--no-hiband` writes the
48 kHz samples without the high band, the upsampler's output alone. `--filters` prints the filter each frame speaks
through, one a line, as the front end's `choose` punches it, which is what the high band's levels are looked up by.
`talk-frames` reads frame cards and writes the 48 kHz samples, and takes `--8k`, `--values` (the samples' pairs of
values, one a line) and `-v`. Frame cards alone don't say which sound a frame is, so `talk-frames` adds no high band
unless it is given the frames' filters as well, with `--filters FILE`. It is there for testing.

To change a Rust machine, you need [cargo-cardiac](https://crates.io/crates/cargo-cardiac) as well.
[`build_machines.sh`](build_machines.sh) compiles the three in [`machines/`](machines/) to their decks, next to
their sources, and writes their sizes to [`machines/cells.txt`](machines/cells.txt). The filter tables are made by
[`../ref/up_table.py`](../ref/up_table.py).

On this Mac (an Apple M5 Ultra) the sentence above, 7.83 seconds of speech, takes 1.41 seconds to work out, a
real-time factor of about 0.18 (1.36 seconds without the high band), where the first version takes 0.084 seconds,
about 0.011.

## How it works

The output stage of the first version puts each 8 kHz sample out as two values, the thousands and the units of
20 yd, where yd is the de-emphasis filter's output. `yd` turns each pair back into yd, which fits in a cell. yd is
50 thousands + units / 20, and since the sample is a multiple of 20 its units are too, so units / 20 is exactly
5 units / 100, five ADDs and SFT 02. It is the same yd the output stage worked with, so the upsampler starts from
the speech before it was scaled to 16 bits.

The upsampling is done in two stages, each a polyphase FIR filter. Stage 1, `fir1`, takes 8 kHz to 16 kHz. For each
8 kHz sample it puts out two 16 kHz samples, one from each half of its 159-tap filter (the even taps and the odd
taps, 80 and 79 of them), each the sum of a tap's coefficient times one of the last 80 samples. This is the filter
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

Stage 1 is a least-squares low-pass of 159 taps at 16 kHz, with a gain of 2, made to pass 0 to 3,820 Hz and to stop
4,000 to 8,000 Hz, the stopband weighted a hundred times the passband. In thousandths, as `fir1` has it, it is
within 0.2 dB of flat up to 3.7 kHz, 0.3 dB down at 3.8 kHz, 6 dB down at 3.88 kHz, 8.2 dB down at 3.9 kHz, 40 dB
down at 4 kHz, 60.3 dB down at 4.2 kHz, and at least 48.2 dB down from 4.5 kHz on. The speech has much of its energy
close to 4 kHz (its fricatives): over the passage from the CARDIAC manual and the three texts below, 28 to 32
percent of it lies above 3 kHz, and 15 to 17 percent from 3.7 to 4 kHz. An image of what is at f lands at 8 kHz - f,
so the stopband starts at 4 kHz itself, and whatever the filter lets through below 4 kHz has its image in the
stopband. That leaves the band from 3.82 to 4 kHz for the filter to fall in, and the narrower the band, the more
taps it takes. With 99 taps the filter is flat to 3.5 kHz and 1 dB down at 3.7 kHz, with 139 it is flat to 3.7 kHz
and 2.6 dB down at 3.8 kHz, and with 159 it is within 0.3 dB to 3.8 kHz. The 48 kHz speech of the three texts below
has 0.25 dB less power than the 8 kHz speech it is made from.

In thousandths, each of the filter's two phases sums to exactly 1, so that a steady signal comes out of both the
same. Each tap rounded to the nearest thousandth, they would sum to slightly different amounts, and the difference
would put an image of the low frequencies at 8 kHz. So after rounding, [`up_table.py`](../ref/up_table.py) moves
taps by a thousandth until each phase sums to 1, each time the tap that the move takes least far from its exact
value, and a symmetric pair at a time, so that the filter stays symmetric. Stage 2's three phases sum to 1 the same
way.

Stage 2 is a sinc cut at 8 kHz under a Kaiser window for 55 dB, 19 taps at 48 kHz, with a gain of 3. It is within
0.1 dB of flat up to 4 kHz and at least 41.9 dB down from 12 kHz to 24 kHz, where the images of stage 1's output
lie, and those images are of speech stage 1 has already cut off at 4 kHz.

## How the host feeds the machines

Each tap of a stage reads its own copy of the samples, as many as there are taps, 159 for `fir1` and 13 for `fir2`.
Every card `yd` punches goes onto each of `fir1`'s copies, and every card `fir1` punches onto each of `fir2`'s, and
each copy starts with as many blank cards as its tap's sample is old, as a delay line starts out empty. The host
merges a stage's deck in a fixed order, the first tap's copy for one card and the routine for five, the second tap's
copy for one card and the routine for five, and so on, round and round, the routine's cards dealt again each time
they run out. Nothing in this depends on what a card says.

The order of `fir2`'s phases is chosen so that each round of its deck starts with the newest sample, so a 16 kHz
sample m makes the 48 kHz samples 3 m + 1, 3 m + 2 and 3 m + 3. Otherwise the merge, after the last sample, would
start a round it couldn't finish, and the machine would put one sample too many out. The 48 kHz sample 0 is left out
(it would be the 16 kHz sample three before the first). So there are exactly six 48 kHz samples for each 8 kHz one,
and the 48 kHz speech comes 245 samples, 5.1 ms, after the 8 kHz speech it is made from. The filters' last 245
samples are not put out, and they are silence, since the speech ends with a pause.

## The high band

The speech is worked out at 8 kHz, so none of it lies above 4 kHz, and much of a fricative's energy does. The voice
box's noise filters are fitted to Klatt's spectra below 4 kHz, so the hiss of an S is pushed up against 4 kHz, and
stage 1, which has to stop at 4 kHz to take out the images, takes the top of that hiss out with them. A word-final S
or Z is left with little, and "for millions of years" can be heard as "for millions of year".

Klatt's synthesizer gives its fricatives their high frequencies through its parallel branch [[Klatt
1980]](../README.md#references). A frication source, AF, drives formant resonators F2 to F6 set side by side, each at its own
amplitude, A2 to A6, and a bypass, AB, that passes the source on flat. His Table III gives the amplitudes of each
fricative, affricate and burst. S and Z excite only F6 (A6 52 dB), a resonance at 4,900 Hz, 1,000 Hz wide. F, V, P
and B excite only the bypass. TH and DH excite F6 and the bypass. SH and ZH excite F3 to F6, most strongly F3, CH
and JH F3 to F6 with most at F4, T F3 to F6 with most at F6, D with most at F5, and K and G F3 to F6 with most at
F3. A voiced fricative has the same
amplitudes as its voiceless cognate, and its frication source is 10 dB weaker, AF 50 dB against 60 dB. His
synthesizer ran at 10 kHz and so stopped at 5 kHz, but read as resonances, as the prototype reads them, his
formants and his bypass go on above it with the same shapes.

So the 48 kHz version works out a band of frication on CARDIACs, from the text, and adds it to the 48 kHz speech.
Three machines do it:

- **The level of each frame.** `choose`, in the front end, already says for every frame which filter it speaks
  through: a fricative's or an affricate's noise filter, a stop's burst filter in the burst's frame, the filter of a
  vowel, a sonorant or a voice bar, or 0 in a silent closure. The table
  [`tables/hiband.cards`](tables/hiband.cards) has a card for each filter of the phoneme table, record for record,
  which is 0 but for the noise filters, and the host fetches each frame's card by the filter's number, as it fetches
  the filters themselves. So vowels, sonorants, nasals, pauses, closures and aspiration (HH, and the breath after P,
  T and K) have no high band at all, and there the 48 kHz samples are the upsampler's own.
- **`hnoise`** ramps the level across each frame as `interp` and `steps` ramp A, in ten steps of 120 samples, each
  moving it on by (next - this) / 10, and not at all when the next frame's V differs. For each sample it puts out +L
  or -L by the sign of x - 500, where x runs through x = 21 x + 7 mod 1000, the decimal generator `excite` uses. At
  8 kHz that sequence repeats every eighth of a second, but at 48 kHz it would repeat every 21 ms, which is a 48 Hz
  buzz in the hiss. So at the start of each step x is moved on by w, which runs through the same generator once a
  step, and the noise no longer repeats. A step whose level is 0 puts out 0s.
- **`hfilt`** shapes the noise into the band. Three zeros at 0 Hz and two at 24 kHz, (1 - z^-1)^3 (1 + z^-1)^2, are
  e = s - s1 - 2 s2 + 2 s3 + s4 - s5, eight ADDs and SUBs, and two poles, y = e + 1.5 y1 - 0.9 y2, are a resonance at
  5.0 kHz, 0.8 kHz wide, close to Klatt's F6. 1.5 y1 is y1 + (5 y1) / 10 and 0.9 y2 is (9 y2) / 10, rows of ADDs and
  an SFT 01 that truncates towards zero. Measured on its output at a steady level, 73.5 percent of its power lies from
  4 to 8 kHz, its peak is at 4.96 kHz, and against the power from 4 to 8 kHz there is -18.1 dB below 4 kHz (-29.9 dB
  below 3 kHz), -15.7 dB from 4 to 4.5 kHz, -6.4 dB from 8 to 12 kHz and -9.4 dB from 12 to 24 kHz. A 0 in clears
  the filter and puts out 0, so nothing rings on into the next sound.
- **`hmix`** adds 4 y to each 48 kHz sample, the thousands and units as `fir2` puts them out, summed on top of 4000
  as `fir2` sums its units on top of 2000. The 48 kHz speech comes 245 samples after the 8 kHz speech, so the host
  deals 245 blank cards ahead of `hfilt`'s, and the band lines up with the frames it was made for.

The host's part is the same kind of bookkeeping as before. It fetches each frame's level by `choose`'s card, collates
each frame's V (the first card of its record) beside it, with one blank card after the last level for the frames'
end record, merges `hnoise`'s deck from those records and the same records from the second one on, two cards from
each in turn, as it merges `interp`'s, and merges `hmix`'s from `fir2`'s pairs and `hfilt`'s cards, two and one in
turn. `choose`'s cards are copied to one more pile for this, and the frame cards, and so the 8 kHz speech, are what
they were.

### The levels

The levels are worked out once, ahead of time, by [`../ref/hb_table.py`](../ref/hb_table.py), and kept in
`tables/hiband.cards`. For each voiceless sound and each burst it takes Klatt's frication spectrum, his parallel
resonances at their Table III amplitudes and his bypass, as the prototype reads them, and from it R, the energy from
4 to 8 kHz against the energy below 4 kHz. Below 4 kHz the 48 kHz speech already speaks the sound, so the level is
set so that the high band's energy from 4 to 8 kHz is R times the speech's below 4 kHz, measured over the sound's
frames in twelve texts (the four passages below and eight sentences for the sounds they have few of), with the
upsampler's arithmetic in Python. A first level comes from the high band's power at a steady level, and then the
level is corrected twice by measuring the band `hnoise` and `hfilt` really make in those texts, ramps and all, since
a burst ramps down towards the aspiration after it and gets less than a steady level would give.

A voiced fricative's speech band is mostly its voicing, which can't say how loud its frication is, so it takes
Klatt's rule instead: its level is its voiceless cognate's 10 dB down. The voiced stops' bursts are unvoiced in the
8 kHz speech, as the voiceless ones' are, and are set from Klatt's figures in the same way.

| Sound | Level | Klatt, 4-8 kHz against 0-4 kHz | Measured, 4-8 kHz against 0-4 kHz | High band below 4 kHz against the speech |
|---|---:|---:|---:|---:|
| S | 39 | 5.5 dB | 5.4 dB | -12.8 dB |
| T (burst) | 35 | 4.6 dB | 4.7 dB | -13.6 dB |
| D (burst) | 11 | 0.3 dB | 0.7 dB | -17.5 dB |
| F | 6 | 0.0 dB | -0.8 dB | -18.1 dB |
| TH | 3 | 0.0 dB | -1.5 dB | -18.0 dB |
| P (burst) | 17 | 0.0 dB | 0.0 dB | -18.3 dB |
| B (burst) | 10 | 0.0 dB | -0.5 dB | -17.4 dB |
| CH | 18 | -3.0 dB | -3.1 dB | -21.3 dB |
| G (burst) | 14 | -4.4 dB | -4.4 dB | -22.2 dB |
| K (burst) | 13 | -4.9 dB | -5.1 dB | -23.1 dB |
| SH | 13 | -7.2 dB | -7.2 dB | -24.8 dB |
| K before a back vowel | 7 | -9.6 dB | -9.0 dB | -26.4 dB |
| G before a back vowel | 8 | -9.3 dB | -9.9 dB | -26.8 dB |
| Z | 12 | S's level, 10 dB down | -7.6 dB | -25.3 dB |
| JH | 6 | CH's, 10 dB down | -15.8 dB | -32.8 dB |
| ZH | 4 | SH's, 10 dB down | -17.8 dB | -34.1 dB |
| V | 2 | F's, 10 dB down | -19.5 dB | -33.9 dB |
| DH | 1 | TH's, 10 dB down | -29.8 dB | -40.3 dB |

The measured columns are from [`../ref/hb_measure.py`](../ref/hb_measure.py), which runs `talk` with and without the
high band on the twelve texts and takes each sound's frames, 1,200 samples at 48 kHz each, 245 samples late, under a
Hann window. The voiceless sounds and bursts come within 1 dB of Klatt's figures, but for TH, at 1.5 dB, whose level
is 3 and can't be set finer. A voiced fricative's figure is low against its own speech band because that band is its
voicing. The last column is what the high band adds below 4 kHz, where its filter's skirt reaches: S's speech band
gains 0.2 dB, and the others' less. Over the twelve texts the high band's power is 14.3 dB below the speech's. For
the three texts of the table below, the energy from 4 to 24 kHz against 0 to 4 kHz over the whole utterance is now
-14.6, -14.4 and -15.9 dB, where the upsampler alone leaves -45.5, -43.6 and -43.5 dB.

The high band peaks at 2,440 (y at 610) over the four passages, where a card holds 999, and the samples at 10,680.

## What each machine does

These are the ten machines the third version adds, after the first version's 79 (whose table is in the
[README](../README.md#what-each-machine-does) above). Cells are what `cargo cardiac build` reports for a Rust
machine and the cells a listing fills for a hand-written one. Instructions are counted by `talk -v` for "Hello, my
name is cardiac and I was born in 1968 to D W Hagelbarger. And now I can talk.", 62,600 samples at 8 kHz and 375,600
at 48 kHz (7.83 seconds), and include each machine's loading of its deck. The last column gives the count per 8 kHz
sample.

| Machine | Source | What it does | Cells | Instructions | Per sample |
|---|---|---|---:|---:|---:|
| digits1, digits2 | [machines/digits.rs](machines/digits.rs) | each coefficient of a table as its sign word and its three digits, counted down | 49 | 5,541 and 935 | |
| words1, words2 | [machines/words.rs](machines/words.rs) | the digits as the five cards of fir's routine | 86 | 6,567 and 755 | |
| yd | [machines/yd.rs](machines/yd.rs) | each 8 kHz sample's thousands and units back into yd | 21 | 1,189,463 | 19.0 |
| fir1 | [hand/fir.cq](hand/fir.cq) | 8 kHz to 16 kHz, two phases of 80 and 79 taps | 69 | 251,609,842 | 4,019.3 |
| fir2 | [hand/fir.cq](hand/fir.cq) | 16 kHz to 48 kHz, two phases of six taps and the sample itself, each 48 kHz sample out as thousands and units | 69 | 56,089,813 | 896.0 |
| hnoise | [hand/hnoise.cq](hand/hnoise.cq) | each frame's high-band level ramped over its ten steps, and +L or -L for each 48 kHz sample | 85 | 2,826,514 | 45.2 |
| hfilt | [hand/hfilt.cq](hand/hfilt.cq) | the noise shaped into the band above 4 kHz: three zeros at 0 Hz, two at 24 kHz, and a resonance at 5.0 kHz | 73 | 6,970,021 | 111.3 |
| hmix | [hand/hmix.cq](hand/hmix.cq) | 4 y added to each 48 kHz sample, as thousands and units | 22 | 6,760,872 | 108.0 |
| | | **10 machines** | | **325,460,323** | **5,199.0** |

All together the 89 machines ran 368,942,687 instructions for 7.83 seconds of speech, about 47.1 million a second of
speech. The first version's 79 run 43,482,364 of them, 5.56 million a second, the upsampler's seven 308,902,916,
39.5 million a second, and the high band's three 16,557,407, 2.1 million a second, 4.5 percent of the whole. That is
982 instructions for each 48 kHz sample, against 695 for each 8 kHz sample of the first version. `hnoise` and
`hfilt` are cheap in the vowels and pauses, where `hnoise` puts out 0s for 6 instructions a sample and `hfilt`
passes them on for 15. In a fricative `hnoise` runs about 19 a sample and `hfilt` about 50, and `hmix` runs its 18
for every sample. Without the high band
(`--no-hiband`) the 86 machines run 352,385,280. A tap costs 17 instructions of reading, signing, shifting and
carrying, and as many ADDs as its digits add up to (one fewer for the third digit), so `fir1`, most of whose taps
are small, runs about 25 instructions a tap and `fir2`, whose coefficients are larger, about 32. `fir1` is 81
percent of the upsampler's work. With 39 taps, passing only to 3.3 kHz, it ran 69,068,968 instructions for this
sentence, and the whole sentence took 0.57 seconds, a real-time factor of 0.073.

The cards add up as well. The 89 programs load 12,008 program cards, and running the sentence the machines read
72,231,455 cards with INP, where the first version's read 1,115,393. Each 8 kHz sample is read once by each of
`fir1`'s 159 taps, and each of `fir1`'s by each of `fir2`'s 13, with five cards of the routine for each tap. They
put out 3,482,667 values with OUT, of which the high band's three put out 1,502,400. Without it the 86 read
70,727,800 and put out 1,980,267.

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

The high band's levels, [`tables/hiband.cards`](tables/hiband.cards), are worked out ahead of time too, by
[`../ref/hb_table.py`](../ref/hb_table.py) ([The levels](#the-levels)). Klatt's spectra need exponentials and a sum
over frequency, and the correction needs the speech measured over many texts, and none of it depends on the text
being spoken. The table is one card for each filter of the phoneme table, record for record, the level of a frame
that speaks through that filter. Which filter each frame speaks through, the ramps, the noise, the filter, the
delay and the sums are worked out by CARDIACs.

## What it gives

[`../ref/up_measure.py`](../ref/up_measure.py) measures how much of the 48 kHz speech lies above 4 kHz, where the
8 kHz speech has nothing, as energy against the energy below 4 kHz, from a spectrum averaged over the whole
utterance. It sets the upsampler's output beside the same 8 kHz samples each repeated six times, the naive way to
make 48 kHz of them. These figures are for the upsampler alone (`talk --no-hiband`), since the high band puts
energy above 4 kHz on purpose ([The high band](#the-high-band) gives the figures with it). For the three texts
below, in dB:

| Text | Upsampler, 4-24 kHz | 4-4.5 kHz | 4.5-8 kHz | 8-24 kHz | Each sample six times, 4-24 kHz |
|---|---:|---:|---:|---:|---:|
| "All your base are belong to us. You have no chance to survive. Make your time." | -45.5 | -49.6 | -49.2 | -52.9 | -7.0 |
| "It doesn't have to be like this. All we need to do is make sure. we keep. talking." | -43.6 | -47.1 | -47.5 | -52.0 | -6.9 |
| "for millions of years, mankind lived just like the animals. ..." | -43.5 | -47.1 | -47.3 | -51.8 | -6.8 |

So the images are 43 to 46 dB below the speech, where repeating each sample leaves them 7 dB below. Most of what is
left above 4 kHz isn't images but the arithmetic. With each 16 kHz sample kept unrounded, the first text's figure
would be -47.8 dB, and with each product worked out exactly too, -53.4 dB, which is what the filters themselves
leave with their coefficients in thousandths. With the products exact and the 16 kHz samples rounded it would be
-48.4 dB. Rounding the 16 kHz samples to whole units of yd is what lets a sample pass from `fir1` to `fir2` on one
card, and each tap's product is truncated to tenths of a unit by its SFTs, so with 159 taps the truncations add up
to about as much as the rounding. With the 39-tap filter of before, which passed only to 3.3 kHz, the figures were
-46.6, -45.0 and -44.7 dB, and the 48 kHz speech had 1.2 dB less power than the 8 kHz speech.

The coefficients are kept in thousandths because a finer step would buy nothing that can be heard. With its
coefficients exact the filter would leave -54.7 dB for the first text, against -53.4 dB in thousandths, both well
under the -45.5 dB that the arithmetic leaves, and a fourth digit would take a sixth card and another jump into the
row for every tap.

## How it was checked

[`../ref/up_ref.py`](../ref/up_ref.py) is the upsampler's integer arithmetic in Python, the same products, sums,
truncations and rounding as the machines, and the high band's too (`hnoise`, `hfilt` and `hmix`, the levels taken
from `front_ref`'s own record of each frame's noise filter). [`../ref/check_up.py`](../ref/check_up.py) checks every
48 kHz sample against it, and every 8 kHz sample underneath (`--8k`) against [`voice_ref`](../ref/voice_ref.py):

    cd upsample && cargo build --release && cd ../ref
    python3 check_up.py            # the fixtures and the three texts
    python3 check_up.py --long     # and the four passages of the previews, a minute and a half more

It runs `talk-frames` on the four frame files in [`../ref/fixtures/`](../ref/fixtures/), which have no high band, and
`talk` on the three texts of `make_wavs.py`, with the references end to end from the text (`text_ref`, `front_ref`,
`voice_ref`, then `up_ref`), checking each text's 48 kHz samples with the high band and without it
(`--no-hiband`). On the day this README was written it found all seven exact, at 48 kHz with and without the high
band and at 8 kHz, and with `--long` the four passages of the manual, "for millions of years", "It doesn't have to
be like this" and "All your base" as well, 2,755,200 samples at 48 kHz. The first version's checks (`check_text`,
`check_front`, `check_voice` and `make_wavs`) still find everything exact, since the frame cards are the same.

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
duller than the 8 kHz speech played perfectly would be, since the filter is 6 dB down at 3.88 kHz, and the speech
has 5 to 6 percent of its energy from 3.85 to 4 kHz.

The high band has limits of its own. It has one shape for every sound, Klatt's F6 near 5 kHz, where his SH and K put
most of their frication lower, at F3 and F4, and his F and TH spread theirs flat; only its level follows the sound.
Its level is fixed for each sound. An unvoiced fricative's A in the 8 kHz speech is fixed too, but a voiced
fricative's moves with its pitch period, and its high band doesn't follow that. The weakest sounds' levels are small whole numbers (DH 1, V 2, TH 3), so
they are only as fine as a step of 1 can make them. Between 3.9 and 4.5 kHz both the speech and the high band are
weak, the speech because stage 1 cuts it off there and the high band because its filter rises from 4 kHz. And y has
to fit in a cell, which it does with 4.3 dB to spare at the loudest S of the four passages.