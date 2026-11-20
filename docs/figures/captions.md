# Figures for the cardiac-speech paper

Made by docs/figures.py from the programs’ own output and the tables they read.

**Figure 1.** The system as four stages of CARDIAC programs, with the counts for the README sentence. Each program reads one deck of cards and punches one stream of cards; the host (shaded) only moves cards, dealing, copying, collating and merging them in fixed orders and fetching table records by number (dashed), and does no arithmetic on the speech. Text becomes 101 phoneme cards in 25 programs, the phonemes become 313 frames of 13 cards in 43 programs, 11 programs turn the frames into 62,600 samples at 8 kHz (each two cards, thousands and units), and 7 programs resample them to 375,600 samples at 48 kHz. Counts from talk -v, --phonemes and --frames (both versions, heartburn); docs/pipeline.svg shows every program.

`fig01-overview.svg`

**Figure 2.** The published methods this system draws on (green, joined to it) and the synthesizers that came from Klatt’s work (grey). Klatt’s work at MIT, which includes his duration rules (1979) and formant targets (1980), became MITalk, and from it came DECtalk and the CallText 5010 that gave Stephen Hawking his voice (Garcia 2018; Hallahan 1995). This system takes the NRL letter-to-sound rules (Elovitz et al. 1976) and Klatt’s rules for its front end, and an LPC lattice (Markel and Gray 1976) and polyphase interpolation (Crochiere and Rabiner 1983) for its back end. It also uses Sacia and Beck’s powers of speech sounds (1926), Bresenham’s running remainder (1965) for the fall of the pitch and Kaiser’s window (1974) for the second resampling filter. Years are those of the paper’s references, and DECtalk’s is the Computer History Museum’s dating.

`fig02-lineage.svg`

**Figure 3.** One reflection coefficient, K1, across two 25 ms frames of the README sentence, frames 90 and 91, in the AA of "was" (the pair of frames within a vowel with the largest change of K1 that is not a multiple of ten). Circles are the values on the frame cards the front end punched, and the green staircase is the value the voice box uses for each sample, as the ksteps program punched it. Each frame is ten steps of 20 samples. The first step holds the frame’s own value and each later step adds (next - this) / 10, formed by one SFT 01, which truncates toward zero. From 362 to 830 the step is 46 where the exact step is 46.8. The tenth step holds 776, and the next frame starts from its own card, 830. The dashed line is exact linear interpolation between the cards, for comparison. Data from talk --frames (heartburn) and from interp and ksteps run on ref/cardiac.py.

`fig03-tens.svg`

**Figure 4.** The letter codes of the text programs and the classes of the NRL rules. Letters are numbered 1 to 26 in the order A O U E I Y F H K P Q T S C X G J Z D L N R B M V W, so that each class a rule names is a range of codes; 27 is the apostrophe and 28 the edge of a word. The symbol above each column is the one the rules use (Elovitz et al. 1976), and the label under it its meaning; the blank matches the edge of a word or an apostrophe. The rules’ & and @ also match the pairs CH and SH (and @ also TH), which are written as separate rules. A rule’s ":" and "#" are counts on the same ranges (none or more consonants, one or more vowels). Testing a letter against a class is two subtractions and two conditional jumps. Ranges from ref/text_tables.py, which writes the rule decks.

`fig04-codes.svg`

**Figure 5.** A worked match of one NRL rule on the A of NAME in the README sentence. Above, the word as the text programs hold it, with an edge (28) on each side, and the rule that matched, ␣:[A]^+␣ = /EY/, its elements tested in turn. The left context is read leftwards from the letter before the bracket, and the right context rightwards from the bracket’s first letter. Each element is a count and a range of codes, and each test is the two comparisons shown. Below, the verdicts the left and right programs punched for each of the 34 rules of A at this letter (filled: the context matches); first chose rule 14, the first with both, outlined in red, and pick punched its phoneme EY. Data from the taps of talk on the README sentence (heartburn) and text/rules.cards.

`fig05-match.svg`

