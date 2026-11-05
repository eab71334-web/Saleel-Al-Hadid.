import sys, math, numpy as np
sys.path.insert(0, '/tmp/mh2')
import mhlib as L
from mhlib import *
from scipy.spatial import cKDTree
V = F = Jb = Wb = dom = hp = order = tree = None
PARENTS = {}
FK_R = {}; FK_P = {}
def use(base):
    global V, F, Jb, Wb, dom, hp, order, tree
    global PARENTS
    V = base['V']; F = base['F']; Jb = base['J']; Wb = base['W']; dom = base['dom']; hp = base['hp']; order = base['order']; PARENTS = base['parents']
    tree = cKDTree(V)

def setpose(kind, params=None):
    import anim
    p = dict(anim.DEF, **anim.guard(kind)) if params is None else dict(anim.DEF, **params); P, _ = anim.to_pose(p, 'archer' if kind == 'archer' else 'melee')
    FK_R.clear(); FK_P.clear()
    for b in order:
        par = PARENTS[b]; Rl = euler(*P.get(b, (0, 0, 0)))
        if par: FK_R[b] = FK_R[par] @ Rl; FK_P[b] = FK_P[par] + FK_R[par] @ (np.array(hp[b]) - np.array(hp[par]))
        else: FK_R[b] = Rl; FK_P[b] = np.array(hp[b], float)
def to_rest(bone, Vp):
    return np.array(hp[bone]) + (np.array(Vp) - FK_P[bone]) @ FK_R[bone]
def aim_y(T):
    T = np.array(T, float); T /= np.linalg.norm(T); y = np.array([0, 1.0, 0]); ax = np.cross(y, T)
    s = np.linalg.norm(ax); c = float(y @ T)
    if s < 1e-6: return np.eye(3)
    ax /= s; K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K

def body_skin(p):
    _, i = tree.query(p)
    return [(order[int(Jb[i, k])], float(Wb[i, k])) for k in range(4) if Wb[i, k] > 0]
def ext(domset, y, tol=0.03, side=None):
    m = np.array([d in domset for d in dom]) & (np.abs(V[:, 1] - y) < tol)
    if side is not None: m &= (V[:, 0] * side > 0)
    if m.sum() < 3: return None
    p = V[m]; return p[:, 0].min(), p[:, 0].max(), p[:, 2].min(), p[:, 2].max()

def shell_rings(domset, ys, grow, side=None):
    rings = []
    for y in ys:
        e = ext(domset, y, side=side)
        if e is None: continue
        x0, x1, z0, z1 = e
        rings.append(ring_xz(((x0 + x1) / 2, y, (z0 + z1) / 2), (x1 - x0) / 2 + grow, (z1 - z0) / 2 + grow))
    return rings

def breastplate(M, kind, mat='steel', trim='gold'):
    wy = hp['root'][1]; ny = hp['neck01'][1]
    ys = list(np.linspace(ny - 0.03, wy + 0.03, 9))
    r = shell_rings({'spine05', 'spine03', 'spine01', 'root'}, ys, 0.014)
    if len(r) > 3:
        Vv, Ff = loft(r, 16, False, False)
        M.add(mat, Vv, Ff, wfn=body_skin)
        # trim bands at top and bottom
        for rr, mname in ((r[0], trim), (r[-1], trim)):
            c, u, v = rr
            Vv, Ff = loft([(c + np.array([0, -0.012, 0]), np.array(u) * 1.03, np.array(v) * 1.03), (c + np.array([0, 0.012, 0]), np.array(u) * 1.03, np.array(v) * 1.03)], 16)
            M.add(mname, Vv, Ff, wfn=body_skin)
    # belt
    e = ext({'root', 'spine05'}, wy + 0.0)
    if e:
        x0, x1, z0, z1 = e
        Vv, Ff = loft([ring_xz(((x0 + x1) / 2, wy - 0.025, (z0 + z1) / 2), (x1 - x0) / 2 + 0.02, (z1 - z0) / 2 + 0.02), ring_xz(((x0 + x1) / 2, wy + 0.035, (z0 + z1) / 2), (x1 - x0) / 2 + 0.02, (z1 - z0) / 2 + 0.02)], 16)
        M.add('leather', Vv, Ff, wfn=body_skin)
        Vv, Ff = box(((x0 + x1) / 2, wy, z1 + 0.03), (0.06, 0.06, 0.02)); M.add('gold', Vv, Ff, smooth=False, bone='root')

