import sys, math, os, numpy as np
sys.path.insert(0, '/tmp/mh2')
import base as B, gear as G, anim, mhlib as L
from mhlib import *
from PIL import Image, ImageEnhance
import colorsys

SKIN = {'cau': (0.86, 0.64, 0.52), 'asi': (0.84, 0.66, 0.46), 'afr': (0.40, 0.25, 0.17), 'ara': (0.70, 0.50, 0.36), 'dark': (0.55, 0.36, 0.25)}
EYE = {'brown': 'eye_brown', 'blue': 'eye_blue', 'green': 'eye_green', 'hazel': 'eye_hazel'}

def hsh(p, k=0):
    x = math.sin(p[0] * 127.1 + p[1] * 311.7 + p[2] * 74.7 + k * 19.19) * 43758.5453
    return x - math.floor(x)

def rtop(r):
    return max(r.items(), key=lambda kv: kv[1])[0] if r else ''

def paint(base, ch):
    Vv = base['V']; dom = base['dom']; hp = base['hp']; raw = base['raw']; n = len(Vv)
    col = np.ones((n, 4), np.float32)
    skin = np.array(SKIN[ch['skin']]); pal = ch['pal']; hair = np.array(ch.get('hair_col', (0.15, 0.1, 0.07)))
    ev = base['eyes']['V']; eyeL = ev[ev[:, 0] > 0].mean(0); eyeR = ev[ev[:, 0] < 0].mean(0); ey = (eyeL[1] + eyeR[1]) / 2
    hm = np.array([d in ('head', 'neck01') for d in dom]); zf = Vv[np.array([d == 'head' for d in dom]), 2].max()
    lipsY = []
    for i in range(n):
        rb = rtop(raw[i])
        if rb.startswith('oris') and dom[i] == 'head' and Vv[i, 2] > zf - 0.03: lipsY.append(Vv[i, 1])
    my = float(np.mean(lipsY)) if lipsY else ey - 0.065
    beard = ch.get('beard', 0.0)
    wy = hp['root'][1]; ank = hp['foot.L'][1]
    ageg = ch['spec'].get('age', 0.5)
    for i in range(n):
        d = dom[i]; p = Vv[i]; rb = rtop(raw[i]); r = {rb: 1}
        jit = (hsh(p) - 0.5) * 0.05
        if d in ('head', 'neck01'):
            c = skin.copy() * (1 + jit)
            front = p[2] > zf - 0.045
            if front and abs(p[0]) < 0.09:
                c *= 1.0 + 0.035 * (1 - abs(p[1] - (ey + 0.05)) * 8)                       # forehead highlight
            if any(k.startswith('oris') for k in r) and front:
                c = c * np.array([1.0, 0.8, 0.74])    # lips
            if any(k.startswith(('oculi', 'orbic')) for k in r): c = c * np.array([0.9, 0.78, 0.76])         # eyelids
            if front and ey - 0.075 < p[1] < ey - 0.02 and abs(p[0]) > 0.03: c = c * np.array([1.0, 0.9, 0.88]) # cheek colour
            if front and ey - 0.05 < p[1] < ey - 0.012 and abs(p[0]) < 0.018 and p[2] > zf - 0.012: c = c * np.array([1.02, 0.86, 0.82])  # nose tip
            if front and ey + 0.012 < p[1] < ey + 0.042 and 0.014 < abs(p[0]) < 0.075:                      # eyebrows
                k = min(1.0, 0.55 + hsh(p, 3) * 0.7); c = c * (1 - k) + hair * 0.9 * k
            if d == 'head' and abs(p[0]) > 0.075 and ey - 0.05 < p[1] < ey + 0.01: c = c * np.array([1.0, 0.88, 0.85])   # ears
            if beard > 0 and p[1] < my + 0.025 and p[1] > my - 0.12 and p[2] > zf - 0.1 and abs(p[0]) < 0.09 and p[1] < ey - 0.02 and not any(k.startswith('oris') for k in r):
                k = beard * (0.55 + 0.45 * hsh(p, 5)); c = c * (1 - k) + hair * k
            if ageg > 0.65 and front and (abs(p[1] - (ey + 0.03)) < 0.01 or abs(p[1] - (my + 0.02)) < 0.006): c *= 0.94    # age lines
            col[i, :3] = np.clip(c, 0, 1); continue
        y = p[1]; c = skin.copy() * (1 + jit * 0.6)
        if d in ('spine05', 'spine03', 'spine01', 'clavicle.L', 'clavicle.R'):
            c = np.array(pal['tunic']);
            if abs(y - wy - 0.02) < 0.05: c = np.array(pal['belt'])
            if y > hp['neck01'][1] - 0.05 and abs(p[0]) < 0.055: c = skin.copy()    # neck opening
        elif d.startswith('upperarm'): c = np.array(pal['arms'])
        elif d.startswith('lowerarm'):
            c = np.array(pal['arms'] if ch['kind'] in ('sword', 'cav', 'hero') else pal['tunic'])
            if ch['kind'] == 'villager': c = skin.copy()
        elif d.startswith('wrist'): c = np.array((0.3, 0.2, 0.12)) if ch['kind'] != 'villager' else skin.copy()
        elif d == 'root':
            c = np.array(pal['pants'])
            if abs(y - wy) < 0.05: c = np.array(pal['belt'])
        elif d.startswith('upperleg') or d.startswith('lowerleg'):
            c = np.array(pal['pants'])
            if y < ank + 0.45: c = np.array(pal['boots'])
        elif d.startswith('foot'): c = np.array(pal['boots'])
        col[i, :3] = np.clip(c, 0, 1)
    return col

