"""Run front-end machine tests: run_tests.py f1 f2a ..."""
import sys
import front_ref as fr
import table as tb
import sentences
import test_front as T

fr.load(tb.C)
texts = sentences.MAIN + sentences.MORE
for w in sys.argv[1:]:
    print(w, 'exact' if getattr(T, 'test_' + w)(texts) else 'DIFFERENT')
