//! glides: a frame's wl and wr (from weights), its segment's pte and nts, and its filters a and b and whether it may
//! glide, g (from choose), in; out the filters gn and go it glides towards halfway at its segment's ends, and how far its own filter is
//! kept (w, 10 for no glide) (front_machines.f5_cframe). At the start the glide is towards the end filter of the
//! segment before, pte; at the end towards the start filter of the segment after, nts. With no glide, gn and go
//! are 0, so that the host fetches a record that is there (the glide table has records only for the filters a
//! frame glides from); glideb then keeps the frame's own filter, whatever they are.
use cardiac::*;

fn main() {
    loop {
        let wl = inp();
        let wr = inp();
        let pte = inp();
        let nts = inp();
        let a = inp();
        let b = inp();
        let gl = inp();
        let (mut gn, mut go, mut w) = (0, 0, 10);
        if gl > 0 {
            if wl > 0 && pte > 0 {
                (gn, go, w) = (pte, a, wl);
            } else if wr > 0 && nts > 0 {
                (gn, go, w) = (nts, b, wr);
            }
        }
        out(gn);
        out(go);
        out(w);
    }
}