def add_body(M, base, col):
    Vv = base['V']; Fv = base['F']
    N = np.zeros_like(Vv); fn = np.cross(Vv[Fv[:, 1]] - Vv[Fv[:, 0]], Vv[Fv[:, 2]] - Vv[Fv[:, 0]])
    for k in range(3): np.add.at(N, Fv[:, k], fn)
    ln = np.linalg.norm(N, axis=1, keepdims=True); ln[ln == 0] = 1; N /= ln
    P = M.prims.setdefault((None, 'body'), dict(pos=[], nrm=[], uv=[], col=[], j=[], w=[], idx=[], n=0))
    P['pos'].append(Vv); P['nrm'].append(N); P['uv'].append(np.zeros((len(Vv), 2))); P['col'].append(col)
    P['j'].append(base['J']); P['w'].append(base['W']); P['idx'].append(Fv); P['n'] += len(Vv)

def add_eyes(M, base, ch):
    e = base['eyes']; mat = EYE[ch.get('eye', 'brown')]
    Vv = e['V']; Fv = e['F']
    N = np.zeros_like(Vv); fn = np.cross(Vv[Fv[:, 1]] - Vv[Fv[:, 0]], Vv[Fv[:, 2]] - Vv[Fv[:, 0]])
    for k in range(3): np.add.at(N, Fv[:, k], fn)
    ln = np.linalg.norm(N, axis=1, keepdims=True); ln[ln == 0] = 1; N /= ln
    M.add(mat, Vv, Fv[:, [0, 2, 1]], bone='head', smooth=True, uvs=e['UV'])

def head_ext(y, tol=0.012):
    return G.ext({'head'}, y, tol)

