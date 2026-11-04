# Builds a morphed MakeHuman base human (CC0 data) -> numpy dict used by the character builder.
import json, math, os, numpy as np
D = '/home/claude/eab71334-web/makehuman/makehuman/data/'
T = D + 'targets/'
_tc = {}

def load_target(rel):
    if rel in _tc: return _tc[rel]
    p = T + rel + '.target'
    idx = []; dv = []
    if os.path.exists(p):
        for l in open(p):
            if not l.strip() or l[0] == '#': continue
            t = l.split()
            idx.append(int(t[0])); dv.append([float(t[1]), float(t[2]), float(t[3])])
    r = (np.array(idx, int), np.array(dv, float).reshape(-1, 3)); _tc[rel] = r; return r

def apply(V0, rel, w):
    if abs(w) < 1e-4: return
    i, d = load_target(rel)
    if len(i): V0[i] += d * w

def mix3(v):  # min / avg / max weights for a 0..1 slider (0.5 = average)
    return max(0.0, 1 - 2 * v), 1 - abs(2 * v - 1), max(0.0, 2 * v - 1)

def macro(V0, g, age, muscle, weight, height, eth):
    gw = {'male': g, 'female': 1 - g}
    if age < 0.1875: aw = {'baby': 1 - age / 0.1875, 'child': age / 0.1875, 'young': 0, 'old': 0}
    elif age < 0.5: aw = {'baby': 0, 'child': 1 - (age - 0.1875) / 0.3125, 'young': (age - 0.1875) / 0.3125, 'old': 0}
    else: aw = {'baby': 0, 'child': 0, 'young': 1 - (age - 0.5) / 0.5, 'old': (age - 0.5) / 0.5}
    mm = dict(zip(('minmuscle', 'averagemuscle', 'maxmuscle'), mix3(muscle)))
    ww = dict(zip(('minweight', 'averageweight', 'maxweight'), mix3(weight)))
    hh = dict(zip(('minheight', None, 'maxheight'), mix3(height)))
    es = sum(eth.values()); eth = {k: v / es for k, v in eth.items()}
    for gk, gv in gw.items():
        for ak, av in aw.items():
            if gv * av < 1e-4: continue
            for mk, mv in mm.items():
                for wk, wv in ww.items():
                    w = gv * av * mv * wv
                    if w < 1e-4: continue
                    apply(V0, f'macrodetails/universal-{gk}-{ak}-{mk}-{wk}', w)
                    for hk in ('minheight', 'maxheight'):
                        if hh[hk] > 1e-4: apply(V0, f'macrodetails/height/{gk}-{ak}-{mk}-{wk}-{hk}', w * hh[hk])
            for ek, ev in eth.items():
                apply(V0, f'macrodetails/{ek}-{gk}-{ak}', ev * gv * av)

def detail(V0, name, v):
    # name like 'nose/nose-width1' (decr/incr), or 'eyes/eye-scale' (applies l- and r-)
    d, n = name.split('/')
    sides = [n]
    if n.startswith('eye-') or n.startswith('cheek-') or n.startswith('ear-'):
        sides = ['l-' + n, 'r-' + n]
    for s in sides:
        suf = f'{d}/{s}-' + ('incr' if v > 0 else 'decr')
        if os.path.exists(T + suf + '.target'): apply(V0, suf, abs(v))
        elif os.path.exists(T + f'{d}/{s}.target'): apply(V0, f'{d}/{s}', abs(v))

CORE = ['root', 'spine05', 'spine03', 'spine01', 'neck01', 'head', 'clavicle.L', 'clavicle.R', 'upperarm01.L', 'upperarm01.R',
        'lowerarm01.L', 'lowerarm01.R', 'wrist.L', 'wrist.R', 'upperleg01.L', 'upperleg01.R', 'lowerleg01.L', 'lowerleg01.R', 'foot.L', 'foot.R']

