# Professional-style procedural animation set for the MakeHuman rig (keyframed in "pose parameter" space, eased, with
# anticipation / follow-through / overlap). Returns clips as (name, duration, fn(t)->(pose, root_offset), loop).
import math
import numpy as np
ARM = 1.2
PI = math.pi

def sm(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def ease_out(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def ease_in(x): x = max(0.0, min(1.0, x)); return x ** 3

DEF = dict(ry=0, dx=0, dy=0, dz=0, rroll=0, rpitch=0,
           lean=0, yaw=0, roll=0, hpitch=0, hyaw=0, hroll=0,
           raf=0, rao=0, rae=0, rat=0, laf=0, lao=0, lae=0, lat=0,
           rlf=0, rlk=0, rlp=0, rlo=0, llf=0, llk=0, llp=0, llo=0, shr=0, shl=0, wr=0, wl=0,
           ikw=0, aimy=0.0, hr=0.0, tl0=0, tl1=0, tl2=0, tr0=0, tr1=0, tr2=0)

def kf(t, keys):
    """keys: [(time, {param: value})...] -> eased interpolation of every parameter present in any key"""
    ks = sorted(keys, key=lambda k: k[0])
    if t <= ks[0][0]: return dict(DEF, **ks[0][1])
    if t >= ks[-1][0]: return dict(DEF, **ks[-1][1])
    for i in range(len(ks) - 1):
        t0, a = ks[i]; t1, b = ks[i + 1]
        if t0 <= t <= t1:
            u = sm((t - t0) / max(t1 - t0, 1e-6))
            out = dict(DEF)
            for k in set(a) | set(b):
                out[k] = a.get(k, 0) * (1 - u) + b.get(k, 0) * u
            return out

def arm_euler(side, fwd, out, elbow, twist):
    """upper arm + forearm local eulers. side 'L' (+x) or 'R' (-x)."""
    beta = ARM - out                      # angle below horizontal
    a = math.atan(math.tan(fwd) * math.sin(beta)) if abs(fwd) < 1.5 and abs(beta) > 0.05 else fwd * math.sin(max(beta, 0.0))
    if abs(beta) <= 0.05: a = fwd
    s = -1 if side == 'L' else 1
    up = (twist, -s * -1 * a * (-1) if False else (-a if side == 'L' else a), s * beta)
    # left arm: forward = negative y rotation; z drop negative.  right arm: mirrored
    up = (twist, (-a if side == 'L' else a), (-beta if side == 'L' else beta))
    fa = (0, (-elbow if side == 'L' else elbow), 0)
    return up, fa

def _to_pose(p, kind='melee'):
    P = {}
    def add(b, x=0, y=0, z=0):
        c = P.get(b, (0, 0, 0)); P[b] = (c[0] + x, c[1] + y, c[2] + z)
    add('root', p['rpitch'], p['ry'], p['rroll'])
    add('spine05', p['lean'] * 0.35, p['yaw'] * 0.3, p['roll'] * 0.3)
    add('spine03', p['lean'] * 0.4, p['yaw'] * 0.4, p['roll'] * 0.4)
    add('spine01', p['lean'] * 0.25, p['yaw'] * 0.3, p['roll'] * 0.3)
    add('neck01', p['hpitch'] * 0.35, p['hyaw'] * 0.4, p['hroll'] * 0.4)
    add('head', p['hpitch'] * 0.65, p['hyaw'] * 0.6, p['hroll'] * 0.6)
    add('clavicle.L', 0, 0, p['shl']); add('clavicle.R', 0, 0, -p['shr'])
    for side, pre in (('R', 'r'), ('L', 'l')):
        up, fa = arm_euler(side, p[pre + 'af'], p[pre + 'ao'], p[pre + 'ae'], p[pre + 'at'])
        add('upperarm01.' + side, *up); add('lowerarm01.' + side, *fa)
        add('wrist.' + side, 0, 0, (p['wr'] if side == 'R' else p['wl']))
    for side, pre in (('R', 'rl'), ('L', 'll')):
        add('upperleg01.' + side, -p[pre + 'f'], 0, (p[pre + 'o'] if side == 'L' else -p[pre + 'o']))
        add('lowerleg01.' + side, p[pre + 'k'], 0, 0)
        add('foot.' + side, p[pre + 'p'], 0, 0)
    return P, [p['dx'], p['dy'], p['dz']]

# stance helpers --------------------------------------------------------------------------

# ---------------------------------------------------------------- two-bone arm IK (archers) --------------------------
_B = None           # dict(hp=..., parents=..., order=...) of the character being exported
FRAMES = {}         # bone -> (up_local, fwd_local) of bow/arrow in wrist bone space, set by gear.bow()
def set_base(base):
    _GC.clear()
    global _B
    _B = dict(hp={k: np.array(v, float) for k, v in base['hp'].items()}, parents=base['parents'], order=base['order'])

def _rot(ax, a):
    c, s_ = math.cos(a), math.sin(a)
    return [np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]]), np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]]), np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])][ax]