def hair_style(M, base, ch, style, hcol):
    hp = base['hp']; Vv = base['V']; dom = base['dom']
    hm = np.array([d == 'head' for d in dom]); top = Vv[hm, 1].max(); zf = Vv[hm, 2].max(); zb = Vv[hm, 2].min(); cz = (zf + zb) / 2
    ev = base['eyes']['V']; ey = ev[:, 1].mean()
    if style == 'bald': return
    def ring_at(y, grow):
        e = head_ext(min(y, top - 0.004))
        if e is None: return None
        x0, x1, z0, z1 = e
        return ring_xz(((x0 + x1) / 2, y, (z0 + z1) / 2 - 0.004), (x1 - x0) / 2 + grow, (z1 - z0) / 2 + grow)
    def shell(y0, y1, n, g0, g1, cut_front=None, back_only=False, mat='hair', col=hcol):
        rings = []
        for t in np.linspace(0, 1, n):
            y = y0 + (y1 - y0) * t
            r = ring_at(y, g0 + (g1 - g0) * t)
            if r is None: continue
            if y > top - 0.025:
                k = max(0.02, math.sqrt(max(1 - ((y - (top - 0.025)) / 0.045) ** 2, 0)))
                r = (r[0], np.array(r[1]) * k, np.array(r[2]) * k)
            rings.append(r)
        if len(rings) < 3: return
        Vs, Fs = loft(rings, 24, False, True)
        if cut_front is not None or back_only:
            keep = []
            for f in Fs:
                pv = Vs[f]; cy = pv[:, 1].mean(); cx = pv[:, 2].mean()
                if back_only and cx > cz + 0.01 and cy < ey + 0.05: continue
                if cut_front is not None and cx > cz + 0.02 and cy < cut_front: continue
                keep.append(f)
            Fs = np.array(keep)
        M.add(mat, Vs, Fs, color=col, bone='head', smooth=True)
    hair_y = ey + 0.052
    if style in ('short', 'crop'):
        shell(hair_y - 0.17 if style == 'short' else hair_y - 0.1, top + 0.012, 9, 0.014, 0.012, cut_front=hair_y)
    elif style == 'curly':
        shell(hair_y - 0.1, top + 0.03, 9, 0.022, 0.026, cut_front=hair_y + 0.01)
    elif style == 'long':
        shell(hair_y - 0.17, top + 0.012, 9, 0.014, 0.012, cut_front=hair_y)
        # long back and sides down over the shoulders, weighted head -> neck -> upper spine
        yb = hp['spine01'][1] + 0.06
        rings = []
        for t in np.linspace(0, 1, 7):
            y = (hair_y - 0.15) + (yb - (hair_y - 0.15)) * t
            rings.append(ring_xz((0, y, cz - 0.05 - 0.03 * t), 0.115 + 0.015 * t, 0.075 + 0.03 * t))
        Vs, Fs = loft(rings, 20, False, True)
        keep = [f for f in Fs if Vs[f][:, 2].mean() < cz + 0.015]
        def w(p):
            if p[1] > hp['neck01'][1]: return [('head', 1.0)]
            t = min(1.0, (hp['neck01'][1] - p[1]) / 0.2); return [('head', 1 - t), ('spine01', t)]
        M.add('hair', Vs, np.array(keep), color=hcol, wfn=w)
    elif style == 'bun':
        shell(hair_y - 0.12, top + 0.012, 9, 0.014, 0.012, cut_front=hair_y)
        Vs, Fs = lathe([(0.001, -0.045), (0.05, -0.03), (0.06, 0.0), (0.05, 0.03), (0.001, 0.045)], 12, (0, top - 0.03, zb - 0.02), 1)
        M.add('hair', Vs, Fs, color=hcol, bone='head')
    elif style == 'sides':   # bald top, hair at the sides and back (old man)
        shell(hair_y - 0.2, hair_y - 0.03, 5, 0.012, 0.012, cut_front=hair_y - 0.03, back_only=False)

def beard_geo(M, base, ch, hcol, style):
    Vv = base['V']; dom = base['dom']
    hm = np.array([d == 'head' for d in dom]); zf = Vv[hm, 2].max(); zb = Vv[hm, 2].min(); cz = (zf + zb) / 2
    ev = base['eyes']['V']; ey = ev[:, 1].mean()
    my = ey - 0.07
    ys = np.linspace(ey - 0.105, ey - 0.02, 6)
    rings = []
    for y in ys:
        e = head_ext(y)
        if e is None: continue
        x0, x1, z0, z1 = e
        rings.append(ring_xz(((x0 + x1) / 2, y, (z0 + z1) / 2), (x1 - x0) / 2 + 0.012, (z1 - z0) / 2 + 0.014))
    if len(rings) < 3: return
    Vs, Fs = loft(rings, 24, False, False)
    keep = []
    for f in Fs:
        pv = Vs[f]; cy = pv[:, 1].mean(); cx = pv[:, 2].mean(); ax = abs(pv[:, 0]).mean()
        if cx < cz - 0.005: continue
        if cy > my + 0.035 and ax < 0.065: continue       # clear the mouth/cheeks region
        if cy > ey - 0.035 and ax > 0.01: continue
        keep.append(f)
    if style == 'full':
        M.add('hair', Vs, np.array(keep), color=hcol, bone='head')
        # drop below chin
        e = head_ext(ey - 0.105)
        if e: x0, x1, z0, z1 = e
        Vb, Fb = loft([ring_xz(((x0 + x1) / 2, ey - 0.1, (z0 + z1) / 2 + 0.01), 0.05, 0.04), ring_xz(((x0 + x1) / 2, ey - 0.15, (z0 + z1) / 2 + 0.02), 0.04, 0.035), ring_xz(((x0 + x1) / 2, ey - 0.19, (z0 + z1) / 2 + 0.03), 0.004, 0.004)], 14, False, True)
        M.add('hair', Vb, Fb, color=hcol, bone='head')
    # moustache
    Vm, Fm = box((0, my + 0.034, zf - 0.004), (0.07, 0.014, 0.014)); M.add('hair', Vm, Fm, color=hcol, smooth=False, bone='head')

