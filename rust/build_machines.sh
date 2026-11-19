#!/bin/sh
# Build every machine written in Rust (machines/*/NAME.rs) to its deck, machines/*/NAME.cqb, with rust-cardiac's
# `cargo cardiac build` (cargo install cargo-cardiac, then cargo cardiac setup), and write each one's size in cells
# to machines/cells.txt. The decks are kept in the repository, so that the host (cargo build --release here) needs
# only Rust; run this after changing a machine. It also remakes the rule decks in data/ from text/ (tables.py).
set -e
here=$(cd "$(dirname "$0")" && pwd)
python3 "$here/tables.py" > /dev/null
cd "$here/machines"
cargo cardiac build --release 2>&1 | tee build.log | grep -v "^ *Compiling" | grep -v " 1 phase, " || true
grep -o "^[a-z]*/[a-z0-9_]*\.rs: 1 phase, [0-9]* cells" build.log \
    | sed 's|^\([a-z]*\)/\([a-z0-9_]*\)\.rs: 1 phase, \([0-9]*\) cells|\1/\2 \3|' | sort > cells.txt
rm build.log
count=$(wc -l < cells.txt | tr -d ' ')
echo "$count machines built, sizes in machines/cells.txt"