def _eul(x=0, y=0, z=0): return _rot(2, z) @ _rot(1, y) @ _rot(0, x)
def _eul_inv(R):
    b = math.asin(max(-1.0, min(1.0, -R[2, 0]))); return (math.atan2(R[2, 1], R[2, 2]), b, math.atan2(R[1, 0], R[0, 0]))
def _arc(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); v = np.cross(a, b); c = float(a @ b)
    if c < -0.9999:
        ax = np.cross(a, [0, 0, 1.0]); ax /= np.linalg.norm(ax); return 2 * np.outer(ax, ax) - np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); return np.eye(3) + K + K @ K / (1 + c)
def _fk(P):
    hp = _B['hp']; par = _B['parents']; R = {}; Pp = {}
    for b in _B['order']:
        Rl = _eul(*P.get(b, (0, 0, 0))); pr = par[b]
        if pr: R[b] = R[pr] @ Rl; Pp[b] = Pp[pr] + R[pr] @ (hp[b] - hp[pr])
        else: R[b] = Rl; Pp[b] = hp[b].copy()
    return R, Pp
def _ik_arms(P, p):
    hp = _B['hp']; par = _B['parents']
    R, Pp = _fk(P)
    aim = np.array([0.0, p['aimy'], 1.0]); aim /= np.linalg.norm(aim); up = np.array([0.0, 1.0, -p['aimy']]); up /= np.linalg.norm(up)
    hr = p['hr']
    for side in ('L', 'R'):
        ua, la, wr = 'upperarm01.' + side, 'lowerarm01.' + side, 'wrist.' + side
        T = np.array([p['t' + side.lower() + str(i)] for i in range(3)])
        hint = np.array([0.3, -1.0, -0.2]) if side == 'L' else (np.array([-0.3, -1.0, -0.2]) * (1 - hr) + np.array([-0.5, 0.15, -1.0]) * hr)
        S = Pp[ua]; L1 = np.linalg.norm(hp[la] - hp[ua]); L2 = np.linalg.norm(hp[wr] - hp[la])
        v = T - S; d = min(np.linalg.norm(v), L1 + L2 - 1e-3); u = v / np.linalg.norm(v)
        a = (L1 * L1 - L2 * L2 + d * d) / (2 * d); h = math.sqrt(max(L1 * L1 - a * a, 1e-6))
        pe = hint - (hint @ u) * u; pe /= np.linalg.norm(pe)
        E = S + a * u + h * pe; Tw = S + d * u
        ru = (hp[la] - hp[ua]) / L1; rf = (hp[wr] - hp[la]) / L2
        Rwu = _arc(ru, E - S); Rl = _arc(Rwu @ rf, Tw - E) @ Rwu
        P[ua] = _eul_inv(R[par[ua]].T @ Rwu); P[la] = _eul_inv(Rwu.T @ Rl)
        R[ua] = Rwu; R[la] = Rl
        fr = FRAMES.get(wr)
        if fr is not None:
            bu, bf = fr; bu = np.array(bu); bf = np.array(bf)
            A = np.array([up, aim, np.cross(up, aim)]).T; Bm = np.array([bu, bf, np.cross(bu, bf)]).T
            Rw = A @ Bm.T
            P[wr] = _eul_inv(Rl.T @ Rw)
    return P

def to_pose(p, kind='melee'):
    P, off = _to_pose(p, kind)
    if p.get('ikw', 0) > 0.5 and _B is not None:
        P = _ik_arms(P, p)
    return P, off

