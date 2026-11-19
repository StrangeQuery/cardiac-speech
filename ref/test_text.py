"""The text machines' references composed, against text_to_phonemes.py."""
import text_ref as tr
import front_ref as fr
import sentences
import words

texts = sentences.MAIN + sentences.MORE + [w for w in words.WORDS] + [w.upper() for w in words.WORDS[:80]] + \
    [w.capitalize() for w in words.WORDS[80:160]] + ["It's 2026, and 7 dogs ate 1,000,000 bones.", "Call 911! Now.",
     "The year 1905 and 1900 and 1999; also 2000 and 1066: and 0 and 007 and 12345678.", "HELLO WORLD", "I AM BACK",
     "D W Hagelbarger", "MTV and nasa, R2D2.", "' tis", "don't stop", "Ask: why?", "Wow!!", "...", ""]

if __name__ == '__main__':
    bad = 0
    for t in texts:
        want = fr.tokens_of(' '.join(tr.tp.text_to_phonemes(t)))
        got = tr.compose(t)
        if got != want:
            bad += 1
            print(repr(t), got, want)
    print(len(texts), 'texts,', bad, 'differ')
