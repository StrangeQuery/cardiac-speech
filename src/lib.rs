//! Text to speech on CARDIACs. Every step of the computation is a CARDIAC program; the host only moves cards
//! between machines (`net`). The listings are in `voice/` (frame cards to samples), `front/` (phonemes to frame
//! cards) and `text/` (text to phonemes).
pub mod net;
pub mod voice;
