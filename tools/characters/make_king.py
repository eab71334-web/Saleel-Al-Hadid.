"""Customisable king: ONE glb with many named parts (Skin, HairN, BeardN, HelmN, CrownN, Gem, PauldN, ChestN, LegsN, BootsN, EmblemN, Cape, SwordN, Shield, Patch, Scar)
that the game shows/hides and tints at runtime.   python3 make_king.py outdir"""
import sys, math, copy, numpy as np
sys.path.insert(0, '/tmp/mh2')
import chars2 as C, base as B, gear as G, anim
from mhlib import *

C.SKIN['king'] = (0.95, 0.80, 0.68)       # lightest tone: runtime tint = chosen_tone / this  (always <= 1)
KING = [c for c in C.CHARS if c['name'] == 'hero'][0]
KING = dict(KING, name='king', skin='king', hair_col=(0.2, 0.14, 0.1), beard=0.0, eye='blue')


def split_body(M, base, col):
    Vv = base['V']; Fv = base['F']; dom = base['dom']
    sk = np.array([d in ('head', 'neck01') for d in dom])
    fs = sk[Fv].all(axis=1)
    N = np.zeros_like(Vv); fn = np.cross(Vv[Fv[:, 1]] - Vv[Fv[:, 0]], Vv[Fv[:, 2]] - Vv[Fv[:, 0]])
    for k in range(3): np.add.at(N, Fv[:, k], fn)
    ln = np.linalg.norm(N, axis=1, keepdims=True); ln[ln == 0] = 1; N /= ln
    for part, mask in (('Skin', fs), (None, ~fs)):
        F = Fv[mask]; used = np.unique(F); remap = -np.ones(len(Vv), int); remap[used] = np.arange(len(used))
        M.part = part
        P = M.prims.setdefault((part, 'body'), dict(pos=[], nrm=[], uv=[], col=[], j=[], w=[], idx=[], n=0))
        off = P['n']
        P['pos'].append(Vv[used]); P['nrm'].append(N[used]); P['uv'].append(np.zeros((len(used), 2))); P['col'].append(col[used])
        P['j'].append(base['J'][used]); P['w'].append(base['W'][used]); P['idx'].append(remap[F] + 0); P['n'] += len(used)
    M.part = None


def ofix(V, F, axis='y'):
    """flip triangles so normals point away from the local axis (axis 'y': vertical shells, 'x': limbs along x)"""
    V = np.array(V); F = np.array(F).copy(); a, b = (0, 2) if axis == 'y' else (1, 2); w = 1 if axis == 'y' else 0
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); fc = V[F].mean(axis=1)
    for i in range(len(F)):
        near = np.abs(V[:, w] - fc[i, w]) < 0.02
        if near.sum() < 3: continue
        c = V[near].mean(axis=0); out = np.zeros(3); out[a] = fc[i, a] - c[a]; out[b] = fc[i, b] - c[b]
        if fn[i] @ out < 0: F[i] = F[i][[0, 2, 1]]
    return F


