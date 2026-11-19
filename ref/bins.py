"""Where the programs the checks run are: the hand-written version's, in target/release, or with --rust on the
command line the Rust version's, in rust/target/release."""
import os
import sys

RUST = '--rust' in sys.argv
if RUST:
    sys.argv.remove('--rust')
RELEASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', *(['rust'] if RUST else []), 'target', 'release')
