"""Where the programs the checks run are: the hand-written version's, in target/release, or with --rust on the
command line the Rust version's, in rust/target/release."""
import os
import sys

RUST = '--rust' in sys.argv
if RUST:
    sys.argv.remove('--rust')
# --all-rust: the Rust version's voice box with its hand-written machines replaced by Rust ones too (talk-frames'
# option), for comparing
EXTRA = []
if '--all-rust' in sys.argv:
    sys.argv.remove('--all-rust')
    EXTRA = ['--all-rust']
    RUST = True
RELEASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', *(['rust'] if RUST else []), 'target', 'release')