def pauldrons(M, mat='steel', col=(1, 1, 1)):
    for sd, sg in (('L', 1), ('R', -1)):
        h = np.array(hp['upperarm01.' + sd])
        for k, rad in enumerate((0.105, 0.088, 0.072)):
            prof = [(rad * math.cos(a), rad * 0.75 * math.sin(a)) for a in np.linspace(0.0, math.pi / 2, 7)]
            Vv, Ff = lathe(prof, 14, (0, 0, 0))
            Vv = place(Vv, euler(0, 0, -sg * (0.35 + 0.1 * k)), h + np.array([sg * (0.03 + 0.012 * k), 0.035 - 0.032 * k, 0]))
            M.add(mat, Vv, Ff, color=col, wfn=body_skin)

def vambraces(M, mat='steel'):
    for sd, sg in (('L', 1), ('R', -1)):
        a = hp['lowerarm01.' + sd]; w = hp['wrist.' + sd]
        # rings perpendicular to x
        xs = np.linspace(a[0] + sg * 0.01, w[0] - sg * 0.01, 5)
        rings = []
        for x in xs:
            m = np.array([d in ('lowerarm01.' + sd,) for d in dom]) & (np.abs(V[:, 0] - x) < 0.012)
            if m.sum() < 3: continue
            p = V[m]; cy = (p[:, 1].min() + p[:, 1].max()) / 2; cz = (p[:, 2].min() + p[:, 2].max()) / 2
            ry = (p[:, 1].max() - p[:, 1].min()) / 2 + 0.012; rz = (p[:, 2].max() - p[:, 2].min()) / 2 + 0.012
            rings.append(((x, cy, cz), (0, ry, 0), (0, 0, rz)))
        if len(rings) > 2:
            Vv, Ff = loft(rings, 12, False, False); M.add(mat, Vv, Ff, wfn=body_skin)

def greaves(M, mat='steel'):
    for sd, sg in (('L', 1), ('R', -1)):
        k = hp['lowerleg01.' + sd][1]; a = hp['foot.' + sd][1]
        ys = np.linspace(k - 0.02, a + 0.07, 6)
        r = shell_rings({'lowerleg01.' + sd, 'upperleg01.' + sd}, ys, 0.011, side=sg)
        if len(r) > 3:
            Vv, Ff = loft(r, 12, False, False); M.add(mat, Vv, Ff, wfn=body_skin)
            c = r[-1][0]
            Vv, Ff = lathe([(0.001, 0), (0.05, 0.0), (0.05, 0.03)], 10, (c[0], k, c[2] + 0.04), 2)
            M.add('gold', place(Vv - np.array([c[0], k, c[2] + 0.04]), euler(math.pi / 2), (c[0], k, c[2] + 0.07)), Ff, bone='lowerleg01.' + sd)

def helmet(M, kind):
    h = hp['head']
    ys = V[:, 1]; hm = np.array([d == 'head' for d in dom])
    top = V[hm, 1].max(); xs = V[hm, 0]; zs = V[hm, 2]
    rx_ = (xs.max() - xs.min()) / 2 + 0.012; rz_ = (zs.max() - zs.min()) / 2 + 0.012
    cz = (zs.max() + zs.min()) / 2
    y0 = h[1] + 0.085; y1 = top + 0.018
    rings = []
    for t in np.linspace(0, 1, 8):
        y = y0 + (y1 - y0) * t
        s = math.sqrt(max(1 - t ** 2.2, 0.02)) if t < 1 else 0.02
        rings.append(ring_xz((h[0], y, cz - 0.004), rx_ * (0.93 + 0.1 * (1 - t)) * s + 0.001, rz_ * (0.96 + 0.1 * (1 - t)) * s + 0.001))
    Vv, Ff = loft(rings, 16, False, True)
    mat = 'steel' if kind != 'archer' else 'leather'
    M.add(mat, Vv, Ff, bone='head')
    if kind == 'archer':
        # hood back drape
        Vv, Ff = loft([ring_xz((h[0], y0 - 0.02, cz - 0.03), rx_ * 0.9, rz_ * 1.0), ring_xz((h[0], y0 - 0.14, cz - 0.07), rx_ * 0.7, rz_ * 0.9)], 12, False, True)
        M.add('leather', Vv, Ff, color=(0.35, 0.55, 0.3), bone='head'); return
    # brim ring and nasal guard
    Vv, Ff = loft([ring_xz((h[0], y0 - 0.006, cz - 0.004), rx_ * 1.04, rz_ * 1.06), ring_xz((h[0], y0 + 0.014, cz - 0.004), rx_ * 1.04, rz_ * 1.06)], 16)
    M.add('gold' if kind == 'hero' else 'iron', Vv, Ff, bone='head')
    zf = zs.max() + 0.012
    Vv, Ff = box((h[0], y0 - 0.045, zf), (0.026, 0.1, 0.012)); M.add('steel', Vv, Ff, smooth=False, bone='head')
    # cheek guards
    for sg in (-1, 1):
        Vv, Ff = box((h[0] + sg * (rx_ * 0.98), y0 - 0.05, cz + 0.0), (0.014, 0.1, 0.13)); M.add('steel', Vv, Ff, smooth=False, bone='head')
    if kind == 'hero':
        for k in range(7):
            a = k * 2 * math.pi / 7
            Vv, Ff = lathe([(0.016, 0), (0.0, 0.07)], 6, (0, 0, 0))
            M.add('gold', Vv + np.array([h[0] + math.sin(a) * rx_ * 0.98, y1 - 0.025, cz + math.cos(a) * rz_ * 0.98]), Ff, bone='head')
    else:
        # crest
        Vv, Ff = box((h[0], y1 + 0.015, cz), (0.018, 0.05, 0.2)); M.add('cloth', Vv, Ff, color=(0.75, 0.1, 0.1), smooth=False, bone='head')