# archery: ready (arrow nocked, bow forward, string hand just behind the grip) and full draw (side-on, anchor at the face)
READY = dict(ikw=1, aimy=0.22, hr=0.0, ry=-0.3, yaw=-0.1, lean=0.03, hyaw=0.3, tl0=0.17, tl1=1.08, tl2=0.36, tr0=0.12, tr1=1.08, tr2=0.23,
             rlf=-0.12, llf=0.14, rlk=0.22, llk=0.26, rlo=0.14, llo=0.1, dy=-0.04)
DRAW_BODY = dict(ry=-0.95, yaw=-0.1, hyaw=1.0, lean=0.0, rlf=-0.1, llf=0.12, rlk=0.1, llk=0.1, rlo=0.2, llo=0.2, dy=-0.03)
def draw_pose():
    p = dict(DEF, **DRAW_BODY, ikw=0)
    P0, _ = _to_pose(p, 'archer'); R, Pp = _fk(P0)
    aim = np.array([0.0, 0.03, 1.0]); aim /= np.linalg.norm(aim)
    tl = Pp['upperarm01.L'] + 0.585 * aim
    anchor = Pp['head'] + R['head'] @ np.array([-0.045, 0.065, 0.10])
    tr = anchor - 0.07 * aim
    return dict(DRAW_BODY, ikw=1, aimy=0.03, hr=1.0, tl0=tl[0], tl1=tl[1], tl2=tl[2], tr0=tr[0], tr1=tr[1], tr2=tr[2])

_GC = {}
def _arm_solve(p, side, T, x0):
    """FK arm params (fwd, out, elbow, twist) putting the wrist at world target T (model space)"""
    from scipy.optimize import minimize
    pre = 'r' if side == 'R' else 'l'
    def cost(x):
        q = dict(p); q[pre + 'af'], q[pre + 'ao'], q[pre + 'ae'], q[pre + 'at'] = x
        P, _ = _to_pose(q, 'melee'); R, Pp = _fk(P)
        e = Pp['wrist.' + side] - np.array(T)
        return float(e @ e) * 400 + 0.02 * (x[3] - x0[3]) ** 2 + 0.01 * (x[1] - x0[1]) ** 2
    _P, _ = _to_pose(dict(p), 'melee'); _R, _Pp = _fk(_P); print('probe', side, 'sh', _Pp['upperarm01.'+side].round(2), 'wr0', _Pp['wrist.'+side].round(2), 'T', T)
    best = None
    for st in ([0.5, 0.6, 1.2, 0.0], [0.9, 0.9, 1.0, 0.0], [0.3, 1.0, 1.5, 0.0], [0.7, 0.4, 0.8, 0.0]):
        r = minimize(cost, st, method='L-BFGS-B', bounds=[(0, 1.4), (0, 1.4), (0.35, 2.2), (-1.0, 1.0)])
        if best is None or r.fun < best.fun: best = r
    r = best; print('solve', side, r.fun, [round(float(v), 2) for v in r.x])
    return [float(v) for v in r.x]

def guard(kind):
    if kind == 'archer': return dict(READY)
    if kind == 'civ': return dict(raf=0.08, rae=0.25, laf=0.08, lae=0.25)
    if kind == 'ride': return dict(raf=0.7, rae=0.9, laf=0.7, lae=0.9)
    # historical ready stance: knees bent, weight low, lead (shield-side) foot forward, trailing foot turned out, body half-turned
    g = dict(raf=0.55, rae=1.2, rao=0.6, rat=-0.3, laf=0.5, lae=1.25, lao=0.55, lat=0.3,
             rlf=-0.2, llf=0.28, rlk=0.3, llk=0.34, rlo=0.12, llo=0.06, dy=-0.07, yaw=0.1, lean=0.04)
    if _B is not None and kind in ('melee', 'sword', 'hero'):
        key = id(_B)
        if key not in _GC:
            p = dict(DEF, **g)
            sc = float(_B['hp']['upperarm01.L'][1]) / 1.34
            r = _arm_solve(p, 'R', tuple(np.array((-0.23, 1.12, 0.33)) * sc), [g['raf'], g['rao'], g['rae'], g['rat']])
            l = _arm_solve(p, 'L', tuple(np.array((0.30, 1.08, 0.27)) * sc), [g['laf'], g['lao'], g['lae'], g['lat']])
            _GC[key] = (r, l); print('guard arms R', r, 'L', l)
        r, l = _GC[key]
        g.update(raf=r[0], rao=r[1], rae=r[2], rat=r[3], laf=l[0], lao=l[1], lae=l[2], lat=l[3])
    return g

