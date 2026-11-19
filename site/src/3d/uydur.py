"""Her tuşun 3D üst yüzünü fotoğraftaki dörtgenine uydurur (düzlemde kaydırma, dönme, ölçek).
Çıktı: uydurma.json {tuş: [dx_mm, dy_mm, dtheta_rad, s]}; bilinmeyen tuşlar komşu ortalamasını alır."""
import re, json, numpy as np
exec(open(__file__.rsplit('/', 1)[0] + '/kamera3d.py').read().split('# başlangıç')[0])   # L, ZR, U, project, rodrigues, least_squares
KJ = json.load(open(__file__.rsplit('/', 1)[0] + '/kamera3d.json'))
p = np.r_[KJ['f'], to_rotvec(np.array(KJ['R'])), KJ['t']]
WID = {"Tab": 1.5, "Caps": 1.75}
def top_corners(k, prm):
    x, y, row = L[k]; w = WID.get(k, 1.0)
    tw = w * U - 1.05 - 5.2; td = U - 1.05 - 5.8; off = 1.2; h = ZR[row] + 1.5
    dx, dy, th, s = prm
    c = np.array([[-tw/2, -td/2 + off], [tw/2, -td/2 + off], [tw/2, td/2 + off], [-tw/2, td/2 + off]]) * s
    R2 = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    c = c @ R2.T + [x * U + dx, y * U + dy]
    return np.column_stack([c, np.full(4, h)])
out = {}
for k in L:
    if k not in K: continue
    tgt = K[k]
    # köşe eşlemesi: en iyi dairesel kaydırma / yön
    P0 = project(p, top_corners(k, (0, 0, 0, 1)))
    best = None
    for rev in (False, True):
        T = tgt[::-1] if rev else tgt
        for sh in range(4):
            Tt = np.roll(T, sh, axis=0); e = np.linalg.norm(P0 - Tt, axis=1).sum()
            if best is None or e < best[0]: best = (e, Tt)
    Tt = best[1]
    f = lambda q: (project(p, top_corners(k, q)) - Tt).ravel()
    r = least_squares(lambda q: f(q), np.array([0., 0., 0., 1.]), f_scale=3)
    e = np.linalg.norm(project(p, top_corners(k, r.x)) - Tt, axis=1)
    out[k] = [float(v) for v in r.x]
    print(f"{k:5s} önce {np.linalg.norm(P0 - Tt, axis=1).mean():5.1f}px  sonra {e.mean():4.1f}px  kayma {r.x[0]:5.1f},{r.x[1]:5.1f}mm  dönme {np.degrees(r.x[2]):5.1f}°  ölçek {r.x[3]:.2f}")
json.dump(out, open(__file__.rsplit('/', 1)[0] + '/uydurma.json', 'w'), indent=0)