def sword(M, kind, bone='wrist.R', lv=0):
    Lb = (0.78 if kind != 'hero' else 0.95) * (1.0, 1.22, 1.45)[lv]
    M.part = 'Sword%d' % lv
    pw = FK_P[bone]; Rq = aim_y((0.1, 0.92, 0.38))
    def put(Vc, Ff, mat, col=(1, 1, 1), smooth=True):
        Vp = pw + np.array([0.0, 0.0, 0.03]) + (np.array(Vc) @ Rq.T)
        M.add(mat, to_rest(bone, Vp), Ff, color=col, bone=bone, smooth=smooth)
    w = np.zeros(3)
    Vv, Ff = lathe([(0.016, -0.11), (0.018, -0.05), (0.018, 0.07), (0.014, 0.075)], 10, w, 1); put(Vv, Ff, 'leather')
    for k in range(5):
        Vv, Ff = lathe([(0.0195, -0.09 + k * 0.035), (0.0195, -0.08 + k * 0.035)], 10, w, 1); put(Vv, Ff, 'iron')
    Vv, Ff = lathe([(0.001, -0.15), (0.03, -0.14), (0.034, -0.12), (0.025, -0.1), (0.001, -0.1)], 12, w, 1); put(Vv, Ff, 'gold')
    for sg in (-1, 1):
        rings = [(w + np.array([sg * x, 0.075 + 0.015 * (x / 0.13) ** 2, 0]), (0, 0.011, 0), (0, 0, 0.016)) for x in np.linspace(0.0, 0.13, 5)]
        Vv, Ff = loft(rings, 8, True, True); put(Vv, Ff, 'gold')
    Vv, Ff = box(w + np.array([0, 0.078, 0]), (0.05, 0.03, 0.04)); put(Vv, Ff, 'gold', smooth=False)
    rings = [(w + np.array([0, 0.09, 0]), (0.034, 0, 0), (0, 0, 0.0055))]
    for t in (0.2, 0.5, 0.8, 0.93, 1.0):
        wd = 0.034 - 0.012 * t if t < 0.93 else 0.034 * (1.0 - t) * 6 + 0.002
        rings.append((w + np.array([0, 0.09 + Lb * t, 0]), (wd, 0, 0), (0, 0, 0.0055 * (1 - 0.3 * t))))
    Vv, Ff = loft(rings, 6, True, True); put(Vv, Ff, 'steel' if (kind != 'hero' and lv < 2) else 'gold')
    Vv, Ff = box(w + np.array([0, 0.09 + Lb * 0.42, 0.0058]), (0.009, Lb * 0.72, 0.002)); put(Vv, Ff, 'iron', smooth=False)

