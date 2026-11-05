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


def build(coat, name, outdir):
    C = COATS[coat]
    M = Model(BONES, P, H)
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
    M.add('body', Vb, Fb, colfn=coatcol, wfn=body_w)

    # muscle masses: hindquarter, gaskin, shoulder, forearm, neck-base, gluteal
    def blob(c, r, bone=None, wfn=None, nseg=14, sq=1.0):
        Vv, Ff = lathe([(0.001, -r[1]), (r[0] * 0.7, -r[1] * 0.75), (r[0], -r[1] * 0.25), (r[0], r[1] * 0.25), (r[0] * 0.7, r[1] * 0.75), (0.001, r[1])], nseg, (0, 0, 0), 1)
        Vv = Vv * np.array([1.0, 1.0, r[2] / r[0]]) + np.array(c)
        return Vv, Ff
    for sg in (-1, 1):
        for c_, r_, bn in (((sg * 0.23, 1.03, -0.72), (0.14, 0.27, 0.2), 'root'),                            ((sg * 0.23, 1.18, 0.6), (0.1, 0.22, 0.17), 'chest'),                            ((sg * 0.18, 1.27, -0.88), (0.1, 0.1, 0.15), 'root')):
            Vv, Ff = blob(c_, r_); M.add('body', Vv, Ff, colfn=coatcol, bone=bn)

    # ------------------------------------------------------------ neck (arched crest)
    nk = [((0, 1.36, 0.84), 0.19, 0.31), ((0, 1.46, 0.95), 0.165, 0.275), ((0, 1.58, 1.05), 0.14, 0.235), ((0, 1.7, 1.14), 0.118, 0.2), ((0, 1.79, 1.22), 0.1, 0.17), ((0, 1.84, 1.28), 0.088, 0.14)]
    rings = [ring_perp(c, (0, 0.8, 0.5), rxv, ryv) for c, rxv, ryv in nk]
    Vn, Fn = loft(rings, 18, False, False)
    def neck_w(p):
        t = float(np.clip((p[1] - 1.36) / 0.45, 0, 1))
        if t < 0.35: return [('chest', 1 - t / 0.35 * 0.5), ('neck', t / 0.35 * 0.5)]
        if t > 0.85: return [('neck', 1 - (t - 0.85) / 0.15 * 0.4), ('head', (t - 0.85) / 0.15 * 0.4)]
        return [('neck', 1.0)]
    M.add('body', Vn, Fn, colfn=coatcol, wfn=neck_w)

    # ------------------------------------------------------------ head (poll -> muzzle)
    hd = [((0, 1.84, 1.27), 0.07, 0.09), ((0, 1.8, 1.31), 0.095, 0.125), ((0, 1.72, 1.375), 0.105, 0.15), ((0, 1.64, 1.44), 0.1, 0.15),
          ((0, 1.57, 1.51), 0.08, 0.12), ((0, 1.515, 1.585), 0.06, 0.1), ((0, 1.485, 1.65), 0.066, 0.095), ((0, 1.47, 1.7), 0.058, 0.07), ((0, 1.465, 1.725), 0.03, 0.03)]
    rings = [ring_perp(c, (0, -0.8, 0.6), rxv, ryv) for c, rxv, ryv in hd]
    Vh, Fh = loft(rings, 20, True, True)
    blaze = C['blaze']
    def headcol(p):
        c = coatcol((p[0], 1.6, p[2]))
        if p[2] > 1.6 and p[1] < 1.56: c = np.array((0.32, 0.22, 0.2)) if coat != 'black' else np.array((0.08, 0.07, 0.07))   # muzzle
        if p[2] > 1.68: c = c * 0.65
        if blaze and abs(p[0]) < 0.028 and p[2] > 1.33 and p[1] > 1.5: c = np.array((0.95, 0.93, 0.88))
        return c
    M.add('body', Vh, Fh, colfn=headcol, bone='head')
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
        M.add('body', Vv, Ff, colfn=coatcol, wfn=legw(s, ykn, yfet))
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

    # ------------------------------------------------------------ tack (saddle blanket in team cloth, saddle, stirrups, girth, bridle, reins, breastcollar)
    Vv, Ff = loft([ring_xy((0, 1.36, zz), 0.335 - 0.03 * abs(zz), 0.275) for zz in (-0.4, -0.2, 0.0, 0.2, 0.4)], 16, True, True)
    M.add('cloth', Vv, Ff, color=(0.78, 0.12, 0.12), bone='root', wfn=lambda p: [('root', 1.0)] if p[2] < 0.1 else [('chest', 0.6), ('root', 0.4)])
    Vv, Ff = loft([ring_xy((0, 1.455 + 0.012 * (abs(zz) > 0.2), zz), 0.14, 0.065 + 0.03 * (abs(zz) > 0.22)) for zz in (-0.34, -0.22, 0.0, 0.2, 0.3)], 12, True, True)
    M.add('leather', Vv, Ff, wfn=lambda p: [('root', 0.5), ('chest', 0.5)])
    Vv, Ff = box((0, 1.56, -0.32), (0.3, 0.14, 0.05), euler(-0.3, 0, 0)); M.add('leather', Vv, Ff, smooth=False, bone='root')
    Vv, Ff = box((0, 1.54, 0.3), (0.12, 0.12, 0.06), euler(0.3, 0, 0)); M.add('leather', Vv, Ff, smooth=False, bone='chest')
    for sg in (-1, 1):
        Vv, Ff = box((sg * 0.34, 1.05, 0.0), (0.016, 0.42, 0.03)); M.add('leather', Vv, Ff, smooth=False, bone='root')
        Vv, Ff = lathe([(0.065, 0.0), (0.065, 0.012)], 4, (0, 0, 0), 1)
        Vv, Ff = box((sg * 0.34, 0.84, 0.0), (0.1, 0.014, 0.115)); M.add('steel', Vv, Ff, smooth=False, bone='root')
        Vv, Ff = box((sg * 0.34, 0.9, 0.0), (0.1, 0.1, 0.012)); M.add('steel', Vv, Ff, smooth=False, bone='root')
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

    def gait(t, kind):
        Pz = {}
        if kind == 'walk': ph = dict(hl=0.0, fl=0.25, hr=0.5, fr=0.75); amp = 0.42; bob = 0.012
        else: ph = dict(hr=0.0, hl=0.1, fr=0.42, fl=0.52); amp = 0.95; bob = 0.055
        a = 2 * math.pi * t
        for s in LEG:
            ang = 2 * math.pi * (t + ph[s]); front = s[0] == 'f'
            sw = math.sin(ang); lift = max(0.0, math.cos(ang))
            if kind == 'run':
                # gallop: leg reaches far forward, folds high in the air, then drives back
                reach = amp * (0.8 if front else 0.7)
                Pz[s + '_u'] = ((sw * reach - 0.1) * (-1 if front else -1) * (1 if front else 1) * 1.0, 0, 0)
                if front: Pz[s + '_u'] = (-sw * reach, 0, 0); Pz[s + '_l'] = ((lift ** 0.8) * 1.5 + 0.05, 0, 0); Pz[s + '_h'] = (-lift * 0.5, 0, 0)
                else: Pz[s + '_u'] = (sw * reach, 0, 0); Pz[s + '_l'] = (-(lift ** 0.8) * 1.25 - 0.05, 0, 0); Pz[s + '_h'] = (lift * 0.45, 0, 0)
            else:
                if front: Pz[s + '_u'] = (-sw * amp, 0, 0); Pz[s + '_l'] = (lift * 0.95 + 0.04, 0, 0); Pz[s + '_h'] = (-lift * 0.25, 0, 0)
                else: Pz[s + '_u'] = (sw * amp * 0.85, 0, 0); Pz[s + '_l'] = (-lift * 0.85 - 0.04, 0, 0); Pz[s + '_h'] = (lift * 0.3, 0, 0)
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
    out = sys.argv[1]
    build('bay', 'horse', out); build('chestnut', 'horse2', out); build('black', 'horse3', out); build('grey', 'horse4', out)