def headscarf(M, base, col):
    Vv = base['V']; dom = base['dom']; hm = np.array([d == 'head' for d in dom]); top = Vv[hm, 1].max()
    ev = base['eyes']['V']; ey = ev[:, 1].mean()
    rings = []
    for t in np.linspace(0, 1, 8):
        y = (ey + 0.045) + (top + 0.025 - (ey + 0.045)) * t
        e = head_ext(min(y, top - 0.004))
        if e is None: continue
        x0, x1, z0, z1 = e; k = 1.0 if t < 0.8 else max(0.05, math.sqrt(max(1 - ((t - 0.8) / 0.2) ** 2, 0)))
        rings.append(ring_xz(((x0 + x1) / 2, y, (z0 + z1) / 2 - 0.006), ((x1 - x0) / 2 + 0.02) * k, ((z1 - z0) / 2 + 0.024) * k))
    Vs, Fs = loft(rings, 20, False, True)
    M.add('cloth', Vs, Fs, color=col, bone='head')
    # draped back
    zb = Vv[hm, 2].min()
    rings = [ring_xz((0, ey + 0.03 - 0.0 - 0.06 * t, zb + 0.06 - 0.015 * t), 0.1 - 0.01 * t, 0.05 + 0.01 * t) for t in np.linspace(0, 1, 5)]
    Vs, Fs = loft(rings, 14, False, True)
    M.add('cloth', Vs, Fs, color=col, bone='head')

def straw_hat(M, base):
    G.villager(M)

def tabard(M, base, col):
    wy = base['hp']['root'][1]; ny = base['hp']['neck01'][1]
    e = G.ext({'spine03', 'spine01', 'spine05'}, (wy + ny) / 2);
    if not e: return
    x0, x1, z0, z1 = e; cx = (x0 + x1) / 2; hw = (x1 - x0) / 2
    for zs, sg in ((z1 + 0.018, 1), (z0 - 0.018, -1)):
        Vv, Ff = box((cx, wy - 0.12, zs), (hw * 1.0, 0.55, 0.012)); M.add('cloth', Vv, Ff, color=col, smooth=False, bone='root')
        Vv, Ff = box((cx, wy + 0.2, zs), (hw * 0.9, 0.35, 0.012)); M.add('cloth', Vv, Ff, color=col, smooth=False, bone='spine05')
        Vv, Ff = box((cx, wy + 0.2, zs + 0.004 * sg), (0.05, 0.3, 0.004)); M.add('gold', Vv, Ff, color=(1, 1, 1), smooth=False, bone='spine05')