def shield(M, kind):
    M.part = 'Shield'
    bone = 'lowerarm01.L'
    a = FK_P[bone]; wr = FK_P['wrist.L']; mid = (a + wr) / 2
    cpos = mid + np.array([0.0, 0.0, 0.13])
    s = 0.62
    poly = [(-0.2 * s, 0.25 * s), (0.2 * s, 0.25 * s), (0.22 * s, 0.0), (0.12 * s, -0.22 * s), (0.0, -0.38 * s), (-0.12 * s, -0.22 * s), (-0.22 * s, 0.0)]
    poly = [(x * 1.25, y * 1.25) for x, y in poly]
    face = (0.5, 0.08, 0.08) if kind != 'hero' else (0.1, 0.12, 0.45)
    Rt = euler(0.0, 0.25, 0.0)
    def put(Vc, Ff, mat, col=(1, 1, 1), smooth=False):
        Vp = cpos + np.array(Vc) @ Rt.T
        M.add(mat, to_rest(bone, Vp), Ff, color=col, smooth=smooth, bone=bone)
    Vv, Ff = extrude(poly, 0.03); put(Vv, Ff, 'wood', (0.85, 0.85, 0.85))
    Vv, Ff = extrude([(x * 0.93, y * 0.93) for x, y in poly], 0.012, 0.018); put(Vv, Ff, 'cloth', face)
    n = len(poly)
    for i in range(n):
        p0 = np.array(poly[i]); p1 = np.array(poly[(i + 1) % n])
        m = (p0 + p1) / 2; d_ = p1 - p0; ln = np.linalg.norm(d_); ang = math.atan2(d_[1], d_[0])
        Vv, Ff = box((m[0], m[1], 0.012), (ln, 0.02, 0.026), euler(0, 0, ang)); put(Vv, Ff, 'steel')
    Vv, Ff = lathe([(0.001, 0.0), (0.06, 0.0), (0.056, 0.02), (0.035, 0.04), (0.001, 0.05)], 14, (0, 0, 0.03), 2); put(Vv, Ff, 'gold', smooth=True)
    Vv, Ff = box((0, -0.02, 0.026), (0.03, 0.4, 0.008)); put(Vv, Ff, 'steel')
    Vv, Ff = box((0, 0.05, 0.026), (0.3, 0.03, 0.008)); put(Vv, Ff, 'steel')

def cape(M, col):
    wy = hp['neck01'][1]; z = V[:, 2].min() + 0.0
    zb = ext({'spine03', 'spine01', 'spine05'}, hp['spine01'][1])
    zb = zb[2] if zb else -0.12
    top = wy - 0.02; bot = hp['root'][1] - 0.5
    rings = []
    for t in np.linspace(0, 1, 6):
        y = top + (bot - top) * t
        rings.append(((0, y, zb - 0.04 - 0.04 * t), (0.14 + 0.15 * t, 0, 0), (0, 0, 0.012)))
    Vv, Ff = loft(rings, 8, False, False)
    M.add('cloth', Vv, Ff, color=col, bone='spine01', smooth=True)

def rest_blend(Vp, wts):
    A = sum(w * FK_R[b] for b, w in wts); t = sum(w * (FK_P[b] - FK_R[b] @ np.array(hp[b])) for b, w in wts)
    return np.linalg.solve(A, np.array(Vp) - t)

