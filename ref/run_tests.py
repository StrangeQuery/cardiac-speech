"""Run the front-end machine tests: run_tests.py checks every machine on the 23 test sentences; run_tests.py feat
glidea ... the ones named (test_front.MACHINES; rules is rules2, rules5 and rules9 together)."""
import sys
import front_ref as fr
import table as tb
import sentences
import test_front as T

fr.load(tb.C)
texts = sentences.MAIN + sentences.MORE
names = sys.argv[1:] or T.MACHINES
for n, ok in T.test(texts, names).items():
    print(n, 'exact' if ok else 'DIFFERENT')