def build(ch, outdir):
    head_cell = ch.get('head_cell', 0.0)
    base = B.build(ch['spec'], head_cell=head_cell, body_cell=ch.get('body_cell', 0.024))
    G.use(base)
    G.setpose('archer' if ch['kind'] == 'archer' else ('civ' if ch['kind'] == 'villager' else 'melee'))
    M = Model(base['order'], base['parents'], {b: base['hp'][b] for b in base['order']})
    col = paint(base, ch)
    add_body(M, base, col); add_eyes(M, base, ch)
    kind = ch['kind']; gk = ch.get('gear', kind)
    hcol = ch.get('hair_col', (0.15, 0.1, 0.07))
    if gk in ('sword', 'cav', 'hero'):
        G.breastplate(M, gk); G.pauldrons(M, 'steel' if gk != 'hero' else 'gold'); G.vambraces(M); G.greaves(M); G.helmet(M, gk); [G.sword(M, gk, lv=_l) for _l in range(3)]; G.shield(M, gk); M.part = None
        if gk == 'hero': G.cape(M, (0.55, 0.05, 0.06))
        if ch.get('tabard'): tabard(M, base, ch['tabard'])
    elif gk == 'archer':
        G.helmet(M, 'archer'); G.vambraces(M, 'leather'); G.bow(M); G.quiver(M)
    elif gk == 'villager':
        pass
    if ch.get('hair', 'short') != 'bald' and not (gk in ('sword', 'cav', 'hero') and ch.get('helmet', True)):
        hair_style(M, base, ch, ch.get('hair', 'short'), hcol)
    elif gk in ('sword', 'cav', 'hero') and ch.get('hair') in ('long', 'sides'):
        hair_style(M, base, ch, 'long' if ch['hair'] == 'long' else 'sides', hcol)
    if gk == 'archer' and ch.get('hair') == 'long':
        hair_style(M, base, ch, 'long', hcol)
    if ch.get('beard_geo'): beard_geo(M, base, ch, hcol, ch['beard_geo'])
    if ch.get('headscarf'): headscarf(M, base, ch['headscarf'])
    if gk == 'villager' and ch.get('hat', True) and not ch.get('headscarf'): G.villager(M)
    if gk == 'villager':
        G.pauldrons  # no-op
        if ch.get('apron'): tabard(M, base, ch['apron'])
    clips = [(n, d, (lambda t, fn=f: fn(t)), lp) for n, d, f, lp in anim.clips(ch['kind'])]
    path = f"{outdir}/{ch['name']}.glb"
    n = M.write(path, clips)
    print(ch['name'], len(base['V']), 'verts', n // 1024, 'KB')

def extra_textures(outdir):
    r = np.random.RandomState(7)
    S = L.S
    # hair strands
    n1 = L._fbm(61, 40, 3, (0.3, 8.0)); n2 = L._scratches(62, 120, 90)
    v = 0.45 + 0.5 * n1 + 0.25 * n2
    base = np.dstack([v, v, v])
    mr = 0.45 + 0.3 * n1
    h = n1 * 0.7 + n2 * 0.3
    Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).save(f'{outdir}/hair_c.png')
    Image.fromarray((np.dstack([np.zeros_like(mr), mr, np.zeros_like(mr)]) * 255).astype(np.uint8)).save(f'{outdir}/hair_mr.png')
    Image.fromarray((np.clip(L._normal(h, 1.0), 0, 1) * 255).astype(np.uint8)).save(f'{outdir}/hair_n.png')
    # eyes from the MakeHuman iris texture in several colours
    src = Image.open(B.D + 'eyes/materials/brown_eye.png').convert('RGB')
    src.save(f'{outdir}/eye_brown_c.png')
    a = np.asarray(src).astype(np.float32) / 255.0
    def tint(rgb):
        lum = a.mean(axis=2, keepdims=True)
        sat = (a.max(axis=2) - a.min(axis=2))[..., None]
        out = a * (1 - np.clip(sat * 2.5, 0, 1)) + lum * np.array(rgb)[None, None, :] * 1.7 * np.clip(sat * 2.5, 0, 1)
        return (np.clip(out, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(tint((0.35, 0.55, 0.9))).save(f'{outdir}/eye_blue_c.png')
    Image.fromarray(tint((0.35, 0.7, 0.4))).save(f'{outdir}/eye_green_c.png')
    Image.fromarray(tint((0.6, 0.5, 0.25))).save(f'{outdir}/eye_hazel_c.png')
    for nme in EYE.values():
        sz = src.size
        Image.fromarray(np.dstack([np.zeros(sz[::-1], np.uint8), np.full(sz[::-1], 30, np.uint8), np.zeros(sz[::-1], np.uint8)])).save(f'{outdir}/{nme}_mr.png')
        Image.fromarray(np.dstack([np.full(sz[::-1], 128, np.uint8), np.full(sz[::-1], 128, np.uint8), np.full(sz[::-1], 255, np.uint8)])).save(f'{outdir}/{nme}_n.png')

PAL = {
 'sword':   dict(tunic=(.45, .47, .52), arms=(.62, .64, .68), pants=(.22, .18, .15), boots=(.12, .09, .07), belt=(.25, .15, .08)),
 'sword2':  dict(tunic=(.5, .2, .18), arms=(.5, .2, .18), pants=(.2, .2, .24), boots=(.12, .09, .07), belt=(.3, .2, .1)),
 'sword3':  dict(tunic=(.2, .3, .5), arms=(.55, .57, .62), pants=(.18, .16, .14), boots=(.1, .08, .06), belt=(.3, .2, .1)),
 'archer':  dict(tunic=(.2, .42, .2), arms=(.2, .42, .2), pants=(.35, .27, .16), boots=(.25, .16, .08), belt=(.25, .15, .08)),
 'archer2': dict(tunic=(.4, .32, .2), arms=(.4, .32, .2), pants=(.28, .24, .18), boots=(.22, .15, .08), belt=(.25, .15, .08)),
 'cav':     dict(tunic=(.5, .5, .55), arms=(.6, .62, .66), pants=(.2, .2, .24), boots=(.1, .08, .07), belt=(.3, .2, .1)),
 'hero':    dict(tunic=(.55, .08, .08), arms=(.75, .6, .2), pants=(.12, .1, .12), boots=(.1, .07, .05), belt=(.8, .65, .2)),
 'villager': dict(tunic=(.62, .5, .32), arms=(.62, .5, .32), pants=(.36, .28, .18), boots=(.3, .2, .12), belt=(.4, .25, .12)),
 'villager2': dict(tunic=(.55, .25, .25), arms=(.55, .25, .25), pants=(.4, .3, .22), boots=(.3, .2, .12), belt=(.4, .25, .12)),
 'villager3': dict(tunic=(.5, .45, .38), arms=(.5, .45, .38), pants=(.3, .26, .2), boots=(.25, .18, .1), belt=(.3, .2, .1)),
}
E = lambda **k: dict(k)
CHARS = [
 dict(name='sword', kind='sword', skin='cau', eye='blue', hair='short', hair_col=(0.3, 0.2, 0.1), beard=0.35, pal=PAL['sword'], head_cell=0.011, helmet=True,
      spec=dict(g=1.0, age=0.45, muscle=0.62, eth={'caucasian': 1, 'african': 0, 'asian': 0}, detail={'chin/chin-prominent': 0.4, 'nose/nose-width1': 0.2, 'head/head-square': 0.3, 'forehead/forehead-scale-vert': -0.2})),
 dict(name='sword2', kind='sword', gear='sword', skin='asi', eye='brown', hair='crop', hair_col=(0.05, 0.04, 0.04), beard=0.0, pal=PAL['sword2'], head_cell=0.011, helmet=True,
      spec=dict(g=1.0, age=0.42, muscle=0.55, eth={'caucasian': 0, 'african': 0, 'asian': 1}, detail={'nose/nose-width1': -0.25, 'cheek/cheek-bones': 0.5, 'chin/chin-width': -0.2})),
 dict(name='sword3', kind='sword', gear='sword', skin='afr', eye='brown', hair='curly', hair_col=(0.04, 0.03, 0.03), beard=0.3, beard_geo='short', pal=PAL['sword3'], head_cell=0.011, helmet=True,
      spec=dict(g=1.0, age=0.5, muscle=0.7, eth={'caucasian': 0, 'african': 1, 'asian': 0}, detail={'nose/nose-width1': 0.45, 'mouth/mouth-lowerlip-volume': 0.4, 'chin/chin-width': 0.3})),
 dict(name='archer', kind='archer', skin='cau', eye='green', hair='long', hair_col=(0.38, 0.22, 0.1), beard=0.0, lip=1, pal=PAL['archer'], head_cell=0.011,
      spec=dict(g=0.0, age=0.4, muscle=0.4, eth={'caucasian': 1, 'african': 0, 'asian': 0}, detail={'eyes/eye-scale': 0.3, 'nose/nose-width1': -0.3, 'mouth/mouth-lowerlip-volume': 0.35, 'cheek/cheek-bones': 0.3})),
 dict(name='archer2', kind='archer', skin='ara', eye='hazel', hair='short', hair_col=(0.08, 0.06, 0.05), beard=0.45, beard_geo='full', pal=PAL['archer2'], head_cell=0.011,
      spec=dict(g=1.0, age=0.5, muscle=0.45, eth={'caucasian': 0.5, 'african': 0.2, 'asian': 0.3}, detail={'nose/nose-hump': 0.5, 'forehead/forehead-scale-vert': 0.2, 'eyes/eye-height1': 0.2})),
 dict(name='cav', kind='cav', gear='cav', skin='cau', eye='brown', hair='short', hair_col=(0.12, 0.08, 0.05), beard=0.4, pal=PAL['cav'], head_cell=0.011, helmet=True,
      spec=dict(g=1.0, age=0.55, muscle=0.75, height=0.65, eth={'caucasian': 1, 'african': 0, 'asian': 0}, detail={'chin/chin-prominent': 0.6, 'head/head-rectangular': 0.4, 'nose/nose-hump': 0.3})),
 dict(name='cav2', kind='cav', gear='cav', skin='dark', eye='brown', hair='crop', hair_col=(0.05, 0.04, 0.04), beard=0.25, pal=PAL['sword3'], head_cell=0.011, helmet=True,
      spec=dict(g=1.0, age=0.5, muscle=0.7, height=0.6, eth={'caucasian': 0.25, 'african': 0.75, 'asian': 0}, detail={'head/head-oval': 0.4, 'nose/nose-width1': 0.2})),
 dict(name='hero', kind='hero', skin='cau', eye='blue', hair='short', hair_col=(0.55, 0.5, 0.45), beard=0.6, beard_geo='full', pal=PAL['hero'], head_cell=0.0, helmet=False,
      spec=dict(g=1.0, age=0.68, muscle=0.8, height=0.75, weight=0.55, eth={'caucasian': 1, 'african': 0, 'asian': 0}, detail={'chin/chin-prominent': 0.5, 'forehead/forehead-scale-vert': 0.25, 'head/head-rectangular': 0.5, 'nose/nose-hump': 0.35, 'eyes/eye-height2': -0.2, 'cheek/cheek-bones': 0.4, 'torso/torso-vshape': 0.5})),
 dict(name='villager', kind='villager', gear='villager', skin='cau', eye='brown', hair='short', hair_col=(0.3, 0.2, 0.1), beard=0.25, pal=PAL['villager'], head_cell=0.011, hat=True,
      spec=dict(g=1.0, age=0.5, muscle=0.4, weight=0.55, eth={'caucasian': 1, 'african': 0, 'asian': 0}, detail={'nose/nose-width1': 0.3, 'ears/ear-scale': 0.3})),
 dict(name='villager2', kind='villager', gear='villager', skin='ara', eye='brown', hair='bun', hair_col=(0.08, 0.06, 0.05), beard=0.0, pal=PAL['villager2'], head_cell=0.011, headscarf=(0.75, 0.3, 0.25), apron=(0.85, 0.82, 0.7),
      spec=dict(g=0.0, age=0.45, muscle=0.35, eth={'caucasian': 0.5, 'african': 0.2, 'asian': 0.3}, detail={'eyes/eye-scale': 0.2, 'mouth/mouth-lowerlip-volume': 0.3})),
 dict(name='villager3', kind='villager', gear='villager', skin='cau', eye='blue', hair='sides', hair_col=(0.85, 0.85, 0.85), beard=0.5, beard_geo='full', pal=PAL['villager3'], head_cell=0.011, hat=False,
      spec=dict(g=1.0, age=0.9, muscle=0.25, weight=0.4, eth={'caucasian': 1, 'african': 0, 'asian': 0}, detail={'nose/nose-width1': 0.4, 'ears/ear-scale': 0.5, 'head/head-age': 0.8})),
]

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out + '/tex', exist_ok=True)
    L.make_textures(out + '/tex'); extra_textures(out + '/tex')
    only = sys.argv[2:]
    for ch in CHARS:
        if only and ch['name'] not in only: continue
        build(ch, out)