**Figure 6.** The inherent duration in the phoneme table of each of the 78 sounds of the README sentence (open circles; Klatt 1979), against the duration the mul program computed for it, (D_inh - D_min) P / 100 + D_min, after the rules’ factors (filled). Sounds are listed in order down the left column and then the right, under the words they belong to; ˈ marks primary and ˌ secondary stress. Of the sounds, 2 are lengthened (green line) and 76 shortened (grey line). The longest, OW at the end of "Hello" before the comma, takes the factors 140, 80 and 120, and lasts 271 ms against its inherent 220 ms. Pauses are omitted. Data from what the feat, rules2, rules5, rules9 and mul programs punched (talk on the README sentence under heartburn) and front/features.cards.

`fig06-durations.svg`

**Figure 7.** Spectral envelopes of filters from the phoneme table. Each curve is computed here in floating point as one pulse passes through the excitation’s low-pass (voiced filters only), the ten-stage lattice with the table’s reflection coefficients and the de-emphasis 0.9, times the filter’s gain. (a) The start targets of IY, AA and UW and the noise filter of S, each with its own gain. (b) The glide in the README sentence with the largest level factor, at frame 88 (2.200 s). The frame’s own filter (W start) is moved towards halfway to its neighbour’s (AY end) with weight 5 tenths, by blending the reflection coefficients as the glideb program punched them. With the own filter’s gain the blend is 13.4 dB quieter than the own filter (dashed red); the glide table’s factor 465, fetched by gnorm, restores it (green). Data from front/filters.cards and front/glides.cards and the taps of glides, glideb and gnorm (talk under heartburn).

`fig07-filters.svg`

**Figure 8.** The fundamental frequency of the README sentence, 8000 / P for each of its 272 voiced frames, from the pitch period P on the frame cards the front end punched (green; points 25 ms apart, at the frames’ centres). Shading marks the frames of vowels with primary stress (darker) and secondary stress (lighter), with each word named once above, where the rise program raises the pitch by 15 or 7 percent. The dashed line is the declination the decl program punched, 130 Hz falling towards 100 Hz across each sentence by Bresenham’s method; the second sentence starts again at 130 Hz. Each sentence ends with the fall towards 85 Hz. Data from talk --frames and the taps of feat, nframes and decl (heartburn).

`fig08-pitch.svg`

**Figure 9.** The excitation as the excite program punched it, one value a sample, for 20 ms in the middle of two sounds of the README sentence, the longest vowel and the longest voiceless fricative. (a) Voiced: a pulse of height A every P samples through the one-pole low-pass e = pulse + 0.5 e (formed as five ADDs and SFT 01, truncated toward zero), which leaves each pulse with a tail of halving values. (b) Unvoiced: +A or -A by the sign of x - 500, where x follows the generator x = 21 x + 7 mod 1000. P and A are those of the frame card; within a frame they move by tenths of the change to the next. Data from interp, steps and excite run on ref/cardiac.py on the frame cards of talk --frames; the values equal ref/voice_ref.py’s and the programs’ instruction counts equal heartburn’s.

`fig09-excitation.svg`

**Figure 10.** The ten-stage lattice as five CARDIAC programs of two stages each (dashed). The forward value f passes down the left rail and the backward value b up the right; stage i computes f(i-1) = f(i) - k(i) b(i-1) and b(i) = b(i-1) + k(i) f(i-1), where b(i-1) is from the sample before (z⁻¹). Stage 10’s b is never used, so L1 does not compute it. Between programs each sample crosses as two cards (marked in red at the first boundary): f down to the program below, and b back up to the program above for the next sample. Each program also reads ten coefficient cards every 20 samples, five for each of its stages. Wiring from src/voice.rs and voice/lattice_top.cq, lattice.cq and lattice_bottom.cq.

`fig10-lattice.svg`

**Figure 11.** The cells of one lattice program, voice/lattice.cq (L2, L3 and L4 run it), which fills 93 of the 97 cells a program has. The row of nine ADDs is cells 90 to 98, and it runs on into cell 99, where the JMP into it leaves the way back. The ten coefficient cards of each 20-sample step are read straight into the two multiply routines (orange, cells 47, 50, 52, 55, 63, 66, 68, 71, 75, 76). For each stage they are the sign word (±, ADD t or SUB t), the two jumps into the row for the coefficient’s digits (d2, d1), the final shift (SFT) and the rounding half (½), so the routines are rewritten every step. Cells and roles read from the listing; drawn by runcardiac’s memmap.py.