def build():
    ch = KING
    base = B.build(ch['spec'], head_cell=0.0, body_cell=ch.get('body_cell', 0.024))
    G.use(base); anim.set_base(base); anim.FRAMES.clear(); G.setpose('melee')
    M = Model(base['order'], base['parents'], {b: base['hp'][b] for b in base['order']})
    hp = base['hp']; V = base['V']; dom = base['dom']
    col = C.paint(base, ch)
    split_body(M, base, col); C.add_eyes(M, base, ch)

    hm = np.array([d == 'head' for d in dom]); top = V[hm, 1].max(); zf = V[hm, 2].max(); zb = V[hm, 2].min(); cz = (zf + zb) / 2
    xs = V[hm, 0]; rxh = (xs.max() - xs.min()) / 2; rzh = (zf - zb) / 2
    ev = base['eyes']['V']; ey = ev[:, 1].mean(); eyeL = ev[ev[:, 0] > 0].mean(0)
    wy = hp['root'][1]; ny = hp['neck01'][1]; ank = hp['foot.L'][1]
    W = (1.0, 1.0, 1.0)

    # ------------------------------------------------------------ hair
    for nm, st in (('Hair1', 'short'), ('Hair2', 'long'), ('Hair3', 'bun')):
        M.part = nm; C.hair_style(M, base, ch, st, W)
    M.part = 'Hair4'                                  # mohawk: crest of tapered strands front-to-back
    for k in range(15):
        t = k / 14.0; z = zf - 0.03 - t * (zf - zb - 0.06); y = top + 0.005 + 0.045 * math.sin(math.pi * (0.1 + 0.85 * t)) + (1 - t) * 0.015
        Vm, Fm = box((0, y, z), (0.012, 0.03 + 0.035 * math.sin(math.pi * t), 0.02), euler(0.0, 0, 0))
        M.add('hair', Vm, Fm, color=W, smooth=False, bone='head')
    # side shave stubble
    # ------------------------------------------------------------ beards
    M.part = 'BeardStubble'; C.beard_geo(M, base, ch, W, 'short')
    M.part = 'BeardFull'; C.beard_geo(M, base, ch, W, 'full')
    M.part = 'BeardBraid'; C.beard_geo(M, base, ch, W, 'full')
    for sg in (-1, 1):
        pts = [(sg * 0.022, ey - 0.15 - 0.04 * k, zf - 0.01 + 0.012 * k) for k in range(5)]
        rr = [(np.array(p_), (0.014 - 0.0022 * k, 0, 0), (0, 0, 0.014 - 0.0022 * k)) for k, p_ in enumerate(pts)]
        Vb, Fb = loft(rr, 8, False, True); M.add('hair', Vb, Fb, color=W, bone='head')
        for k in range(4):
            Vq, Fq = box(pts[k] + np.array([0, -0.02, 0.0]), (0.017, 0.004, 0.017)); M.add('gold', Vq, Fq, smooth=False, bone='head')
    # ------------------------------------------------------------ eye patch + scar
    M.part = 'Patch'
    Vp, Fp = lathe([(0.001, 0.0), (0.03, 0.0), (0.03, 0.006), (0.001, 0.008)], 12, (0, 0, 0), 2)
    Vp = place(Vp, euler(0, 0, 0), (eyeL[0], eyeL[1], zf - 0.006)); M.add('leather', Vp, Fp, color=(0.1, 0.08, 0.07), bone='head')
    rr = [ring_xz((0, y, cz), rxh + 0.006, rzh + 0.006) for y in (ey + 0.012, ey + 0.026)]
    Vp, Fp = loft(rr, 20, False, False); M.add('leather', Vp, Fp, color=(0.1, 0.08, 0.07), bone='head')
    M.part = 'Scar'
    Vs_, Fs_ = box((-eyeL[0] * 0.95, ey - 0.005, zf - 0.004), (0.0045, 0.06, 0.004), euler(0, 0, 0.45)); M.add('body', Vs_, Fs_, color=(0.62, 0.3, 0.27), smooth=False, bone='head')

    # ------------------------------------------------------------ helmets (heavy -> light)
    hy0 = hp['head'][1]
    def dome(y0, y1, grow, n=9, k0=0.93):
        rings = []
        for t in np.linspace(0, 1, n):
            y = y0 + (y1 - y0) * t; s = math.sqrt(max(1 - t ** 2.2, 0.02)) if t < 1 else 0.02
            e = C.head_ext(min(y, top - 0.004)) or (-rxh, rxh, zb, zf)
            x0, x1, z0, z1 = e
            rings.append(ring_xz(((x0 + x1) / 2, y, (z0 + z1) / 2 - 0.004), ((x1 - x0) / 2 + grow) * (k0 + 0.1 * (1 - t)) * s + 0.001, ((z1 - z0) / 2 + grow) * (k0 + 0.1 * (1 - t)) * s + 0.001))
        return rings
    # Helm0: great helm (fully enclosed, eye slit, breaths)
    M.part = 'Helm0'
    rings = dome(ny + 0.0, top + 0.035, 0.03, n=11, k0=0.97)
    Vv, Fv = loft(rings, 20, False, True); M.add('steel', Vv, Fv, bone='head')
    Vv, Fv = box((0, ey + 0.012, zf + 0.03), (0.075, 0.008, 0.012)); M.add('iron', Vv, Fv, color=(0.02, 0.02, 0.02), smooth=False, bone='head')
    Vv, Fv = box((0, ey + 0.012, zf + 0.0), (0.005, 0.03, 0.012)); M.add('steel', Vv, Fv, smooth=False, bone='head')
    for k in range(5):
        for sg in (-1, 1):
            Vv, Fv = box((sg * (0.015 + 0.012 * k), ey - 0.07 - 0.008 * k, zf + 0.03), (0.003, 0.003, 0.01)); M.add('iron', Vv, Fv, color=(0.02, 0.02, 0.02), smooth=False, bone='head')
    Vv, Fv = box((0, top + 0.05, cz), (0.01, 0.025, rzh * 0.9)); M.add('gold', Vv, Fv, smooth=False, bone='head')           # crest
    # Helm1: bascinet with raised visor, mail aventail
    M.part = 'Helm1'
    rings = dome(ey - 0.1, top + 0.025, 0.02, n=10)
    Vv, Fv = loft(rings, 20, False, True)
    keep = [f for f in Fv if not (Vv[f][:, 2].mean() > cz + 0.03 and Vv[f][:, 1].mean() < ey + 0.035 and abs(Vv[f][:, 0].mean()) < rxh * 0.82)]
    M.add('steel', Vv, np.array(keep), bone='head')
    rr = [ring_xz((0, y, cz - 0.01), rxh * k + 0.03, rzh * k + 0.035) for y, k in ((ey - 0.07, 1.0), (ey - 0.13, 1.08), (ny - 0.03, 1.15), (ny - 0.07, 1.3))]
    Vv, Fv = loft(rr, 18, False, False); M.add('iron', Vv, Fv, bone='head', wfn=lambda p: [('head', 0.5), ('neck01', 0.5)] if p[1] > ny else [('neck01', 1.0)])
    Vv, Fv = box((0, ey + 0.065, zf + 0.025), (0.06, 0.04, 0.008), euler(-0.35, 0, 0)); M.add('steel', Vv, Fv, smooth=False, bone='head')   # raised visor
    # Helm2: kettle hat with nasal
    M.part = 'Helm2'
    rings = dome(ey + 0.03, top + 0.02, 0.016, n=8)
    Vv, Fv = loft(rings, 18, False, True); M.add('steel', Vv, Fv, bone='head')
    Vv, Fv = lathe([(rxh + 0.07, 0.0), (rxh + 0.07, 0.006), (rxh + 0.015, 0.012)], 22, (0, ey + 0.045, cz), 1); M.add('steel', Vv, Fv, bone='head')
    Vv, Fv = box((0, ey - 0.0, zf + 0.012), (0.009, 0.06, 0.006)); M.add('steel', Vv, Fv, smooth=False, bone='head')
    # Helm3: leather cap / arming coif
    M.part = 'Helm3'
    rings = dome(ey - 0.12, top + 0.012, 0.011, n=9, k0=0.98)
    Vv, Fv = loft(rings, 20, False, True)
    keep = [f for f in Fv if not (Vv[f][:, 2].mean() > cz + 0.02 and Vv[f][:, 1].mean() < ey + 0.075)]
    M.add('leather', Vv, np.array(keep), bone='head')
    # ------------------------------------------------------------ crowns (+gem)
    cy0 = top - 0.012
    cr = max(rxh, rzh) * 0.0 + 0.0
    def band(m, mat, h=0.05, grow=0.02):
        rr = [ring_xz((0, cy0 + dy, cz - 0.004), rxh + grow, rzh + grow) for dy in (0.0, h)]
        Vv, Fv = loft(rr, 28, False, False); M.add(mat, Vv, Fv, bone='head')
    M.part = 'Crown0'; band(M, 'gold')
    for k in range(9):
        a = 2 * math.pi * k / 9; Vv, Fv = lathe([(0.012, 0.0), (0.001, 0.07 if k % 2 == 0 else 0.05)], 6, (0, 0, 0), 1)
        M.add('gold', Vv + np.array([math.sin(a) * (rxh + 0.02), cy0 + 0.05, cz - 0.004 + math.cos(a) * (rzh + 0.02)]), Fv, bone='head')
    M.part = 'Crown1'; band(M, 'gold', 0.04)
    for ang in (0.0, math.pi / 2):
        rr = []
        for t in np.linspace(0, 1, 9):
            a = math.pi * t; p_ = np.array([math.cos(a) * (rxh + 0.02) * (1 if ang == 0 else 0.0) + 0, cy0 + 0.04 + math.sin(a) * 0.075, cz - 0.004 + (math.cos(a) * (rzh + 0.02) if ang else 0)])
            rr.append((p_, (0.007, 0, 0), (0, 0.007, 0)))
        Vv, Fv = loft(rr, 6, False, False); M.add('gold', Vv, Fv, bone='head')
    Vv, Fv = lathe([(0.001, -0.02), (0.02, -0.006), (0.02, 0.006), (0.001, 0.02)], 10, (0, cy0 + 0.125, cz - 0.004), 1); M.add('gold', Vv, Fv, bone='head')
    M.part = 'Crown2'; band(M, 'gold', 0.014, 0.018)
    for k in range(26):
        a = 2 * math.pi * k / 26; side = 1 if k % 2 else -1
        Vv, Fv = lathe([(0.0, 0.0), (0.012, 0.025), (0.0, 0.055)], 6, (0, 0, 0), 1)
        Vv = place(Vv * np.array([0.6, 1, 1.0]), euler(0.3, a, side * 0.5), (math.sin(a) * (rxh + 0.022), cy0 + 0.012, cz - 0.004 + math.cos(a) * (rzh + 0.022)))
        M.add('cloth', Vv, Fv, color=(0.28, 0.5, 0.2), smooth=False, bone='head')
    M.part = 'Crown3'; band(M, 'gold', 0.04)
    for sg in (-1, 1):
        rr = []
        for t in np.linspace(0, 1, 8):
            p_ = np.array([sg * (rxh + 0.02 + 0.075 * math.sin(t * 1.9)), cy0 + 0.03 + 0.12 * t ** 1.3, cz - 0.004]); rr.append((p_, (0.0, 0, 0.018 * (1 - t) + 0.003), (0.018 * (1 - t) + 0.003, 0, 0)))
        Vv, Fv = loft(rr, 8, False, True); M.add('iron', Vv, Fv, color=(0.92, 0.9, 0.82), bone='head')
    M.part = 'Gem'
    Vv, Fv = lathe([(0.001, -0.014), (0.012, -0.004), (0.012, 0.004), (0.001, 0.016)], 8, (0, cy0 + 0.028, zf + 0.02), 1); M.add('body', Vv, Fv, color=(1, 1, 1), bone='head')

    # ------------------------------------------------------------ shoulders: plain / spiked / fur
    def limb(dn, x0, x1, grow, n, mat, color=None, wf=None):
        rings = []
        for x in np.linspace(x0, x1, n):
            m = np.array([d == dn for d in dom]) & (np.abs(V[:, 0] - x) < 0.012)
            if m.sum() < 3: continue
            p = V[m]; cy = (p[:, 1].min() + p[:, 1].max()) / 2; cz_ = (p[:, 2].min() + p[:, 2].max()) / 2
            rings.append(((x, cy, cz_), (0, (p[:, 1].max() - p[:, 1].min()) / 2 + grow, 0), (0, 0, (p[:, 2].max() - p[:, 2].min()) / 2 + grow)))
        if len(rings) > 2:
            Vv, Fv = loft(rings, 12, False, False); Fv = ofix(Vv, Fv, 'x'); M.add(mat, Vv, Fv, wfn=G.body_skin, color=color or (1, 1, 1))
    M.part = 'Pauld0'; G.pauldrons(M, 'steel')
    M.part = 'Pauld1'; G.pauldrons(M, 'steel')
    for sd, sg in (('L', 1), ('R', -1)):
        h = np.array(hp['upperarm01.' + sd])
        for k, (dx, dz) in enumerate(((0.0, 0.0), (0.0, 0.06), (0.0, -0.06))):
            Vv, Fv = lathe([(0.02, 0.0), (0.001, 0.12 if k == 0 else 0.07)], 7, (0, 0, 0), 1)
            Vv = place(Vv, euler(0.0, 0, -sg * 0.5), h + np.array([sg * 0.07, 0.09, dz])); M.add('steel', Vv, Fv, wfn=G.body_skin)
    M.part = 'Pauld2'
    for sd, sg in (('L', 1), ('R', -1)):
        h = np.array(hp['upperarm01.' + sd]); rg = np.random.RandomState(3 if sg > 0 else 4)
        for k in range(40):
            a = rg.rand() * 2 * math.pi; r_ = 0.06 + 0.05 * rg.rand()
            c = h + np.array([sg * 0.03 + math.cos(a) * r_ * 0.9, 0.05 + 0.03 * rg.rand(), math.sin(a) * r_])
            Vv, Fv = lathe([(0.02, -0.03), (0.026, 0.0), (0.001, 0.05)], 5, (0, 0, 0), 1)
            Vv = place(Vv, euler(rg.rand() - 0.5, 0, (rg.rand() - 0.5) * 1.2 - sg * 0.5), c); M.add('hair', Vv, Fv, color=(0.55, 0.45, 0.35), smooth=False, wfn=G.body_skin)

    # ------------------------------------------------------------ chest tiers (torso + arms)   0 plate / 1 mail / 2 leather / (3 cloth = none)
    M.part = 'Chest0'
    G.breastplate(M, 'hero', 'steel', 'gold'); G.vambraces(M, 'steel')
    for sd, sg in (('L', 1), ('R', -1)):
        a0 = hp['upperarm01.' + sd]; a1 = hp['lowerarm01.' + sd]
        limb('upperarm01.' + sd, a0[0] + sg * 0.01, a1[0] - sg * 0.01, 0.012, 5, 'steel')
    for k in range(5):     # faulds (hip lames)
        e = G.ext({'root', 'upperleg01.L', 'upperleg01.R'}, wy - 0.02 - 0.03 * k)
        if e:
            x0, x1, z0, z1 = e
            rr = [ring_xz(((x0 + x1) / 2, wy - 0.01 - 0.045 * k, (z0 + z1) / 2), (x1 - x0) / 2 + 0.03 + 0.004 * k, (z1 - z0) / 2 + 0.03 + 0.004 * k), ring_xz(((x0 + x1) / 2, wy - 0.045 - 0.045 * k, (z0 + z1) / 2), (x1 - x0) / 2 + 0.032 + 0.004 * k, (z1 - z0) / 2 + 0.032 + 0.004 * k)]
            Vv, Fv = loft(rr, 18, False, False); Fv = ofix(Vv, Fv); M.add('steel', Vv, Fv, wfn=G.body_skin)
    M.part = 'Chest1'
    ys = list(np.linspace(wy - 0.16, ny - 0.03, 11))
    r = G.shell_rings({'spine05', 'spine03', 'spine01', 'root', 'upperleg01.L', 'upperleg01.R'}, ys, 0.011)
    r = [(c, (np.array(u) * (1 + 0.1 * max(0, (wy - c[1]) / 0.16)), ), v) for c, u, v in [(c, u, v) for c, u, v in r]]
    r = [(c, u[0], np.array(v) * (1 + 0.12 * max(0, (wy - c[1]) / 0.16))) for c, u, v in r]
    Vv, Fv = loft(r, 20, False, False); Fv = ofix(Vv, Fv); M.add('iron', Vv, Fv, wfn=G.body_skin)
    Vv, Fv = loft([(r[0][0], np.array(r[0][1]) * 1.02, np.array(r[0][2]) * 1.02), (r[0][0] + np.array([0, 0.015, 0]), np.array(r[0][1]) * 1.02, np.array(r[0][2]) * 1.02)], 20, False, False); M.add('gold', Vv, Fv, wfn=G.body_skin)
    for sd, sg in (('L', 1), ('R', -1)):
        a0 = hp['upperarm01.' + sd]; a1 = hp['lowerarm01.' + sd]; a2 = hp['wrist.' + sd]
        limb('upperarm01.' + sd, a0[0] + sg * 0.01, a1[0] - sg * 0.01, 0.008, 5, 'iron')
        limb('lowerarm01.' + sd, a1[0] + sg * 0.01, a1[0] + (a2[0] - a1[0]) * 0.55, 0.008, 4, 'iron')
    e = G.ext({'root', 'spine05'}, wy)
    M.part = 'Chest2'
    ys = list(np.linspace(wy - 0.03, ny - 0.035, 9))
    r = G.shell_rings({'spine05', 'spine03', 'spine01', 'root'}, ys, 0.008)
    Vv, Fv = loft(r, 18, False, False); Fv = ofix(Vv, Fv); M.add('leather', Vv, Fv, color=(0.62, 0.42, 0.25), wfn=G.body_skin)
    for k in range(6):
        Vv, Fv = box((0, ys[2] + 0.04 * k, r[0][0][2] + 0.001 + (r[0][2][2] if len(r) else 0.1)), (0.006, 0.012, 0.004)); M.add('iron', Vv, Fv, smooth=False, wfn=G.body_skin)
    for sd, sg in (('L', 1), ('R', -1)):
        a1 = hp['lowerarm01.' + sd]; a2 = hp['wrist.' + sd]
        limb('lowerarm01.' + sd, a1[0] + sg * 0.01, a2[0] - sg * 0.01, 0.008, 4, 'leather', (0.55, 0.38, 0.22))

    # ------------------------------------------------------------ leg tiers
    def legshell(mat, grow, colr, upper_to=0.0, k0=0.0):
        for sd, sg in (('L', 1), ('R', -1)):
            kn = hp['lowerleg01.' + sd][1]; fy = hp['foot.' + sd][1]; hy = hp['upperleg01.' + sd][1]
            r1 = G.shell_rings({'upperleg01.' + sd, 'root'}, list(np.linspace(kn + 0.01, hy - 0.02 - upper_to, 7)), grow, side=sg)
            r2 = G.shell_rings({'lowerleg01.' + sd, 'upperleg01.' + sd}, list(np.linspace(fy + 0.06, kn - 0.01, 6)), grow * 0.9, side=sg)
            for rr in (r1, r2):
                if len(rr) > 3:
                    Vv, Fv = loft(rr, 14, False, False); Fv = ofix(Vv, Fv); M.add(mat, Vv, Fv, color=colr, wfn=G.body_skin)
    M.part = 'Legs0'; legshell('steel', 0.013, (1, 1, 1))
    for sd, sg in (('L', 1), ('R', -1)):
        k = hp['lowerleg01.' + sd][1]; Vv, Fv = lathe([(0.001, 0), (0.055, 0.0), (0.05, 0.03)], 10, (0, 0, 0), 2)
        c = G.shell_rings({'lowerleg01.' + sd}, [k + 0.03], 0.0, side=sg)
        if c: M.add('gold', place(Vv, euler(math.pi / 2), (c[0][0][0], k, c[0][0][2] + 0.07)), Fv, wfn=G.body_skin)
    M.part = 'Legs1'; legshell('iron', 0.008, (0.8, 0.8, 0.82))
    M.part = 'Legs2'; legshell('leather', 0.006, (0.5, 0.34, 0.2), upper_to=0.0)
    # ------------------------------------------------------------ boots
    def boot(mat, up, grow, colr, sole=True, toe=0.0):
        for sd, sg in (('L', 1), ('R', -1)):
            ys = list(np.linspace(0.012, ank + up, 7))
            r = G.shell_rings({'foot.' + sd, 'lowerleg01.' + sd}, ys, grow, side=sg)
            if len(r) > 3:
                Vv, Fv = loft(r, 14, True, False); Fv = ofix(Vv, Fv); M.add(mat, Vv, Fv, color=colr, wfn=G.body_skin)
            if toe > 0:
                e = G.ext({'foot.' + sd}, 0.03, tol=0.03, side=sg)
                if e:
                    x0, x1, z0, z1 = e
                    Vv, Fv = lathe([(0.001, 0), (0.04, 0.0), (0.035, 0.03)], 10, (0, 0, 0), 2)
                    M.add(mat, place(Vv * np.array([1, 1, 2.2]), euler(math.pi / 2), ((x0 + x1) / 2, 0.03, z1 + 0.0)), Fv, color=colr, bone='foot.' + sd)
    M.part = 'Boots0'; boot('steel', 0.1, 0.014, (1, 1, 1), toe=1)
    M.part = 'Boots1'; boot('leather', 0.2, 0.012, (0.28, 0.2, 0.14))
    M.part = 'Boots2'; boot('leather', 0.09, 0.007, (0.42, 0.3, 0.2))

    # ------------------------------------------------------------ chest emblems
    ty = (wy + ny) / 2 + 0.03; ez = (G.ext({'spine05', 'spine03'}, ty) or (0, 0, 0, 0.12))[3] + 0.034
    M.part = 'Emblem1'
    for dx, dy, sx, sy in ((0, 0, 0.012, 0.15), (0, 0.04, 0.07, 0.012)):
        Vv, Fv = box((dx, ty + dy, ez), (sx, sy, 0.006)); M.add('gold', Vv, Fv, smooth=False, bone='spine03')
    M.part = 'Emblem2'
    Vv, Fv = box((0, ty, ez), (0.07, 0.07, 0.006), euler(0, 0, math.pi / 4)); M.add('gold', Vv, Fv, smooth=False, bone='spine03')
    Vv, Fv = box((0, ty, ez + 0.004), (0.035, 0.035, 0.006), euler(0, 0, math.pi / 4)); M.add('cloth', Vv, Fv, color=(0.7, 0.08, 0.08), smooth=False, bone='spine03')
    M.part = 'Emblem3'
    for k in range(5):
        a = 2 * math.pi * k / 5
        Vv, Fv = box((math.sin(a) * 0.04, ty + math.cos(a) * 0.04, ez), (0.02, 0.06, 0.006), euler(0, 0, -a)); M.add('gold', Vv, Fv, smooth=False, bone='spine03')

    # ------------------------------------------------------------ cape, sword (3 lengths), shield
    M.part = 'Cape'; G.cape(M, (1, 1, 1))
    [G.sword(M, 'hero', lv=_l) for _l in range(3)]
    G.shield(M, 'hero'); M.part = None

    clips = [(n, d, (lambda t, fn=f: fn(t)), lp) for n, d, f, lp in anim.clips('hero')]
    n = M.write(f'{OUT}/king.glb', clips)
    print('king', len(base['V']), 'verts', n // 1024, 'KB')


if __name__ == '__main__':
    OUT = sys.argv[1]
    from PIL import Image
    a = np.asarray(Image.open(f'{OUT}/tex/eye_blue_c.png').convert('RGB')).astype(np.float32) / 255.0 if False else None
    build()