def build(spec, head_cell=0.0, body_cell=0.024):
    V0 = []; faces = []; grp = None
    for l in open(D + '3dobjs/base.obj'):
        if l.startswith('v '): V0.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('g '): grp = l.split()[1]
        elif l.startswith('f ') and grp == 'body':
            idx = [int(t.split('/')[0]) - 1 for t in l.split()[1:]]
            for i in range(1, len(idx) - 1): faces.append([idx[0], idx[i], idx[i + 1]])
    V0 = np.array(V0); faces = np.array(faces)
    macro(V0, spec.get('g', 1.0), spec.get('age', 0.5), spec.get('muscle', 0.5), spec.get('weight', 0.5), spec.get('height', 0.5), spec.get('eth', {'african': 0.33, 'asian': 0.33, 'caucasian': 0.34}))
    for k, v in spec.get('detail', {}).items(): detail(V0, k, v)
    sk = json.load(open(D + 'rigs/default.mhskel')); bones = sk['bones']; joints = sk['joints']
    def core_of(b):
        while b is not None and b not in CORE: b = bones[b]['parent']
        return b or 'root'
    W = json.load(open(D + 'rigs/default_weights.mhw'))['weights']
    infl = [dict() for _ in range(len(V0))]; raw = [dict() for _ in range(len(V0))]
    for b, lst in W.items():
        c = core_of(b)
        for vi, w in lst:
            if vi < len(V0):
                infl[vi][c] = infl[vi].get(c, 0) + w; raw[vi][b] = w
    S = 0.1
    Vm = V0 * S
    used0 = np.unique(faces)
    ymin = Vm[used0, 1].min()
    Vm[:, 1] -= ymin
    def jpos(n): return Vm[joints[n]].mean(axis=0)
    hp = {b: jpos(bones[b]['head']) for b in CORE}
    # ---- decimate: fine around head/neck, coarse elsewhere
    dom0 = {}
    for i in used0:
        d = infl[i]; dom0[i] = max(d.items(), key=lambda kv: kv[1])[0] if d else 'root'
    key = {}; cid = -np.ones(len(V0), dtype=np.int64)
    for i in used0:
        face = dom0[i] in ('head',) or (dom0[i] == 'neck01')
        cell = head_cell if face else (0.034 if dom0[i].startswith('wrist') else body_cell)
        if face and cell <= 0: k = ('v', int(i))
        else: k = tuple(np.floor(Vm[i] / cell).astype(int)) + ((1 if Vm[i][0] > hp['root'][0] else 0) if not dom0[i].startswith('wrist') else 2, dom0[i] in ('head', 'neck01'), dom0[i].startswith('wrist'))
        if k not in key: key[k] = len(key)
        cid[i] = key[k]
    nc = len(key); V2 = np.zeros((nc, 3)); cnt = np.zeros(nc); infl2 = [dict() for _ in range(nc)]; raw2 = [None] * nc; rep = -np.ones(nc, int)
    for i in used0:
        c = cid[i]; V2[c] += Vm[i]; cnt[c] += 1
        for b, w in infl[i].items(): infl2[c][b] = infl2[c].get(b, 0) + w
        if rep[c] < 0: rep[c] = i; raw2[c] = raw[i]
    V2 /= cnt[:, None]
    f2 = cid[faces]; keep = (f2[:, 0] != f2[:, 1]) & (f2[:, 1] != f2[:, 2]) & (f2[:, 0] != f2[:, 2]); f2 = f2[keep]
    order = []; seen = set()
    cpar = {b: (None if b == 'root' else core_of(bones[b]['parent'])) for b in CORE}
    def add(b):
        if b in seen: return
        if cpar[b]: add(cpar[b])
        seen.add(b); order.append(b)
    for b in CORE: add(b)
    bidx = {b: i for i, b in enumerate(order)}
    J = np.zeros((nc, 4), np.uint16); WT = np.zeros((nc, 4), np.float32); dom = ['root'] * nc
    for i, d in enumerate(infl2):
        if not d: d = {'root': 1.0}
        top = sorted(d.items(), key=lambda kv: -kv[1])[:4]; s = sum(w for _, w in top); dom[i] = top[0][0]
        for k, (b, w) in enumerate(top): J[i, k] = bidx[b]; WT[i, k] = w / s
    # ---- eyes (MakeHuman proxy mesh fitted to this face)
    eyes = fit_eyes(Vm, ymin, spec.get('eye_poly', 'high-poly'))
    return dict(V=V2, F=f2, J=J, W=WT, dom=dom, hp=hp, order=order, parents=cpar, raw=raw2, eyes=eyes, spec=spec, Vfull=Vm, joints=joints)

def fit_eyes(Vm, ymin, poly):
    base = D + f'eyes/{poly}/{poly}'
    lines = open(base + '.mhclo').read().splitlines()
    scale = {}; ent = []; inverts = False
    for l in lines:
        t = l.split()
        if not t: continue
        if t[0] in ('x_scale', 'y_scale', 'z_scale'): scale[t[0][0]] = (int(t[1]), int(t[2]), float(t[3]))
        if t[0] == 'verts': inverts = True; continue
        if inverts:
            try:
                if len(t) == 1: ent.append((int(t[0]),))
                elif len(t) == 9: ent.append((int(t[0]), int(t[1]), int(t[2]), float(t[3]), float(t[4]), float(t[5]), float(t[6]), float(t[7]), float(t[8])))
                else: break
            except ValueError: break
    s = {}
    for ax, i in (('x', 0), ('y', 1), ('z', 2)):
        a_, b_, den = scale[ax]; s[i] = abs(Vm[a_][i] - Vm[b_][i]) / 0.1 / den
    P = []
    for e in ent:
        if len(e) == 1: P.append(Vm[e[0]])
        else:
            P.append(Vm[e[0]] * e[3] + Vm[e[1]] * e[4] + Vm[e[2]] * e[5] + np.array([e[6] * s[0], e[7] * s[1], e[8] * s[2]]) * 0.1)
    P = np.array(P)
    # obj topology + uv
    pos = []; vt = []; fs = []; uvs = []
    for l in open(base + '.obj'):
        if l.startswith('v '): pos.append(1)
        elif l.startswith('vt '): vt.append([float(x) for x in l.split()[1:3]])
        elif l.startswith('f '):
            idx = [tuple(int(q) - 1 for q in t.split('/')[:2]) for t in l.split()[1:]]
            for i in range(1, len(idx) - 1): fs.append([idx[0], idx[i], idx[i + 1]])
    m = {}; Vo = []; UV = []; F = []
    for tri in fs:
        r = []
        for vi, ti in tri:
            if (vi, ti) not in m: m[(vi, ti)] = len(Vo); Vo.append(P[vi]); UV.append([vt[ti][0], 1 - vt[ti][1]])
            r.append(m[(vi, ti)])
        F.append(r)
    return dict(V=np.array(Vo), F=np.array(F), UV=np.array(UV))