def idle(kind):
    def f(t):
        a = 2 * PI * t
        p = dict(DEF, **guard(kind))
        p['lean'] = 0.02 + 0.012 * math.sin(a); p['shl'] = p['shr'] = 0.03 * math.sin(a)
        p['roll'] = 0.025 * math.sin(a * 0.5); p['rroll'] = -0.02 * math.sin(a * 0.5); p['dx'] = 0.012 * math.sin(a * 0.5)
        p['hyaw'] = 0.12 * math.sin(a * 0.5 + 1.0); p['hpitch'] = 0.03 * math.sin(a)
        if kind == 'melee':
            p['dy'] += 0.012 * math.sin(a * 2) - 0.012; p['rlk'] += 0.03 * math.sin(a * 2); p['llk'] += 0.03 * math.sin(a * 2 + 0.6)  # fighting bounce
            p['dx'] = 0.02 * math.sin(a); p['rlf'] += 0.02 * math.sin(a); p['llf'] -= 0.02 * math.sin(a)
        else:
            p['rlf'] = 0.05; p['llf'] = -0.04; p['rlk'] = 0.08; p['llk'] = 0.06; p['dy'] = -0.015 + 0.004 * math.sin(a)
        p['raf'] += 0.02 * math.sin(a + 0.8); p['laf'] += 0.015 * math.sin(a + 1.6)
        return to_pose(p, kind)
    return f

def gait(kind, amp, knee, bob, lean, arm, speed_hips):
    def f(t):
        a = 2 * PI * t
        p = dict(DEF, **guard(kind))
        s, c = math.sin(a), math.cos(a)
        for side, ph in (('r', 0.0), ('l', PI)):
            sa = math.sin(a + ph); ca = math.cos(a + ph)
            p[side + 'lf'] = sa * amp
            p[side + 'lk'] = (max(0.0, -ca) ** 1.2) * knee + 0.06
            p[side + 'lp'] = -sa * 0.2 - max(0.0, -ca) * 0.35 * knee * 0.3
        p['dy'] = -0.03 - abs(math.sin(a)) * -bob + 0.0 if False else (-0.02 + bob * (0.5 - 0.5 * math.cos(2 * a)) - bob * 0.35)
        p['ry'] = s * speed_hips; p['yaw'] = -s * speed_hips * 1.6; p['roll'] = c * 0.025; p['rroll'] = -c * 0.03
        p['lean'] = lean + 0.01 * math.cos(2 * a)
        p['hyaw'] = s * speed_hips * 0.9; p['hpitch'] = -lean * 0.6
        if kind in ('melee',):
            g0 = guard('melee'); p['raf'] = g0['raf'] - arm * 0.12 * s; p['laf'] = g0['laf'] + arm * 0.06 * s
        elif kind == 'archer':
            p['raf'] = 0.4 + arm * 0.5 * -s * 0.6; p['laf'] = 0.6 + arm * 0.4 * s * 0.5
        else:
            p['raf'] = arm * 0.9 * -s; p['laf'] = arm * 0.9 * s; p['rae'] = 0.3 + 0.5 * max(0, s) * arm; p['lae'] = 0.3 + 0.5 * max(0, -s) * arm
        p['shl'] = s * 0.05; p['shr'] = -s * 0.05
        return to_pose(p, kind)
    return f

WRIST_TILT = 0.7
def stroll(kind='melee'):
    """relaxed, confident walk: long loose stride, hip sway, shoulders rolling, arms swinging, head scanning"""
    def f(t):
        a = 2 * PI * t
        p = dict(DEF, **guard('civ'))
        s, c = math.sin(a), math.cos(a)
        for side, ph in (('r', 0.0), ('l', PI)):
            sa = math.sin(a + ph); ca = math.cos(a + ph)
            p[side + 'lf'] = sa * 0.5
            p[side + 'lk'] = (max(0.0, -ca) ** 1.2) * 0.85 + 0.05
            p[side + 'lp'] = -sa * 0.18 - max(0.0, -ca) * 0.1
        p['dy'] = -0.02 + 0.03 * (0.5 - 0.5 * math.cos(2 * a)) - 0.012
        p['dx'] = 0.03 * s
        p['ry'] = s * 0.12; p['yaw'] = -s * 0.2; p['roll'] = c * 0.04; p['rroll'] = -c * 0.05
        p['lean'] = 0.03 + 0.008 * math.cos(2 * a)
        p['hyaw'] = 0.22 * math.sin(a * 0.5) - s * 0.08; p['hpitch'] = -0.02 + 0.03 * math.sin(a * 0.5 + 1)
        p['raf'] = 0.12 - s * 0.16; p['laf'] = s * 0.45
        p['rae'] = 0.18 + 0.1 * max(0, s); p['lae'] = 0.25 + 0.4 * max(0, -s)
        p['rao'] = 0.1; p['lao'] = 0.12; p['wr'] = WRIST_TILT
        p['shl'] = s * 0.07; p['shr'] = -s * 0.07
        return to_pose(p, kind)
    return f