`fig11-lattice-cells.svg`

**Figure 12.** Spectrogram of the README sentence as the voice box produces it at 8 kHz, played at 48 kHz by repeating each sample six times, the simplest way a player can raise the rate. Repetition leaves images of the speech band reflected about every multiple of 8 kHz, so everything above 4 kHz (red line) is an artefact heard as tones and hiss over the voice. Hann windows of 1,024 samples (21 ms) every 240 samples (5 ms); levels relative to the loudest point of this figure and the next spectrogram. Data from talk (heartburn).

`fig12-spectrogram-8k.svg`

**Figure 13.** The frequency responses of the two resampling filters, computed from the coefficients in thousandths that the CARDIAC programs read (upsample/tables/fir1.cards and fir2.cards, which equal ref/up_table.py’s design), each divided by its gain. (a) Stage 1, the 159-tap least-squares low-pass at 16 kHz, is within 0.3 dB of flat to 3.8 kHz, 40.0 dB down at 4 kHz and at least 48.2 dB down from 4.5 kHz. (b) Stage 2, the 19-tap Kaiser-windowed sinc at 48 kHz, is at least 41.9 dB down from 12 to 24 kHz. (c) The two together, stage 1’s response repeating every 16 kHz at the 48 kHz rate. The dashed line marks 4 kHz, the top of the 8 kHz speech band.

`fig13-resampler-filters.svg`

**Figure 14.** Spectrogram of the README sentence as the 48 kHz version produces it, resampled by the seven CARDIAC programs, for comparison with the previous spectrogram, with the same analysis and the same reference level. For this sentence the energy from 4 to 24 kHz (above the red line) is -44.6 dB relative to 0 to 4 kHz, against -7.2 dB for the previous spectrogram (measured as in Figure 16), and most of what remains is the noise of the arithmetic’s rounding and truncation rather than images. Data from upsample/target/release/talk --no-hiband and talk --8k (heartburn).

`fig14-spectrogram-48k.svg`

**Figure 15.** The five operations of the host, each with one of its uses in this system. (a) It deals cards a fixed number at a time to several decks in turn. (b) It copies every card put on a pile onto several decks. (c) It collates whole records from fixed columns of several piles. (d) It merges several piles, taking a fixed number of cards from each in a fixed order, each pile waiting its turn. (e) It fetches the record of a table deck that a card names and puts that record in a deck, as a librarian fetches a book by its call number; record 48 is the first that gnorm asked for in the README sentence. None of the operations depends on what a card says, except the fetch, which uses it only as a record number. Uses from src/net.rs, src/front.rs, src/voice.rs and upsample/src/lib.rs.

`fig15-host.svg`

**Figure 16.** Images above 4 kHz. (a) The power spectrum of "All your base" averaged over the whole utterance (Hann windows of 4,096 samples, half overlapping), for the 48 kHz output of the CARDIAC resampler and for the same 8 kHz samples each repeated six times; shading marks 4 to 24 kHz, where the 8 kHz speech has nothing. (b) The energy from 4 to 24 kHz relative to 0 to 4 kHz for the paper’s three sample texts, as in the table of Section 7.2, which is -45.5, -43.6, -43.5 dB for the resampler (green) against -7.0, -6.9, -6.8 dB for repetition (grey). Measured by ref/up_measure.py on the output of upsample/target/release/talk --no-hiband and talk --8k (heartburn).

`fig16-images.svg`

**Figure 17.** CARDIAC instructions per second of speech for each stage, for the README sentence (7.83 s of speech; 352,382,024 instructions in all, loading included). The darker part of each bar is the programs that multiply by jumping into a row of ADDs. In the voice box they are the five lattice programs, 85 percent of its instructions and 79 percent of the whole 8 kHz pipeline’s, and in the resampler the two filter programs. Counts from talk -v --no-hiband of the 48 kHz version under heartburn.

`fig17-cost.svg`
