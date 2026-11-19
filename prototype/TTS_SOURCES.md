# Sources for the rule-based text-to-speech front end

Files: `text_to_phonemes.py`, `phonemes_to_frames.py`, `tts.sh`, `tts_check.py`. No recording, no speech
synthesizer (macOS `say` included) and no outside code or pronunciation dictionary were used anywhere. All code
was written for this program. The papers below were read as scans, and every number was typed in by hand from
the printed tables.

## Primary sources

1. **H. S. Elovitz, R. W. Johnson, A. McHugh and J. E. Shore, *Automatic Translation of English Text to
   Phonetics by Means of Letter-to-Sound Rules*, NRL Report 7948, Naval Research Laboratory, 21 January 1976.**
   https://archive.org/details/DTIC_ADA021929 (the same report as DTIC ADA021929; apps.dtic.mil refused the
   download). The journal version is IEEE Trans. ASSP 24(6), 446–459, 1976.
   - All the letter-to-sound rules in `text_to_phonemes.py` (`RULES_TEXT`) come from Table 6 of the report
     (pp. 15–24, "version 3 of the rules"). That is 308 letter rules, typed in order from the page images,
     with the report's phoneme names (AA AE AH AO AW AX AY B CH D DH EH ER EY F G HH IH IY JH K L M N NX OW OY
     P R S SH T TH UH UW V W WH Y Z ZH).
   - The meaning of the special symbols (# * . $ % & @ ^ + : and blank) is from Table 2.
   - The matching algorithm follows pp. 4–5: scan left to right, try the current letter's rules in order,
     take the first rule that matches, emit its phonemes and skip the bracketed letters.
   - Two readings of the scan are mine. The printed "[OROUCH]" is read as OROUGH (thorough, borough), since
     C and G look alike in that font. In "' ^:[E] " the space after the apostrophe is ignored.
   - The report gives 319 rules for version 3 (Table 5), and that count includes six punctuation rules, so
     about 313 letter rules. I transcribed 308. I re-checked the edges of the page images, so either a few
     are missing from my transcription or the report counts them differently.

2. **D. H. Klatt, "Software for a cascade/parallel formant synthesizer", J. Acoust. Soc. Am. 67(3), 971–995,
   March 1980.** https://www.fon.hum.uva.nl/david/ba_shs/2009/klatt-1980.pdf
   - **Table II (vowels):** F1 F2 F3 B1 B2 B3, both rows (target and off-glide) for IY IH EY EH AE AA AO AH OW
     UH UW ER AY AW OY. ER is Klatt's [ɝ].
   - **Table III (consonants):**
     - W Y R L: F1–F3 and B1–B3.
     - F V TH DH S Z SH, the affricates CH JH and the plosives P B T D K G: F1–F3, B1–B3 and the parallel
       amplitudes A2 A3 A4 A5 A6 AB.
     - M N: FNP, FNZ, F1–F3, B1–B3.
     - The printed blank for [θ] A5 is taken as 0.
   - **Table I (typical constant values):**
     - F4 3300 / B4 250, F5 3750 / B5 200 and F6 4900 / B6 1000, used in every frame.
     - BNP 100.
     - The typical F1–F3 / B1–B3 of 450/1450/2450 and 50/70/110 are used for schwa (AX), which Table II
       does not list.
   - **Eq. 2, the digital resonator:** r = exp(−π B T), with angle 2π F T. Each formant becomes the pole pair
     1 − 2r cos θ z⁻¹ + r² z⁻².
   - **Text, Sec. V.B (rules taken from it):**
     - A prevocalic sonorant's AV is about 10 dB below the vowel.
     - [h] takes the following vowel's formants with B1 about 300 Hz and aspiration in place of voicing.
     - Voiceless fricatives use AF 60. Voiced fricatives use AF 50, AV 47 and AVS 47.
     - Before nonfront vowels the velars' A2 is about 60 dB.
     - The Table III F2 and F3 serve as loci, and the formant value at voicing onset lies between the locus
       and the vowel target.
     - The nasal pole sits at 270 Hz, and the nasal zero cancels F1.
   - **Sec. V.A:**
     - A stressed vowel's AV falls "by a few dB near the end of the syllable".
     - An isolated vowel's F0 falls linearly from 130 to 100 Hz.
   - **Sec. I.D and III (source spectra):**
     - The frication source is flat after the LPF and the radiation characteristic cancel, so the frication
       target is just the parallel resonators.
     - The voicing source falls about 12 dB/octave and radiation adds 6, a net −6 dB/octave. The
       synthesizer's 0.9 de-emphasis supplies that tilt, so voiced frames use formant poles only.

3. **D. H. Klatt, "Synthesis by rule of segmental durations in English sentences", Proc. 9th International
   Congress of Phonetic Sciences (Copenhagen, 1979), Symposium 5, pp. 290–297.**
   https://www.coli.uni-saarland.de/Phonetics/icphs/ICPhS1979/p9.2_290.pdf
   - **Table 1:** INHDUR and MINDUR in ms for every phoneme used here, including the affricates' closure
     and frication pairs. ER uses Klatt's RR ("bird").
   - **The model:** DUR = (INHDUR − MINDUR) × PRCNT / 100 + MINDUR, with PRCNT multiplied rule by rule.
   - **Rules implemented:**
     - 1: a 200 ms pause at a comma.
     - 2: clause-final lengthening, ×1.4.
     - 3: non-phrase-final shortening, ×0.6, and a phrase-final postvocalic liquid or nasal ×1.4.
     - 4: non-word-final shortening, ×0.85.
     - 5: polysyllabic shortening, ×0.8.
     - 6: non-initial consonant shortening, ×0.85.
     - 7: unstressed shortening (MINDUR/2, then ×0.5 or ×0.7 for syllabic segments, ×0.1 for a
       prevocalic liquid or glide, ×0.7 for the rest).
     - 9: postvocalic context: ×1.2, 1.6, 1.2, 0.85, 0.7 or 1.0, and 70 + 0.3 × PRCNT1 when not
       phrase-final.
     - 10: clusters: ×1.2, 0.7, 0.5, 0.7 and 0.7.
     - 11: +25 ms after an aspirated plosive.
   - **Stress features:** consonants before a stressed vowel in the same word are stressed, and function
     words carry no primary stress.
   - Rule 8 (emphasis) is not used.

4. **C. F. Sacia and C. J. Beck, "The Power of Fundamental Speech Sounds", Bell System Technical Journal 5(3),
   393–403, July 1926.** https://archive.org/details/bstj5-3-393
   - **Table V, column A** (mean conversational power, 16 speakers) sets each phoneme's output power:
     - AO 1870, AA 1380, OW 875, EY 808, EH 664, AH 616, UW 532, IY 484, ER 384, AE 366, IH 346.
     - N 84, M 74, SH 73, CH 58, S 38, Z 29, JH 19, NX 14, K 14, T 6, D 3, F 3, V 1.
   - **Column B** (peak power) is used only to fill in sounds missing from column A. See the estimates below.
   - Column A's L (13) is not used. Klatt's sonorant rule is used for W, Y, R and L instead.

## Supporting method (standard, not a numeric source)

- The autocorrelation method with Levinson's recursion, used to fit the order-10 all-pole filter to a
  frication spectrum, is the same one encode.py already uses. Reflection coefficients come from the step-down
  (backward Levinson) recursion with encode.py's sign convention. `phonemes_to_frames.step_down` was checked
  against `synth_float`'s lattice: the same filter run as a direct form and as the lattice gives identical
  impulse responses, to 3e-15.

## Estimated by me, not taken from a source

### Phoneme table gaps

- **NX formants:** Klatt's velar locus (the k/g row, F2 1990, F3 2850) with the n bandwidths and nasal pole.
- **ZH:** the SH row with a lower F1 and B1 (240 and 70), following Klatt's voiced-versus-voiceless pattern
  (z against s).
- **WH:** spoken as W.
- **Schwa (AX):** uses Klatt Table I's "typical" values, which are a neutral vowel rather than a measured
  schwa.

### Powers missing from Sacia and Beck column A

Each is column B scaled by a measured neighbour:

- UH 616 (ref AH).
- ZH 24 (ref SH).
- DH 5.5 (mean of the V and F references).
- G 18 (ref K).
- B and P 2.5 (ref T).
- TH 0.5 (ref F).

Vowels without their own entry:

- AY and AW use AA.
- OY uses AO.
- AX uses AH.

### How the spectra are built

- **Nasals:** the nasal pole replaces F1, and the zero is left out because the filter is all-pole.
- **Klatt's parallel amplitudes:** read as peak levels of peak-normalized analog resonances, summed in power
  with the bypass AB. Klatt's internal scaling constants were not used.
- **F6 (4900 Hz):** above the 4 kHz band, so only its skirt below 4 kHz counts. This makes /s/ fairly flat
  and weak at 8 kHz, with a measured centroid of about 2.5 kHz.
- **Voiced fricatives:** this synthesizer has one excitation per frame, so they use pulses through a fit of
  voicing (the cascade, peak set 3 dB under the frication peak, from AV 47 against AF 50) plus frication.

### Timing and levels

- **Stops:**
  - The closure is the Klatt duration minus one 25 ms burst frame, and the burst is one frame.
  - For p, t and k before a vowel or sonorant, the first frame of that segment becomes aspiration noise,
    at −14 dB against the vowel.
  - The burst carries the Sacia–Beck mean power × (INHDUR / 25 ms), on the assumption that the measured
    mean was spread over the whole consonant.
  - A b, d or g after a voiced sound has a voice bar (Klatt's F1 200 / B1 60) at power 1.5.
- **Formant transitions:** linear over 40 ms on each side of a boundary (capped at half the segment), from
  the halfway "virtual locus" between the neighbouring targets. Diphthongs move linearly from target to
  off-glide across the segment.
- **Vowel levels:**
  - An unstressed vowel is 3 dB down.
  - A vowel's level falls 3 dB from start to end, Klatt's "a few dB".
- **Silences and pads:** a voiced zero-gain frame ends a vowel, so the synthesizer's interpolation fades it
  out. An unvoiced zero-gain frame precedes a voiced onset, so the onset is not faded in. There is 50 ms of
  silence before the sentence and 150 ms after it.

### Prosody

- **Sentence F0:** Klatt's 130 → 100 Hz fall, applied across each sentence rather than one vowel.
- **Stress accents:** a stressed vowel's onset is raised by 15% (primary) or 7% (secondary), and the raise
  decays to 40% of that by the vowel's end.
- **Sentence ends:** from the last primary-stressed vowel on, F0 moves toward 85 Hz (statement) or 160 Hz
  (question).

### Letter-to-sound additions (not in the NRL report)

- **Stress heuristic:**
  - Primary stress goes on a content word's first vowel other than AX.
  - The other long vowels and diphthongs get secondary stress, except a word-final IY.
  - Function words get no stress.
- **Exception list:** written by hand, each entry checked by running the rules first:
  - HELLO is there for stress only.
  - The rest are pronunciation fixes: WANT(S), SAYS, BEEN, YOUR, ZERO, COMPUTER, MACHINE, WOMEN, DONE, GONE,
    FRIEND, SEVEN, ELEVEN, HUNDRED, THOUSAND, OKAY, LISTEN, OFTEN, and BROWN, DOWN, TOWN, COW, CROWN and
    POWER (the rules have [OW]=/OW/ only).
- **Doubled consonants:** collapsed (LITTLE gives T T in the rules).
- **Spelling out:**
  - Letter names are spelled out for an all-caps word of two or more letters. In an all-caps sentence,
    only all-caps words with no vowel are spelled.
  - The last letter takes primary stress and the others secondary.
- **Numbers:** read as number words.

## Sources looked up but not used

- **Peterson and Barney (1952), "Control methods used in a study of the vowels", JASA 24, 175–184.** I could
  not reach a readable copy of their Table II, so no Peterson–Barney numbers are used. All vowel formants are
  Klatt's Table II, which also gives bandwidths and off-glides.

## Pauses (changed 2026-11-18)

Klatt 1979 rule 1 gives 200 ms at a comma and none at a sentence end. After listening, we wanted clear pauses at commas and periods, so the pauses are now our choice, not sourced: 300 ms at a comma and 600 ms at a period, question mark or exclamation mark.