def turn(kind, d):
    # in-place pivot: head leads, torso twists into the turn, feet shuffle; loops
    def f(t):
        a = 2 * PI * t
        p = dict(DEF, **guard(kind))
        p['hyaw'] = 0.55 * d; p['yaw'] = 0.32 * d + 0.06 * d * math.sin(a); p['ry'] = -0.18 * d * math.sin(a)
        p['rroll'] = -0.06 * d; p['roll'] = 0.05 * d; p['lean'] = 0.05
        for side, ph in (('r', 0.0), ('l', PI)):
            sa = math.sin(a + ph); ca = math.cos(a + ph)
            p[side + 'lf'] = sa * 0.22 * 1; p[side + 'lk'] = max(0.0, -ca) * 0.5 + 0.1
            p[side + 'lo'] = (0.18 if (side == 'l') == (d > 0) else -0.1) * max(0.0, -ca)
        p['dy'] = -0.035 + 0.012 * abs(math.sin(a))
        return to_pose(p, kind)
    return f

def react(kind):
    def f(t):
        base = guard(kind)
        keys = [(0.0, dict(base, lean=0.0)),
                (0.14, dict(base, lean=-0.32, hpitch=-0.35, rao=0.9, lao=0.7, raf=-0.1, laf=0.0, rae=0.5, lae=0.5, rlk=0.35, llk=0.5, dy=-0.07, dz=-0.07, shr=0.25, shl=0.25, ry=0.12)),
                (0.32, dict(base, lean=0.12, hpitch=0.12, rlk=0.4, llk=0.35, dy=-0.1, dz=-0.04, ry=-0.06)),
                (0.6, dict(base, lean=0.0, rlk=0.1, llk=0.1))]
        return to_pose(kf(t, keys), kind)
    return f

def block(kind):
    def f(t):
        base = guard(kind)
        up = dict(base, laf=1.05, lae=1.6, lao=0.0, lat=0.3, lean=0.1, rlk=0.2, llk=0.3, dy=-0.06, hpitch=0.1, shl=0.1)
        keys = [(0.0, base), (0.18, up), (0.3, dict(up, lean=0.05, dz=-0.03)), (0.42, dict(up, lean=0.1)), (0.8, up)]
        return to_pose(kf(t, keys), kind)
    return f

def attack_slash(kind):
    def f(t):
        base = guard(kind)
        keys = [(0.0, base),
                (0.30, dict(base, raf=-0.2, rao=1.5, rae=0.7, rat=0.6, yaw=0.55, ry=0.15, lean=-0.1, rlk=0.3, llk=0.1, rlf=0.3, llf=-0.25, dy=-0.04, dz=-0.04, hyaw=-0.25, wr=0.2)),
                (0.45, dict(base, raf=1.45, rao=0.1, rae=0.25, rat=-0.7, yaw=-0.7, ry=-0.2, lean=0.3, rlk=0.6, llk=0.1, rlf=-0.3, llf=0.7, dy=-0.12, dz=0.12, hyaw=0.2, hpitch=0.1, wr=-0.3)),
                (0.6, dict(base, raf=1.2, rao=-0.15, rae=0.4, rat=-0.9, yaw=-0.55, lean=0.28, rlk=0.55, llk=0.15, rlf=-0.25, llf=0.62, dy=-0.1, dz=0.11)),
                (1.0, base)]
        return to_pose(kf(t, keys), kind)
    return f