def bow(M):
    import anim
    dp = anim.draw_pose(); anim.FRAMES.clear()
    aim = np.array([0.0, dp['aimy'], 1.0]); aim /= np.linalg.norm(aim); up = np.array([0.0, 1.0, -dp['aimy']]); up /= np.linalg.norm(up)
    setpose('archer', dp)
    for side in ('L', 'R'):
        Rw = FK_R['wrist.' + side]; anim.FRAMES['wrist.' + side] = ((Rw.T @ up).tolist(), (Rw.T @ aim).tolist())
    setpose('archer', dp)
    side_v = np.cross(up, aim)
    Gp = FK_P['wrist.L'] + 0.035 * aim
    mid = FK_P['wrist.R'] + 0.07 * aim
    # --- bow stave (wood) bound to the bow hand
    rings = []
    for t in np.linspace(-1, 1, 13):
        c = Gp + up * 0.52 * t - aim * 0.11 * t * t
        w = 0.014 * (1.15 - abs(t) * 0.55)
        rings.append((c, side_v * w, aim * w * 1.15))
    Vv, Ff = loft(rings, 8, True, True); M.add('wood', to_rest('wrist.L', Vv), Ff, bone='wrist.L')
    Vv, Ff = box(Gp, (0.03, 0.14, 0.035), None); 
    for k, (a_, b_) in enumerate(((0.52, -0.11),)):
        pass
    # grip wrap
    rr = [(Gp + up * y, side_v * 0.019, aim * 0.021) for y in (-0.07, 0.07)]
    Vg, Fg = loft(rr, 8, True, True); M.add('leather', to_rest('wrist.L', Vg), Fg, bone='wrist.L')
    # --- string: tips on the bow, middle follows the string hand
    tipT = Gp + up * 0.52 - aim * 0.11; tipB = Gp - up * 0.52 - aim * 0.11
    pts = [tipT + (mid - tipT) * k / 5 for k in range(6)] + [mid + (tipB - mid) * k / 5 for k in range(1, 6)]
    rings = [(p_, side_v * 0.0035, aim * 0.0035) for p_ in pts]
    Vs, Fs = loft(rings, 4, False, False)
    # per-vertex blend: weight along the polyline
    verts = []; jw = []
    n = len(pts)
    for k, p_ in enumerate(pts):
        r = abs(k - 5) / 5.0               # 0 at the middle -> 1 at tips
        wR = 1.0 - r; wL = r
        for q in range(4):
            wts = [('wrist.L', wL), ('wrist.R', wR)]; wts = [(b, w) for b, w in wts if w > 1e-4]
            jw.append(wts)
    Vrest = np.array([rest_blend(Vs[i], jw[i]) for i in range(len(Vs))])
    M.add('cloth', Vrest, Fs, color=(0.93, 0.9, 0.78), smooth=True, jw=jw)
    # --- nocked arrow, rigid on the string hand
    L = float((Gp + aim * 0.13 - mid) @ aim)
    rings = [(mid + aim * l, side_v * 0.0045, up * 0.0045) for l in np.linspace(0.0, L - 0.05, 4)]
    Va, Fa = loft(rings, 6, True, True); M.add('wood', to_rest('wrist.R', Va), Fa, bone='wrist.R')
    Vh, Fh = lathe([(0.001, 0.0), (0.011, 0.0), (0.001, 0.07)], 6, np.zeros(3), 1)
    # arrow head: lathe along +y -> rotate to aim
    Rq = aim_y(aim); Vh = (Vh @ Rq.T) + (mid + aim * (L - 0.05)); M.add('steel', to_rest('wrist.R', Vh), Fh, bone='wrist.R')
    for k in range(3):
        a = 2 * math.pi * k / 3
        off = (side_v * math.cos(a) + up * math.sin(a)) * 0.012
        Vf, Ff = box(mid + aim * 0.05 + off, (0.003, 0.003, 0.05), None) if False else (None, None)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        d_ = side_v * math.cos(a) + up * math.sin(a)
        c0 = mid + aim * 0.045
        Vf = np.array([c0, c0 + d_ * 0.022, c0 + d_ * 0.022 + aim * 0.06, c0 + aim * 0.06]); Ff = np.array([[0, 1, 2], [0, 2, 3], [0, 2, 1], [0, 3, 2]])
        M.add('cloth', to_rest('wrist.R', Vf), Ff, color=(0.8, 0.15, 0.12), smooth=False, bone='wrist.R')

def quiver(M):
    s = np.array(hp['spine01']) + np.array([0.03, -0.16, -0.17])
    Vv, Ff = lathe([(0.001, -0.25), (0.045, -0.25), (0.05, 0.0), (0.056, 0.2), (0.001, 0.2)], 10, s, 1)
    M.add('leather', place(Vv - s, euler(0.1, 0, 0.25), s), Ff, bone='spine01')
    for k in range(5):
        Vv, Ff = lathe([(0.004, 0.2), (0.004, 0.45)], 5, s + np.array([-0.02 + k * 0.012, 0.0, 0.01 * (k % 2)]), 1)
        M.add('wood', place(Vv - s, euler(0.1, 0, 0.25), s), Ff, bone='spine01')
        Vv, Ff = box(s + np.array([-0.02 + k * 0.012, 0.47, 0.01 * (k % 2)]), (0.03, 0.06, 0.004)); M.add('cloth', place(Vv - s, euler(0.1, 0, 0.25), s), Ff, color=(0.9, 0.85, 0.7), smooth=False, bone='spine01')

def villager(M):
    h = hp['head']
    Vv, Ff = lathe([(0.2, 0.0), (0.205, 0.012), (0.1, 0.03), (0.08, 0.1), (0.001, 0.105)], 16, (h[0], h[1] + 0.1, h[2]), 1)
    M.add('cloth', Vv, Ff, color=(0.85, 0.72, 0.4), bone='head')
    wy = hp['root'][1]
    e = ext({'root', 'spine05'}, wy)
    if e:
        x0, x1, z0, z1 = e
        Vv, Ff = loft([ring_xz(((x0 + x1) / 2, wy - 0.02, (z0 + z1) / 2), (x1 - x0) / 2 + 0.014, (z1 - z0) / 2 + 0.014), ring_xz(((x0 + x1) / 2, wy + 0.03, (z0 + z1) / 2), (x1 - x0) / 2 + 0.014, (z1 - z0) / 2 + 0.014)], 14)
        M.add('leather', Vv, Ff, wfn=body_skin)

def eyes(M):
    h = hp['head']
    for sg in (-1, 1):
        Vv, Ff = box((h[0] + sg * 0.036, h[1] + 0.085, h[2] + 0.11), (0.02, 0.012, 0.01)); M.add('iron', Vv, Ff, smooth=False, bone='head')

