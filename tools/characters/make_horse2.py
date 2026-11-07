"""High-detail procedural horse: muscled body, arched neck, sculpted head with eyes/ears/nostrils, hair-strand mane, forelock and tail,
jointed legs with hooves and shoes, saddle tack.  Skeleton: root(pelvis) > chest > neck > head, tail > tail2, 4 legs x 3 bones.
Clips: idle, walk, run (gallop with spine flex), turn_left, turn_right.   python3 make_horse2.py outdir"""
import sys, math, numpy as np
sys.path.insert(0, '/tmp/mh2')
from mhlib import *

H = {'root': (0, 1.2, -0.45), 'chest': (0, 1.25, 0.3), 'neck': (0, 1.34, 0.86), 'head': (0, 1.80, 1.27), 'tail': (0, 1.33, -1.0), 'tail2': (0, 1.0, -1.15),
     'fl_u': (0.17, 1.05, 0.62), 'fl_l': (0.17, 0.6, 0.62), 'fl_h': (0.17, 0.2, 0.63),
     'fr_u': (-0.17, 1.05, 0.62), 'fr_l': (-0.17, 0.6, 0.62), 'fr_h': (-0.17, 0.2, 0.63),
     'hl_u': (0.18, 1.08, -0.7), 'hl_l': (0.18, 0.64, -0.8), 'hl_h': (0.18, 0.2, -0.72),
     'hr_u': (-0.18, 1.08, -0.7), 'hr_l': (-0.18, 0.64, -0.8), 'hr_h': (-0.18, 0.2, -0.72)}
P = {'root': None, 'chest': 'root', 'neck': 'chest', 'head': 'neck', 'tail': 'root', 'tail2': 'tail'}
for s in ('fl', 'fr'): P[s + '_u'] = 'chest'; P[s + '_l'] = s + '_u'; P[s + '_h'] = s + '_l'
for s in ('hl', 'hr'): P[s + '_u'] = 'root'; P[s + '_l'] = s + '_u'; P[s + '_h'] = s + '_l'
BONES = list(H.keys())

COATS = {
    'bay':      dict(body=(0.36, 0.19, 0.095), dark=(0.06, 0.045, 0.04), mane=(0.05, 0.04, 0.035), belly=1.18, socks=0.0, blaze=1),
    'chestnut': dict(body=(0.5, 0.235, 0.09), dark=(0.38, 0.17, 0.07), mane=(0.62, 0.36, 0.17), belly=1.12, socks=1.0, blaze=1),
    'black':    dict(body=(0.07, 0.065, 0.06), dark=(0.05, 0.045, 0.04), mane=(0.04, 0.04, 0.04), belly=1.4, socks=0.0, blaze=0),
    'grey':     dict(body=(0.66, 0.67, 0.7), dark=(0.38, 0.38, 0.4), mane=(0.82, 0.82, 0.84), belly=1.0, socks=0.0, blaze=0),
}


def noise(p, f=14.0):
    return (math.sin(p[0] * f * 1.3 + p[1] * f * 0.7) * math.sin(p[2] * f + p[1] * f * 1.9) + 1) * 0.5


def make_caparison_tex(outdir):
    import os
    from PIL import Image, ImageDraw
    os.makedirs(outdir + '/tex', exist_ok=True)
    W, Hh = 1024, 640
    img = Image.new('RGB', (W, Hh), (172, 20, 28)); d = ImageDraw.Draw(img)
    gold = (236, 184, 60); dk = (120, 10, 18)
    # woven pattern
    for y in range(0, Hh, 8):
        d.line([(0, y), (W, y)], fill=(165, 18, 26), width=1)
    for x in range(0, W, 8):
        d.line([(x, 0), (x, Hh)], fill=(180, 24, 32), width=1)
    # borders (hem = u edges, front/back = v edges)
    bw = 34
    for k, (c, w) in enumerate(((gold, bw), (dk, 22))):
        off = sum(q[1] for q in ((gold, bw), (dk, 22))[:k])
        d.rectangle([off, 0, off + w, Hh], fill=c); d.rectangle([W - off - w, 0, W - off, Hh], fill=c)
        d.rectangle([0, off, W, off + w], fill=c) if k == 0 else d.rectangle([0, off, W, off + w], fill=c)
        d.rectangle([0, Hh - off - w, W, Hh - off], fill=c)
    d.rectangle([84, 84, W - 84, Hh - 84], outline=gold, width=5)
    # heraldic emblem on both flanks: ring + cross + corner studs
    for cx in (int(W * 0.24), int(W * 0.76)):
        cy = Hh // 2
        d.ellipse([cx - 120, cy - 120, cx + 120, cy + 120], fill=dk, outline=gold, width=10)
        d.ellipse([cx - 92, cy - 92, cx + 92, cy + 92], outline=gold, width=4)
        d.rectangle([cx - 14, cy - 96, cx + 14, cy + 96], fill=gold); d.rectangle([cx - 96, cy - 14, cx + 96, cy + 14], fill=gold)
        for ang in range(8):
            import math as _m
            px = cx + 108 * _m.cos(ang * _m.pi / 4); py = cy + 108 * _m.sin(ang * _m.pi / 4); d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=gold)
    # diamond lattice (stitching) around
    for gx in range(1, 9):
        for gy in range(1, 5):
            x = gx * W // 9; y = gy * Hh // 5
            if min(abs(x - W * 0.24), abs(x - W * 0.76)) > 150: d.polygon([(x, y - 14), (x + 14, y), (x, y + 14), (x - 14, y)], outline=gold)
    img.save(outdir + '/tex/caparison_c.png')
    Image.new('RGB', (W, Hh), (0, 205, 0)).save(outdir + '/tex/caparison_mr.png')
    Image.new('RGB', (W, Hh), (128, 128, 255)).save(outdir + '/tex/caparison_n.png')