def attack_overhead(kind):
    def f(t):
        base = guard(kind)
        keys = [(0.0, base),
                (0.34, dict(base, raf=2.5, rao=0.0, rae=1.1, rat=-0.2, lean=-0.18, rlk=0.15, llk=0.4, rlf=0.2, llf=-0.4, dy=0.0, dz=-0.06, hpitch=-0.15, shr=0.2)),
                (0.48, dict(base, raf=0.9, rao=0.0, rae=0.15, lean=0.42, rlk=0.55, llk=0.15, rlf=-0.35, llf=0.75, dy=-0.15, dz=0.13, hpitch=0.15)),
                (0.62, dict(base, raf=0.75, rao=-0.1, rae=0.2, lean=0.38, rlk=0.5, llk=0.2, rlf=-0.3, llf=0.7, dy=-0.14, dz=0.12)),
                (1.0, base)]
        return to_pose(kf(t, keys), kind)
    return f

def attack_thrust(kind):
    def f(t):
        base = guard(kind)
        keys = [(0.0, base),
                (0.32, dict(base, raf=0.2, rao=0.4, rae=1.9, rat=-1.2, yaw=0.45, lean=-0.05, rlk=0.55, llk=0.1, rlf=0.35, llf=-0.3, dy=-0.1, dz=-0.08)),
                (0.46, dict(base, raf=1.55, rao=0.0, rae=0.1, rat=-1.4, yaw=-0.5, lean=0.25, rlk=0.35, llk=0.05, rlf=-0.55, llf=0.95, dy=-0.2, dz=0.25, hpitch=0.05, shl=0.1)),
                (0.64, dict(base, raf=1.5, rao=0.0, rae=0.15, rat=-1.4, yaw=-0.45, lean=0.22, rlk=0.35, llk=0.05, rlf=-0.5, llf=0.9, dy=-0.19, dz=0.24)),
                (1.0, base)]
        return to_pose(kf(t, keys), kind)
    return f

def attack_rising(kind):
    # Unterhau: low-to-high rising cut from the trailing side, long step in, hips drive it up
    def f(t):
        base = guard(kind)
        keys = [(0.0, base),
                (0.28, dict(base, raf=-0.35, rao=-0.2, rae=0.3, rat=0.5, yaw=0.5, ry=0.2, lean=0.12, rlk=0.55, llk=0.3, rlf=-0.35, llf=0.1, dy=-0.14, dz=-0.05, hpitch=0.1, wr=0.2)),
                (0.44, dict(base, raf=1.9, rao=0.3, rae=0.2, rat=-0.6, yaw=-0.6, ry=-0.2, lean=0.15, rlk=0.4, llk=0.1, rlf=-0.5, llf=0.85, dy=-0.12, dz=0.16, hpitch=-0.05, wr=-0.3)),
                (0.58, dict(base, raf=2.2, rao=0.4, rae=0.3, yaw=-0.5, lean=0.1, rlk=0.4, llk=0.1, rlf=-0.45, llf=0.8, dy=-0.1, dz=0.14)),
                (1.0, base)]
        return to_pose(kf(t, keys), kind)
    return f

def attack_bash(kind):
    # shield bash: gather behind the shield, shoulder + step drive, sword hand cocked back for the follow-up
    def f(t):
        base = guard(kind)
        keys = [(0.0, base),
                (0.22, dict(base, laf=0.9, lae=1.9, lao=0.2, lean=0.0, yaw=0.3, rlk=0.45, llk=0.5, rlf=-0.3, llf=0.15, dy=-0.12, dz=-0.08, shl=0.1)),
                (0.38, dict(base, laf=1.25, lae=0.7, lao=0.1, lat=0.3, lean=0.3, yaw=-0.3, rlf=-0.5, llf=0.8, rlk=0.3, llk=0.2, dy=-0.1, dz=0.22, shl=0.35, raf=0.4, rae=1.4)),
                (0.55, dict(base, laf=1.2, lae=0.8, lean=0.25, rlf=-0.45, llf=0.7, dy=-0.1, dz=0.2, shl=0.3)),
                (1.0, base)]
        return to_pose(kf(t, keys), kind)
    return f

