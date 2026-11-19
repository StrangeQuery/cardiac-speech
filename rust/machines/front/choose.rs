//! choose: a frame's j, u and last (from framer), and its segment's c, ma, mb, uon, vm, gl, cf and af, in; out the
//! two target filters a and b it glides between by uu tenths, whether it sounds (snd: 1 sounding, 0 silent, 9 the
//! very last frame), whether it is voiced (V), and whether it may glide at its segment's ends (g: gl, for a frame
//! that speaks through ma and mb) (front_machines.f5_cframe). A closure frame speaks through cf (or is
//! silent), a breathy first frame through af, and the rest through ma and mb, gliding when uon.
use cardiac::*;

fn main() {
    loop {
        let j = inp();
        let u = inp();
        let last = inp();
        let c = inp();
        let ma = inp();
        let mb = inp();
        let uon = inp();
        let vm = inp();
        let gl = inp();
        let cf = inp();
        let af = inp();
        let (mut a, mut b, mut uu, mut voiced, mut snd, mut g) = (ma, mb, 0, vm, 1, gl);
        if j < c {
            (a, b, voiced, g) = (cf, cf, 1, 0);
            if cf < 1 {
                snd = if last > 0 { 9 } else { 0 };
            }
        } else if j < 1 && af > 0 {
            (a, b, voiced, g) = (af, af, 0, 0);
        } else if uon > 0 {
            uu = u;
        }
        out(a);
        out(b);
        out(uu);
        out(snd);
        out(voiced);
        out(g);
    }
}