def build(coat, name, outdir):
    C = COATS[coat]
    M = Model(BONES, P, H); M.body_rough = 0.5
    body = np.array(C['body']); dark = np.array(C['dark'])

    def coatcol(p):
        # dapple + lighter belly/inner legs, dark lower legs / muzzle
        shade = 0.93 + 0.1 * noise(p)
        c = body * shade
        if p[1] < 0.95 and p[1] > 0.0 and (abs(p[0]) > 0.0): pass
        k = float(np.clip((0.62 - p[1]) / 0.3, 0, 1))
        if C['socks'] > 0.5 and p[1] < 0.3 and p[2] > 0.0: c = np.array((0.9, 0.88, 0.82)) * 0.95
        else: c = c * (1 - k) + dark * k
        if p[1] < 1.0 and p[1] > 0.84 and abs(p[0]) < 0.2 and -0.8 < p[2] < 0.9: c = c * C['belly']
        return np.clip(c, 0, 1)

    # ------------------------------------------------------------ torso (barrel, croup, shoulder, chest)
    sec = [(-1.04, 1.31, 0.05, 0.06), (-1.0, 1.31, 0.17, 0.2), (-0.9, 1.32, 0.255, 0.285), (-0.75, 1.33, 0.295, 0.335), (-0.55, 1.32, 0.29, 0.35),
           (-0.3, 1.27, 0.27, 0.36), (-0.05, 1.22, 0.275, 0.375), (0.2, 1.2, 0.285, 0.385), (0.45, 1.22, 0.295, 0.385), (0.68, 1.27, 0.285, 0.365),
           (0.86, 1.33, 0.25, 0.33), (0.98, 1.38, 0.19, 0.27), (1.05, 1.42, 0.1, 0.18), (1.08, 1.43, 0.02, 0.05)]
    rings = [ring_xy((0, cy, z), rxv, ryv) for z, cy, rxv, ryv in sec]
    Vb, Fb = loft(rings, 26, True, True)
    def body_w(p):
        z = p[2]
        if z > 0.1:
            t = min((z - 0.1) / 0.4, 1.0)
            if z > 0.9: n_ = min((z - 0.9) / 0.18, 1.0) * 0.7; return [('chest', 1 - n_ * 0.4 - 0.0), ('neck', n_ * 0.4)] if n_ > 0 else [('chest', 1.0)]
            return [('chest', t), ('root', 1 - t)] if t < 1 else [('chest', 1.0)]
        if z < -0.95: return [('root', 0.8), ('tail', 0.2)]
        return [('root', 1.0)]
    pass

    # muscle masses: hindquarter, gaskin, shoulder, forearm, neck-base, gluteal
    def blob(c, r, bone=None, wfn=None, nseg=14, sq=1.0):
        Vv, Ff = lathe([(0.001, -r[1]), (r[0] * 0.7, -r[1] * 0.75), (r[0], -r[1] * 0.25), (r[0], r[1] * 0.25), (r[0] * 0.7, r[1] * 0.75), (0.001, r[1])], nseg, (0, 0, 0), 1)
        Vv = Vv * np.array([1.0, 1.0, r[2] / r[0]]) + np.array(c)
        return Vv, Ff
    for sg in (-1, 1):
        for c_, r_, bn in (((sg * 0.23, 1.03, -0.72), (0.14, 0.27, 0.2), 'root'),                            ((sg * 0.23, 1.18, 0.6), (0.1, 0.22, 0.17), 'chest'),                            ((sg * 0.18, 1.27, -0.88), (0.1, 0.1, 0.15), 'root')):
            pass

    # ------------------------------------------------------------ neck (arched crest)
    nk = [((0, 1.36, 0.84), 0.19, 0.31), ((0, 1.46, 0.95), 0.165, 0.275), ((0, 1.58, 1.05), 0.14, 0.235), ((0, 1.7, 1.14), 0.118, 0.2), ((0, 1.79, 1.22), 0.1, 0.17), ((0, 1.84, 1.28), 0.088, 0.14)]
    rings = [ring_perp(c, (0, 0.8, 0.5), rxv, ryv) for c, rxv, ryv in nk]; rings_neck = rings
    Vn, Fn = loft(rings, 18, False, False)
    def neck_w(p):
        t = float(np.clip((p[1] - 1.36) / 0.45, 0, 1))
        if t < 0.35: return [('chest', 1 - t / 0.35 * 0.5), ('neck', t / 0.35 * 0.5)]
        if t > 0.85: return [('neck', 1 - (t - 0.85) / 0.15 * 0.4), ('head', (t - 0.85) / 0.15 * 0.4)]
        return [('neck', 1.0)]
    pass

    # ------------------------------------------------------------ head (poll -> muzzle)
    hd = [((0, 1.84, 1.27), 0.07, 0.09), ((0, 1.8, 1.31), 0.095, 0.125), ((0, 1.72, 1.375), 0.105, 0.15), ((0, 1.64, 1.44), 0.1, 0.15),
          ((0, 1.57, 1.51), 0.08, 0.12), ((0, 1.515, 1.585), 0.06, 0.1), ((0, 1.485, 1.65), 0.066, 0.095), ((0, 1.47, 1.7), 0.058, 0.07), ((0, 1.465, 1.725), 0.03, 0.03)]
    rings = [ring_perp(c, (0, -0.8, 0.6), rxv, ryv) for c, rxv, ryv in hd]; rings_head = rings
    Vh, Fh = loft(rings, 20, True, True)
    blaze = C['blaze']
    def headcol(p):
        c = coatcol((p[0], 1.6, p[2]))
        if p[2] > 1.6 and p[1] < 1.56: c = np.array((0.32, 0.22, 0.2)) if coat != 'black' else np.array((0.08, 0.07, 0.07))   # muzzle
        if p[2] > 1.68: c = c * 0.65
        if blaze and abs(p[0]) < 0.028 and p[2] > 1.33 and p[1] > 1.5: c = np.array((0.95, 0.93, 0.88))
        return c
    pass
    # jaw / cheek mass, nostrils, eyes, brow, ears, lips
    for sg in (-1, 1):
        Vv, Ff = blob((sg * 0.07, 1.6, 1.43), (0.06, 0.1, 0.09)); M.add('body', Vv, Ff, colfn=lambda p: coatcol((p[0], 1.6, p[2])), bone='head')
        Vv, Ff = blob((sg * 0.03, 1.49, 1.715), (0.015, 0.02, 0.015)); M.add('body', Vv, Ff, color=(0.04, 0.03, 0.03), bone='head')   # nostril
        Vv, Ff = blob((sg * 0.098, 1.725, 1.37), (0.03, 0.036, 0.034), nseg=12); M.add('body', Vv, Ff, color=(0.02, 0.015, 0.015), bone='head')   # eye
        Vv, Ff = blob((sg * 0.108, 1.735, 1.385), (0.008, 0.01, 0.008), nseg=8); M.add('body', Vv, Ff, color=(0.95, 0.95, 0.95), bone='head')    # glint
        Vv, Ff = blob((sg * 0.095, 1.77, 1.35), (0.04, 0.012, 0.05), nseg=10); M.add('body', Vv, Ff, colfn=lambda p: coatcol((p[0], 1.6, p[2])) * 0.9, bone='head')   # brow ridge
        # ear: cone tilted up/out/forward
        Ve, Fe = lathe([(0.032, 0.0), (0.034, 0.03), (0.022, 0.1), (0.001, 0.16)], 10, (0, 0, 0), 1)
        Ve = Ve * np.array([1.0, 1.0, 0.55]); Ve = place(Ve, euler(0.35, 0, -sg * 0.3), (sg * 0.06, 1.86, 1.24))
        M.add('body', Ve, Fe, colfn=lambda p: coatcol((p[0], 1.6, p[2])), bone='head')
        Vi, Fi = lathe([(0.016, 0.01), (0.012, 0.08), (0.001, 0.135)], 8, (0, 0, 0), 1)
        Vi = place(Vi * np.array([1.0, 1.0, 0.5]), euler(0.35, 0, -sg * 0.3), (sg * 0.06, 1.865, 1.255)); M.add('body', Vi, Fi, color=(0.45, 0.3, 0.27), bone='head')
    # lips line
    Vv, Ff = blob((0, 1.462, 1.7), (0.045, 0.012, 0.03), nseg=10); M.add('body', Vv, Ff, color=(0.22, 0.15, 0.14), bone='head')

    # ------------------------------------------------------------ hair: mane strands, forelock, tail
    hcol = np.array(C['mane'])
    def strand(pts, w0, w1, bone, wfn=None, col=None, rng=None, phi=0.0):
        # flat ribbon along pts (list of 3-vectors), width tapers, side vector = x axis
        V = []; Fq = []; n = len(pts)
        for i, p_ in enumerate(pts):
            w = w0 + (w1 - w0) * i / (n - 1)
            wv = np.array([math.cos(phi) * w, 0, math.sin(phi) * w]); V.append(np.array(p_) + wv); V.append(np.array(p_) - wv)
        for i in range(n - 1):
            a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
            Fq += [[a, b, c], [b, d, c], [a, c, b], [b, c, d]]
        shade = 0.8 + 0.4 * (rng.random() if rng is not None else 0.5)
        M.add('hair', np.array(V), np.array(Fq), color=np.clip((col if col is not None else hcol) * shade, 0, 1), smooth=False, wfn=wfn, bone=bone)
    rng = np.random.default_rng(7)
    upv = np.array([0.0, 0.53, -0.85]); upv /= np.linalg.norm(upv)
    ncs = np.array([c for c, _, _ in nk]); nrx = np.array([r for _, r, _ in nk]); nry = np.array([r for _, _, r in nk])
    for k in range(24):
        t = k / 23.0
        ci = t * (len(nk) - 1); i0 = int(min(ci, len(nk) - 2)); f_ = ci - i0
        c = ncs[i0] * (1 - f_) + ncs[i0 + 1] * f_; rx_ = nrx[i0] * (1 - f_) + nrx[i0 + 1] * f_; ry_ = nry[i0] * (1 - f_) + nry[i0 + 1] * f_
        ln = 0.16 + 0.1 * rng.random()
        top = c + upv * ry_ * 1.0
        side = c + np.array([rx_ * 0.95, 0, 0]) + upv * ry_ * 0.35
        end = side + np.array([0.025 + 0.02 * rng.random(), -ln, -0.07 - 0.04 * rng.random()])
        pts = [top, top * 0.5 + side * 0.5 + np.array([0.012, 0.012, 0]), side + np.array([0.012, 0, 0]), (side + end) / 2 + np.array([0.025, 0, -0.02]), end]
        strand(pts, 0.03, 0.014, 'neck', rng=rng, phi=math.pi / 2)
    # forelock
    for k in range(7):
        x = (k - 3) * 0.012
        b0 = np.array([x, 1.855, 1.3]); pts = [b0, b0 + np.array([x * 0.5, -0.03, 0.05]), b0 + np.array([x, -0.09, 0.09]), b0 + np.array([x * 1.3, -0.16 - 0.02 * (k % 2), 0.1])]
        strand(pts, 0.014, 0.007, 'head', rng=rng, phi=0.6)
    # tail
    def tail_w(p): return [('tail', 1.0)] if p[1] > 1.12 else [('tail', 0.35), ('tail2', 0.65)] if p[1] > 0.85 else [('tail2', 1.0)]
    for k in range(44):
        a = rng.random() * 2 * math.pi; r = 0.025 * rng.random(); ln = 0.75 + 0.35 * rng.random()
        b0 = np.array([math.cos(a) * r, 1.34 + math.sin(a) * r * 0.5, -1.02])
        sway = (rng.random() - 0.5) * 0.12
        pts = [b0, b0 + np.array([sway * 0.3, -0.12, -0.1]), b0 + np.array([sway * 0.7, -0.3, -0.17]), b0 + np.array([sway, -0.5 * ln, -0.2]), b0 + np.array([sway * 1.2, -0.78 * ln, -0.18])]
        strand(pts, 0.034, 0.018, 'tail', wfn=tail_w, rng=rng, phi=rng.random() * math.pi)
    # tail dock
    Vv, Ff = loft([ring_xz((0, 1.34, -1.0), 0.04, 0.04), ring_xz((0, 1.25, -1.07), 0.045, 0.045)], 10, True, True)
    M.add('body', Vv, Ff, color=tuple(dark if coat != 'grey' else body * 0.8), bone='tail')

    # ------------------------------------------------------------ legs
    def legw(s, ykn, yfet, band=0.06):
        def f(p):
            y = p[1]
            if y > ykn + band: return [(s + '_u', 1.0)]
            if y > ykn - band:
                t = (y - (ykn - band)) / (2 * band); return [(s + '_u', t), (s + '_l', 1 - t)]
            if y > yfet + band: return [(s + '_l', 1.0)]
            if y > yfet - band:
                t = (y - (yfet - band)) / (2 * band); return [(s + '_l', t), (s + '_h', 1 - t)]
            return [(s + '_h', 1.0)]
        return f
    LEGP = {}
    def leg(s, front):
        x = H[s + '_u'][0]
        zu = 0.62 if front else -0.7
        if front:
            prof = [(1.12, zu, .1, .12), (0.95, zu + 0.005, .085, .105), (0.78, zu + 0.0, .066, .085), (0.64, zu + 0.015, .062, .075), (0.58, zu + 0.015, .066, .07),
                    (0.5, zu + 0.015, .046, .052), (0.36, zu + 0.015, .042, .048), (0.26, zu + 0.02, .046, .05), (0.205, zu + 0.03, .056, .062), (0.15, zu + 0.045, .045, .05), (0.1, zu + 0.06, .056, .06)]
            ykn, yfet = 0.6, 0.2
        else:
            prof = [(1.18, zu, .125, .17), (1.0, zu - 0.04, .105, .15), (0.82, zu - 0.1, .075, .115), (0.7, zu - 0.12, .07, .09), (0.63, zu - 0.15, .07, .095),
                    (0.55, zu - 0.1, .052, .06), (0.4, zu - 0.04, .043, .05), (0.28, zu, .044, .05), (0.215, zu + 0.01, .056, .062), (0.15, zu + 0.03, .045, .05), (0.1, zu + 0.05, .056, .06)]
            ykn, yfet = 0.64, 0.2
        rings = [ring_xz((x, y, z), rx_, rz_) for y, z, rx_, rz_ in prof]
        Vv, Ff = loft(rings, 14, False, False)
        LEGP[s] = (x, prof)
        zh = prof[-1][1]; xh = x
        # hoof (dark horn, flared) + steel shoe
        Vv, Ff = lathe([(0.001, 0.0), (0.078, 0.0), (0.082, 0.012), (0.07, 0.05), (0.058, 0.1), (0.001, 0.1)], 14, (xh, 0.0, zh + 0.03), 1)
        M.add('body', Vv, Ff, color=(0.13, 0.11, 0.1), bone=s + '_h')
        Vv, Ff = lathe([(0.082, 0.0), (0.086, 0.007), (0.082, 0.014), (0.07, 0.014), (0.07, 0.0)], 14, (xh, 0.0, zh + 0.03), 1)
        M.add('steel', Vv, Ff, bone=s + '_h')
        # hair tuft at the fetlock (feather)
        Vv, Ff = lathe([(0.04, 0.0), (0.062, 0.03), (0.05, 0.075)], 10, (xh, 0.145, zh + 0.012), 1)
    for s in ('fl', 'fr'): leg(s, True)
    for s in ('hl', 'hr'): leg(s, False)

    szs0 = np.array([q[0] for q in sec]); scy0 = np.array([q[1] for q in sec]); srx0 = np.array([q[2] for q in sec]); sry0 = np.array([q[3] for q in sec])
    # ------------------------------------------------------------ ONE smooth anatomical body (SDF smooth-union of muscle masses -> marching cubes)
    from skimage.measure import marching_cubes
    ELL = []     # (centre, frame(3x3 rows = local axes), radii)
    I3 = np.eye(3)
    GRP = [0]
    def ell(c, r, fr=I3): ELL.append((np.array(c, float), np.array(fr, float), np.array(r, float), GRP[0]))
    def grp(): GRP[0] += 1
    def frame_perp(axis):
        a = np.array(axis, float); a /= np.linalg.norm(a); ex = np.array([1.0, 0, 0]); ey = np.cross(a, ex); ey /= np.linalg.norm(ey)
        return np.array([ex, a, ey])
    # torso
    grp()
    zz = np.linspace(sec[0][0], sec[-1][0], 46)
    for z in zz:
        ell((0, np.interp(z, szs0, scy0), z), (max(np.interp(z, szs0, srx0), 0.03), max(np.interp(z, szs0, sry0), 0.03), 0.06))
    # muscle masses merged into the body (hindquarter, thigh, gluteal, shoulder, forearm root)
    for sg in (-1, 1):
        for cc, rr in (((sg * 0.2, 1.1, -0.72), (0.14, 0.3, 0.2)), ((sg * 0.19, 0.95, -0.7), (0.1, 0.2, 0.13)), ((sg * 0.17, 1.3, -0.86), (0.12, 0.13, 0.15)), ((sg * 0.2, 1.15, 0.62), (0.1, 0.25, 0.17)), ((sg * 0.17, 0.95, 0.63), (0.075, 0.17, 0.1)), ((sg * 0.16, 1.4, 0.55), (0.11, 0.12, 0.2))):
            grp(); ell(cc, rr)
    # neck (frames perpendicular to the neck axis)
    grp()
    for i in range(len(nk) - 1):
        for t in np.linspace(0, 1, 8, endpoint=(i == len(nk) - 2)):
            c = np.array(nk[i][0]) * (1 - t) + np.array(nk[i + 1][0]) * t; rxv = nk[i][1] * (1 - t) + nk[i + 1][1] * t; ryv = nk[i][2] * (1 - t) + nk[i + 1][2] * t
            ell(c, (rxv * 1.02, 0.06, ryv * 0.98), frame_perp((0, 0.8, 0.5)))
    # head
    grp()
    for i in range(len(hd) - 1):
        for t in np.linspace(0, 1, 6, endpoint=(i == len(hd) - 2)):
            c = np.array(hd[i][0]) * (1 - t) + np.array(hd[i + 1][0]) * t; rxv = hd[i][1] * (1 - t) + hd[i + 1][1] * t; ryv = hd[i][2] * (1 - t) + hd[i + 1][2] * t
            ell(c, (rxv, 0.04, ryv), frame_perp((0, -0.8, 0.6)))
    # legs
    for sname, (lx, prof) in LEGP.items():
        grp()
        for i in range(len(prof) - 1):
            y0, z0, rx0, rz0 = prof[i]; y1, z1, rx1, rz1 = prof[i + 1]
            for t in np.linspace(0, 1, max(2, int(abs(y0 - y1) / 0.035)), endpoint=(i == len(prof) - 2)):
                ell((lx, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t), ((rx0 + (rx1 - rx0) * t) * 1.08, 0.045, (rz0 + (rz1 - rz0) * t) * 1.08))
        # joints: knee/hock + fetlock knobs for definition
        yk = 0.6 if sname[0] == 'f' else 0.64
    step = 0.027; kk = 0.07
    xs = np.arange(-0.52, 0.52 + step, step); ys = np.arange(-0.02, 2.02, step); zs_ = np.arange(-1.25, 1.85, step)
    ng = GRP[0] + 1
    Dg = np.full((ng, len(xs), len(ys), len(zs_)), 9.0, np.float32)
    for c, fr, r, g in ELL:
        reach = r.max() + 3 * kk
        ix = np.where(abs(xs - c[0]) < reach)[0]; iy = np.where(abs(ys - c[1]) < reach)[0]; iz = np.where(abs(zs_ - c[2]) < reach)[0]
        if len(ix) == 0 or len(iy) == 0 or len(iz) == 0: continue
        gx, gy, gz = np.meshgrid(xs[ix] - c[0], ys[iy] - c[1], zs_[iz] - c[2], indexing='ij')
        q = np.stack([gx, gy, gz], -1) @ fr.T / r
        d = ((np.sqrt((q ** 2).sum(-1)) - 1.0) * r.min()).astype(np.float32)
        sub = Dg[g][np.ix_(ix, iy, iz)]; Dg[g][np.ix_(ix, iy, iz)] = np.minimum(sub, d)
    # polynomial smooth-min across groups (bounded inflation)
    S = Dg[0].copy()
    for g in range(1, ng):
        a_ = S; b_ = Dg[g]; h = np.maximum(kk - np.abs(a_ - b_), 0) / kk
        S = np.minimum(a_, b_) - h * h * kk * 0.25
    Fld = S
    del Dg
    vv, ff, _, _ = marching_cubes(Fld, 0.0, spacing=(step, step, step))
    vv = vv + np.array([xs[0], ys[0], zs_[0]])
    vv[:, 1] = np.maximum(vv[:, 1], 0.0)
    ff = ff[:, [0, 2, 1]]
    def sbody_w(p):
        x, y, z = p
        fx = float(np.clip((abs(x) - 0.06) / 0.08, 0, 1))
        front = z > 0.0
        if y < 1.18 and fx > 0:
            sd = ('f' if front else 'h') + ('l' if x > 0 else 'r')
            ykn, yfet = (0.6, 0.2) if front else (0.64, 0.2); band = 0.07
            u = float(np.clip((1.18 - y) / 0.22, 0, 1)) * fx
            if y > ykn + band: lw = [(sd + '_u', 1.0)]
            elif y > ykn - band: t = (y - (ykn - band)) / (2 * band); lw = [(sd + '_u', t), (sd + '_l', 1 - t)]
            elif y > yfet + band: lw = [(sd + '_l', 1.0)]
            elif y > yfet - band: t = (y - (yfet - band)) / (2 * band); lw = [(sd + '_l', t), (sd + '_h', 1 - t)]
            else: lw = [(sd + '_h', 1.0)]
            base = [('chest', 1.0)] if front else [('root', 1.0)]
            if u >= 0.999: return lw
            return [(b, w * u) for b, w in lw] + [(b, w * (1 - u)) for b, w in base]
        if y > 1.3 and z > 0.78:
            h = float(np.clip((z - 1.2) / 0.14, 0, 1)) if y > 1.35 else 0.0
            if z < 1.0:
                t = float(np.clip((y - 1.36) / 0.45, 0, 1)); return [('chest', 1 - t * 0.5), ('neck', t * 0.5)]
            return [('neck', 1 - h), ('head', h)] if h < 1 else [('head', 1.0)]
        if z > 0.1:
            t = min((z - 0.1) / 0.4, 1.0)
            if z > 0.78: return [('chest', 0.75), ('neck', 0.25)]
            return [('chest', t), ('root', 1 - t)] if t < 1 else [('chest', 1.0)]
        if z < -0.95: return [('root', 0.8), ('tail', 0.2)]
        return [('root', 1.0)]
    def sbody_col(p):
        c = coatcol(p)
        if p[2] > 1.3 and p[1] > 1.42: c = headcol(p)
        return c
    M.add('body', vv, ff, colfn=sbody_col, wfn=sbody_w)

    szs = np.array([q[0] for q in sec]); scy = np.array([q[1] for q in sec]); srx = np.array([q[2] for q in sec]); sry = np.array([q[3] for q in sec])
    def _flipfix(V, F, ctr):
        V = np.array(V); F = np.array(F)
        fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fc = V[F].mean(axis=1)
        out = fc - np.array([ctr[0], ctr[1], 0]) * np.array([1, 1, 0]) - np.array([0, 0, 0])
        out[:, 2] = 0; bad = (fn * out).sum(axis=1) < 0
        F = F.copy(); F[bad] = F[bad][:, [0, 2, 1]]; return F
    def CAPARISON():
        # draped trapper cloth: team field, gold border, scalloped hem; two skins so it has thickness
        zs = np.linspace(-0.66, 0.7, 68); rowsV = []
        for z in zs:
            rx_ = np.interp(z, szs, srx); ry_ = np.interp(z, szs, sry); cy = np.interp(z, szs, scy)
            edge = min(z + 0.66, 0.7 - z)
            yh = cy - ry_ * 0.55 - 0.03 + 0.1 * max(0.0, 0.1 - edge) * 3 + 0.025 * math.sin(z * 17)
            pts = [(-(rx_ * 1.1 + 0.07), yh), (-(rx_ * 1.07 + 0.03), cy - ry_ * 0.45)]
            for ph in np.linspace(-1.55, 1.55, 19): pts.append((rx_ * 1.045 * math.sin(ph), cy + ry_ * 1.045 * math.cos(ph) * 1.0))
            pts += [((rx_ * 1.07 + 0.03), cy - ry_ * 0.45), ((rx_ * 1.1 + 0.07), yh)]
            pts = [tuple(q) for q in pts]; dense = []
            for q in range(len(pts) - 1):
                n_ = 12 if q in (0, len(pts) - 2) else (3 if q in (1, len(pts) - 3) else 1)
                for sub in range(n_):
                    tt = sub / n_
                    dense.append((pts[q][0] * (1 - tt) + pts[q + 1][0] * tt, pts[q][1] * (1 - tt) + pts[q + 1][1] * tt))
            dense.append(pts[-1]); rowsV.append([(x, y, z) for x, y in dense])
        nz, nu = len(rowsV), len(rowsV[0])
        UVs = []
        for ri, r in enumerate(rowsV):
            arr = np.array(r); seg = np.linalg.norm(np.diff(arr[:, :2], axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); cum /= cum[-1]
            for ci in range(nu): UVs.append((cum[ci], ri / (nz - 1)))
        UVs = np.array(UVs)
        V = np.array([p for r in rowsV for p in r]); F = []
        for i in range(nz - 1):
            for j in range(nu - 1):
                a_, b_, c_, d_ = i * nu + j, i * nu + j + 1, (i + 1) * nu + j, (i + 1) * nu + j + 1
                F += [[a_, b_, c_], [b_, d_, c_]]
        F = np.array(F)
        cyv = np.interp(V[:, 2], szs, scy)
        Vin = V.copy(); Vin[:, 0] *= 0.985; Vin[:, 1] = cyv + (V[:, 1] - cyv) * 0.985 - 0.004
        def col(p):
            z = p[2]; edge = min(z + 0.66, 0.7 - z); yh = np.interp(z, szs, scy) - np.interp(z, szs, sry) * 0.55 - 0.03
            gold = np.array((0.95, 0.74, 0.22)); red = np.array((0.7, 0.07, 0.09)); dk = np.array((0.5, 0.04, 0.06))
            if p[1] < yh + 0.05 or edge < 0.05: return gold
            if p[1] < yh + 0.09 or edge < 0.09: return dk
            if p[1] < yh + 0.135 and p[1] > yh + 0.115: return gold * 0.9
            if abs(p[0]) > 0.25 and (p[2] ** 2 + (p[1] - (yh + 0.4)) ** 2) < 0.17 ** 2: return gold if (p[2] ** 2 + (p[1] - (yh + 0.4)) ** 2) > 0.12 ** 2 else dk
            return red * (0.95 + 0.06 * noise(p, 12.0))
        wf = lambda p: [('root', 1.0)] if p[2] < 0.0 else [('chest', 0.7), ('root', 0.3)]
        M.add('caparison', V, _flipfix(V, F, (0, 1.25)), color=(1, 1, 1), wfn=wf, smooth=True, uvs=UVs)
        M.add('cloth', Vin, _flipfix(Vin, F, (0, 1.25))[:, [0, 2, 1]], color=(0.45, 0.05, 0.07), wfn=wf, smooth=False)

    def arc_plate(rings, i0, i1, a0, a1, off, mat, col, bone, nz=1, nth=7, wfn=None, gap=0.0):
        # curved plate following loft rings (c,u,v) between ring index floats i0..i1 and ellipse angles a0..a1 (90deg = top)
        n = len(rings)
        def ring_at(f):
            i = int(min(max(f, 0), n - 2)); t = f - i
            c = np.array(rings[i][0]) * (1 - t) + np.array(rings[i + 1][0]) * t
            u = np.array(rings[i][1]) * (1 - t) + np.array(rings[i + 1][1]) * t; v = np.array(rings[i][2]) * (1 - t) + np.array(rings[i + 1][2]) * t
            return c, u, v
        V = []; F = []
        steps = max(2, nz + 1)
        for k in range(steps):
            c, u, v = ring_at(i0 + (i1 - i0) * k / (steps - 1))
            for th in np.linspace(a0, a1, nth):
                th = math.radians(th); p = c + u * math.cos(th) * (1 + off / max(np.linalg.norm(u), 1e-3)) + v * math.sin(th) * (1 + off / max(np.linalg.norm(v), 1e-3)); V.append(p)
        for k in range(steps - 1):
            for j in range(nth - 1):
                a_, b_, c_, d_ = k * nth + j, k * nth + j + 1, (k + 1) * nth + j, (k + 1) * nth + j + 1
                F += [[a_, b_, c_], [b_, d_, c_]]
        V = np.array(V); F = np.array(F)
        cen = np.array([np.mean([r[0][i] for r in rings]) for i in range(3)])
        fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fc = V[F].mean(axis=1)
        # orient outward from the ring axis
        ci = [np.array(ring_at(i0 + (i1 - i0) * (k + 0.5) / (steps - 1))[0]) for k in range(steps - 1)]
        bad = np.array([(fn[f] @ (fc[f] - ci[min(f // (2 * (nth - 1)), len(ci) - 1)])) < 0 for f in range(len(F))])
        F[bad] = F[bad][:, [0, 2, 1]]
        M.add(mat, V, F, color=col, bone=bone, smooth=True, wfn=wfn)

    # ------------------------------------------------------------ tack (saddle blanket in team cloth, saddle, stirrups, girth, bridle, reins, breastcollar)
    CAPARISON()
    Vv, Ff = loft([ring_xy((0, 1.64 + 0.012 * (abs(zz) > 0.2), zz), 0.14, 0.065 + 0.03 * (abs(zz) > 0.22)) for zz in (-0.34, -0.22, 0.0, 0.2, 0.3)], 12, True, True)
    M.add('leather', Vv, Ff, wfn=lambda p: [('root', 0.5), ('chest', 0.5)])
    Vv, Ff = box((0, 1.78, -0.32), (0.3, 0.17, 0.05), euler(-0.3, 0, 0)); M.add('leather', Vv, Ff, smooth=False, bone='root')
    Vv, Ff = box((0, 1.74, 0.3), (0.12, 0.14, 0.06), euler(0.3, 0, 0)); M.add('leather', Vv, Ff, smooth=False, bone='chest')
    for sg in (-1, 1):
        Vv, Ff = box((sg * 0.37, 1.2, 0.0), (0.016, 0.62, 0.03)); M.add('leather', Vv, Ff, smooth=False, bone='root')
        Vv, Ff = lathe([(0.065, 0.0), (0.065, 0.012)], 4, (0, 0, 0), 1)
        Vv, Ff = box((sg * 0.37, 0.89, 0.0), (0.1, 0.014, 0.115)); M.add('steel', Vv, Ff, smooth=False, bone='root')
        Vv, Ff = box((sg * 0.37, 0.95, 0.0), (0.1, 0.1, 0.012)); M.add('steel', Vv, Ff, smooth=False, bone='root')
    Vv, Ff = loft([ring_xy((0, 1.2, 0.2), 0.288, 0.388), ring_xy((0, 1.2, 0.26), 0.288, 0.388)], 18, False, False)
    M.add('leather', Vv, Ff, wfn=lambda p: [('chest', 1.0)])
    # breast collar
    Vv, Ff = loft([ring_xy((0, 1.3, 0.93 + 0.01 * k), 0.215 - 0.03 * k, 0.28 - 0.03 * k) for k in range(2)], 14, False, False)
    M.add('leather', Vv, Ff, wfn=lambda p: [('chest', 1.0)])
    # bridle: noseband, browband, cheekpieces, bit rings, reins
    Vv, Ff = loft([ring_perp((0, 1.52, 1.58), (0, -0.8, 0.6), 0.064, 0.102), ring_perp((0, 1.515, 1.592), (0, -0.8, 0.6), 0.064, 0.102)], 14, False, False)
    M.add('leather', Vv, Ff, bone='head')
    Vv, Ff = loft([ring_perp((0, 1.745, 1.37), (0, -0.8, 0.6), 0.108, 0.155), ring_perp((0, 1.757, 1.362), (0, -0.8, 0.6), 0.108, 0.155)], 14, False, False)
    M.add('leather', Vv, Ff, bone='head')
    Vv, Ff = loft([ring_perp((0, 1.67, 1.33), (0, -0.8, 0.6), 0.112, 0.15), ring_perp((0, 1.67, 1.322), (0, -0.8, 0.6), 0.112, 0.15)], 14, False, False)
    M.add('leather', Vv, Ff, bone='head')
    for sg in (-1, 1):
        Vv, Ff = box((sg * 0.095, 1.64, 1.4), (0.012, 0.2, 0.014), euler(0.5, 0, 0)); M.add('leather', Vv, Ff, smooth=False, bone='head')
        Vv, Ff = lathe([(0.02, 0.0), (0.02, 0.006)], 8, (0, 0, 0), 0)
        Vv, Ff = loft([ring_xz((sg * 0.07, 1.495, 1.62), 0.017, 0.017), ring_xz((sg * 0.07, 1.47, 1.62), 0.017, 0.017)], 8, True, True); M.add('steel', Vv, Ff, bone='head')
        # rein: from bit ring back to the saddle bow
        pts = [(sg * 0.075, 1.48, 1.62), (sg * 0.1, 1.5, 1.35), (sg * 0.14, 1.55, 0.95), (sg * 0.15, 1.5, 0.6)]
        rr = [(np.array(q), (0.004, 0, 0), (0, 0, 0.004)) for q in pts]
        Vv, Ff = loft(rr, 4, False, False); M.add('leather', Vv, Ff, bone='neck', smooth=True)


    # ------------------------------------------------------------ barding: crinet (neck plates), face plate, peytral (chest)
    for k in range(8):
        f0 = k * 0.62; f1 = f0 + 0.7
        arc_plate(rings_neck, f0, min(f1, len(rings_neck) - 1.001), 40, 140, 0.012 + 0.004 * (k % 2), 'steel', (1, 1, 1), 'neck', nz=1, nth=6, wfn=neck_w)
        arc_plate(rings_neck, f0 + 0.02, min(f0 + 0.1, len(rings_neck) - 1.001), 55, 125, 0.02, 'gold', (1, 1, 1), 'neck', nz=1, nth=4, wfn=neck_w)
    arc_plate(rings_head, 1.4, 6.3, 62, 118, 0.011, 'steel', (1, 1, 1), 'head', nz=7, nth=7)       # face plate (chamfron)
    arc_plate(rings_head, 1.4, 6.3, 87, 93, 0.02, 'gold', (1, 1, 1), 'head', nz=7, nth=3)          # gold ridge
    Vv, Ff = lathe([(0.03, 0.0), (0.02, 0.05), (0.001, 0.1)], 8, (0, 0, 0), 1); M.add('gold', place(Vv, euler(0.55, 0, 0), (0, 1.8, 1.4)), Ff, bone='head')   # plume spike
    for sg in (-1, 1):
        Vv, Ff = blob((sg * 0.1, 1.735, 1.375), (0.044, 0.044, 0.02), nseg=12); M.add('steel', Vv, Ff, bone='head') if False else None

    # ------------------------------------------------------------ animation
    def rotx(v): return (v, 0, 0)
    LEG = ('fl', 'fr', 'hl', 'hr')

    def idle(t):
        a = 2 * math.pi * t
        Pz = {'root': (math.sin(a) * 0.004, 0, 0), 'chest': (math.sin(a) * 0.012, math.sin(a * 0.5) * 0.02, 0),   # breathing
              'neck': (-0.03 + math.sin(a + 1.0) * 0.03 + 0.05 * max(0, math.sin(a * 0.5 + 2)), math.sin(a * 0.5 + 0.6) * 0.18, 0),
              'head': (math.sin(a * 2 + 0.5) * 0.03, math.sin(a * 0.5 + 1.0) * 0.1, 0),
              'tail': (0.2 + math.sin(a) * 0.06, math.sin(a * 2) * 0.16, 0), 'tail2': (0.1, math.sin(a * 2 - 0.8) * 0.25, 0)}
        # weight shift + one hoof paw per cycle
        paw = max(0.0, math.sin(a * 1.0 - 1.2)) ** 3 if t > 0.5 else 0.0
        Pz['fl_u'] = (-paw * 0.5, 0, 0); Pz['fl_l'] = (paw * 1.0, 0, 0); Pz['fl_h'] = (-paw * 0.3, 0, 0)
        Pz['hr_u'] = (0.04 * math.sin(a * 0.5), 0, 0)
        return Pz, [0, 0.003 * math.sin(a), 0]

    def legcycle(ph, front, duty, fwd0, back0, flex):
        """foot on the ground while the leg sweeps back (stance), then folds and swings forward (swing). returns (u, l, h) rotations"""
        ph = ph % 1.0
        if ph < duty:
            k = ph / duty; uf = fwd0 + (back0 - fwd0) * k
            fl = 0.06 + 0.1 * max(0.0, k - 0.75) * 4.0 * (1 if front else 0.6)       # heel lifts at push-off
            hh = 0.0
        else:
            psi = (ph - duty) / (1.0 - duty); sm = psi * psi * (3 - 2 * psi)
            uf = back0 + (fwd0 - back0) * sm
            fl = flex * math.sin(math.pi * min(1.0, psi * 1.12)) ** 0.9 + 0.06
            hh = 0.3 * math.sin(math.pi * psi)
        if front: return (-uf, fl, -hh * 0.6)
        return (-uf, -fl * 1.05, hh)

    def gait(t, kind):
        Pz = {}
        if kind == 'walk': ph = dict(hl=0.0, fl=0.25, hr=0.5, fr=0.75); duty, f0, b0, fx = 0.62, 0.32, -0.3, 1.1; bob = 0.012
        else: ph = dict(hr=0.0, hl=0.1, fr=0.42, fl=0.52); duty, f0, b0, fx = 0.34, 0.5, -0.5, 1.7; bob = 0.055
        a = 2 * math.pi * t
        for s in LEG:
            front = s[0] == 'f'
            u_, l_, h_ = legcycle(t + ph[s], front, duty, f0 if front else f0 * 0.9, b0 if front else b0 * 1.1, fx if front else fx * 0.9)
            Pz[s + '_u'] = (u_, 0, 0); Pz[s + '_l'] = (l_, 0, 0); Pz[s + '_h'] = (h_, 0, 0)
        if kind == 'run':
            Pz['root'] = (-math.sin(a + 0.4) * 0.14, 0, math.sin(a) * 0.02)
            Pz['chest'] = (math.sin(a + 0.4) * 0.17, math.sin(a) * 0.03, 0)               # spine flexes opposite to the pelvis
            Pz['neck'] = (-0.28 + math.sin(a + 1.4) * 0.12, 0, 0)                         # neck stretched out, bobbing
            Pz['head'] = (0.12 + math.sin(a + 2.0) * 0.06, 0, 0)
            Pz['tail'] = (0.75 + math.sin(a * 2) * 0.1, math.sin(a) * 0.1, 0); Pz['tail2'] = (0.35 + math.sin(a * 2 - 1) * 0.15, math.sin(a - 0.5) * 0.15, 0)
            off = [0, bob * (0.5 + 0.5 * math.sin(2 * a + 0.2)) - 0.02, 0]
        else:
            Pz['root'] = (math.sin(a * 2) * 0.012, math.sin(a) * 0.03, math.sin(a) * 0.015)
            Pz['chest'] = (math.sin(a * 2 + 0.5) * 0.01, -math.sin(a) * 0.03, -math.sin(a) * 0.012)
            Pz['neck'] = (-0.04 + math.sin(a * 2 + 1.0) * 0.07, math.sin(a) * 0.05, 0)       # head nods with each stride
            Pz['head'] = (math.sin(a * 2 + 2.0) * 0.05, 0, 0)
            Pz['tail'] = (0.3 + math.sin(a * 2) * 0.1, math.sin(a) * 0.18, 0); Pz['tail2'] = (0.15, math.sin(a - 0.7) * 0.25, 0)
            off = [0, bob * abs(math.sin(a * 2)), 0]
        return Pz, off

    def turn(t, d):
        # in-place turn: neck and head lead into the turn, forelegs cross over and step, hindquarters pivot
        Pz = gait(t, 'walk')[0]
        a = 2 * math.pi * t
        for k in list(Pz.keys()):
            if k.endswith('_u') or k.endswith('_l') or k.endswith('_h'):
                v = Pz[k]; Pz[k] = (v[0] * 0.6, 0, 0)
        for s in LEG:
            ang = 2 * math.pi * (t + dict(hl=0.0, fl=0.25, hr=0.5, fr=0.75)[s]); lift = max(0.0, math.cos(ang))
            Pz[s + '_u'] = (Pz[s + '_u'][0], 0, d * lift * 0.28 * (1 if s[1] == 'l' else -1))
        Pz['neck'] = (-0.04 + math.sin(a * 2) * 0.03, 0.55 * d, 0.0); Pz['head'] = (0.03, 0.22 * d, 0.0)
        Pz['chest'] = (0.0, 0.2 * d + math.sin(a) * 0.03, -0.05 * d); Pz['root'] = (0.0, -0.12 * d - math.sin(a) * 0.03, 0.04 * d)
        Pz['tail'] = (0.3, -0.35 * d + math.sin(a * 2) * 0.1, 0)
        return Pz, [0, 0.01 * abs(math.sin(a * 2)), 0]

    CLIPS = [('idle', 4.0, idle, True), ('walk', 1.2, lambda t: gait(t, 'walk'), True), ('run', 0.62, lambda t: gait(t, 'run'), True),
             ('turn_left', 1.2, lambda t: turn(t, 1.0), True), ('turn_right', 1.2, lambda t: turn(t, -1.0), True)]
    n = M.write(f'{outdir}/{name}.glb', CLIPS)
    print(name, n // 1024, 'KB')


if __name__ == '__main__':
    out = sys.argv[1]; make_caparison_tex(out)
    build('bay', 'horse', out); build('chestnut', 'horse2', out); build('black', 'horse3', out); build('grey', 'horse4', out)