def mount_clip(kind, rev=False):
    # Standing at the horse's near side facing its flank: hands on pommel/mane, foot to the stirrup, pull up, swing the far leg over, settle in the saddle.
    def f(t):
        base = guard(kind)
        stand = dict(base, ry=-1.35, yaw=-0.1, hyaw=0.5, raf=0.7, rae=0.5, rao=0.6, laf=0.65, lae=0.7, lao=0.5, rlf=0.0, llf=0.1, rlk=0.1, llk=0.1, rlo=0.1, llo=0.1, dy=0.0, lean=0.05)
        foot = dict(stand, llf=1.15, llk=1.35, llo=0.25, lean=0.12, raf=0.95, laf=0.9, rae=0.35, lae=0.45, rlk=0.15, dy=-0.02)
        pull = dict(stand, llf=1.0, llk=1.0, llo=0.3, lean=0.38, ry=-1.1, raf=1.1, laf=1.0, rae=0.3, lae=0.35, rlf=-0.9, rlk=0.7, rlo=0.5, dy=0.04, roll=-0.15)
        over = dict(stand, llf=0.9, llk=0.9, llo=0.2, lean=0.3, ry=-0.55, raf=1.0, laf=0.9, rae=0.5, lae=0.5, rlf=-0.2, rlk=0.35, rlo=1.2, dy=0.05, roll=-0.08, hyaw=0.2)
        seat = dict(base, ry=0.0, yaw=0.0, hyaw=0.0, raf=0.75, rae=0.9, rao=0.2, laf=0.75, lae=0.9, lao=0.2, rlf=1.3, llf=1.3, rlk=1.35, llk=1.35, rlo=0.35, llo=0.35, dy=-0.0, lean=0.1, hpitch=-0.06)
        keys = [(0.0, stand), (0.14, foot), (0.4, pull), (0.62, over), (0.85, dict(seat, ry=-0.1, lean=0.18)), (1.0, seat)]
        if rev: keys = [(1.0 - k[0], k[1]) for k in keys]
        return to_pose(kf(t, keys), kind)
    return f

def attack_bow():
    def f(t):
        rd = dict(READY); dr = draw_pose()
        raise_ = dict(rd, ry=-0.6, yaw=-0.1, hyaw=0.6, hr=0.5, aimy=0.1, tl0=0.2, tl1=1.2, tl2=0.5, tr0=0.1, tr1=1.15, tr2=0.3)
        hold = dict(dr, tr2=dr['tr2'] + 0.004, tl1=dr['tl1'] + 0.004)
        rel = dict(dr, tr0=dr['tr0'] - 0.05, tr1=dr['tr1'] - 0.03, tr2=dr['tr2'] - 0.12, hr=1.0, shl=0.05)
        fol = dict(rel, tr2=dr['tr2'] - 0.1, tr1=dr['tr1'] - 0.1, tl1=dr['tl1'] - 0.02)
        keys = [(0.0, rd), (0.22, raise_), (0.55, dr), (0.68, hold), (0.72, rel), (0.82, fol), (1.0, rd)]
        return to_pose(kf(t, keys), 'archer')
    return f

def attack_civ():
    def f(t):
        base = guard('civ')
        keys = [(0.0, base), (0.3, dict(base, raf=2.0, rao=0.3, rae=0.6, lean=-0.12)), (0.45, dict(base, raf=0.7, rao=0.0, rae=0.2, lean=0.3, rlk=0.3, dz=0.08)), (1.0, base)]
        return to_pose(kf(t, keys), 'civ')
    return f

def die(kind, mode):
    def f(t):
        base = guard(kind)
        if kind == 'archer': base = dict(base, ikw=0, raf=0.4, rae=0.9, rao=0.2, laf=0.5, lae=0.8, lao=0.1)
        if mode == 0:   # collapse and fall on the back
            keys = [(0.0, base),
                    (0.16, dict(base, lean=-0.18, hpitch=-0.3, rao=0.8, lao=0.6, rlk=0.5, llk=0.4, dy=-0.08)),
                    (0.4, dict(base, lean=0.0, rpitch=-0.3, rlk=1.2, llk=0.9, dy=-0.45, dz=-0.1, rao=1.0, lao=1.0, raf=-0.2, laf=-0.2, rae=0.4, lae=0.4, hpitch=-0.3)),
                    (0.8, dict(base, rpitch=-1.45, rlk=0.4, llk=0.25, dy=-0.76, dz=-0.35, rao=1.4, lao=1.4, raf=0.0, laf=0.0, rae=0.2, lae=0.2, hpitch=-0.1, rlf=0.2, llf=0.0, rlo=0.25, llo=0.3)),
                    (1.0, dict(base, rpitch=-1.52, rlk=0.2, llk=0.15, dy=-0.78, dz=-0.38, rao=1.5, lao=1.5, raf=0.1, laf=0.1, rae=0.1, lae=0.1, rlo=0.3, llo=0.3))]
        else:           # drop to the knees, then forward
            keys = [(0.0, base),
                    (0.2, dict(base, lean=0.15, rlk=0.6, llk=0.4, dy=-0.1, rae=0.5, lae=0.5)),
                    (0.5, dict(base, lean=0.45, rlk=1.9, llk=1.7, rlf=0.5, llf=0.2, dy=-0.4, raf=0.4, laf=0.4, hpitch=0.35, rao=0.5, lao=0.5)),
                    (0.85, dict(base, rpitch=1.4, lean=0.2, rlk=1.9, llk=1.9, rlf=-0.1, llf=-0.1, dy=-0.7, dz=0.4, raf=1.0, laf=1.0, rao=0.8, lao=0.8, hpitch=-0.3)),
                    (1.0, dict(base, rpitch=1.5, lean=0.2, rlk=1.5, llk=1.5, dy=-0.74, dz=0.45, raf=1.1, laf=1.1, rao=0.9, lao=0.9, hpitch=-0.35))]
        return to_pose(kf(t, keys), kind)
    return f

def ride(kind):
    def f(t):
        a = 2 * PI * t
        p = dict(DEF, **guard('ride'))
        p['rlf'] = 1.3; p['llf'] = 1.3; p['rlk'] = 1.35; p['llk'] = 1.35; p['rlo'] = 0.35; p['llo'] = 0.35
        p['dy'] = -0.28 + 0.015 * abs(math.sin(a)); p['lean'] = 0.1 + 0.05 * math.sin(a); p['hpitch'] = -0.06
        p['raf'] = 0.75 + 0.05 * math.sin(a); p['laf'] = 0.75 - 0.05 * math.sin(a)
        return to_pose(p, 'ride')
    return f

def clips(kind):
    """kind: sword | cav | hero (melee), archer, villager (civ)"""
    k = 'archer' if kind == 'archer' else ('civ' if kind == 'villager' else 'melee')
    C = []
    C.append(('idle', 3.0, idle(k), True))
    if k == 'civ': C.append(('walk', 1.1, gait('civ', 0.55, 0.9, 0.025, 0.04, 0.6, 0.09), True)); C.append(('run', 0.65, gait('civ', 0.95, 1.6, 0.05, 0.22, 0.9, 0.14), True))
    elif k == 'archer': C.append(('walk', 1.0, gait('archer', 0.6, 0.95, 0.025, 0.05, 0.5, 0.1), True)); C.append(('run', 0.6, gait('archer', 1.0, 1.7, 0.055, 0.25, 0.8, 0.15), True))
    else: C.append(('walk', 1.0, gait('melee', 0.6, 0.95, 0.025, 0.05, 0.5, 0.1), True)); C.append(('run', 0.6, gait('melee', 1.0, 1.75, 0.055, 0.26, 0.8, 0.15), True))
    C.append(('turn_left', 0.9, turn(k, 1.0), True)); C.append(('turn_right', 0.9, turn(k, -1.0), True))
    C.append(('react', 0.6, react(k), False))
    if k == 'melee': C.append(('block', 0.8, block(k), False)); C.append(('stroll', 1.3, stroll(k), True))
    if k == 'melee':
        C.append(('attack', 0.9, attack_slash(k), False)); C.append(('attack2', 1.0, attack_overhead(k), False)); C.append(('attack3', 0.95, attack_thrust(k), False)); C.append(('attack4', 0.9, attack_rising(k), False)); C.append(('mount', 1.5, mount_clip(k), False)); C.append(('dismount', 1.1, mount_clip(k, True), False)); C.append(('attack5', 0.85, attack_bash(k), False))
    elif k == 'archer': C.append(('attack', 1.3, attack_bow(), False))
    else: C.append(('attack', 0.8, attack_civ(), False))
    C.append(('die', 1.2, die(k, 0), False)); C.append(('die2', 1.3, die(k, 1), False))
    C.append(('ride', 1.0, ride(k), True))
    return C
