"""Kamerayı 29 tuşun dört üst köşesinden (116 nokta) çözer; kamera3d.json'u günceller."""
import json, numpy as np
exec(open(__file__.rsplit('/', 1)[0] + '/kamera3d.py').read().split('# başlangıç')[0])
KJ = json.load(open(__file__.rsplit('/', 1)[0] + '/kamera3d.json'))
WID = {"Tab": 1.5, "Caps": 1.75}
def corners(k):
    x, y, row = L[k]; w = WID.get(k, 1.0)
    tw = w * U - 1.05 - 5.2; td = U - 1.05 - 5.8; off = 1.2; h = ZR[row] + 1.5
    c = np.array([[-tw/2, -td/2 + off], [tw/2, -td/2 + off], [tw/2, td/2 + off], [-tw/2, td/2 + off]]) + [x * U, y * U]
    return np.column_stack([c, np.full(4, h)])
p = np.r_[KJ['f'], to_rotvec(np.array(KJ['R'])), KJ['t']]
keys = [k for k in L if k in K]
def match(p):
    X3, X2 = [], []
    for k in keys:
        C = corners(k); P0 = project(p, C); T = K[k]; best = None
        for rev in (False, True):
            TT = T[::-1] if rev else T
            for sh in range(4):
                Tt = np.roll(TT, sh, axis=0); e = np.linalg.norm(P0 - Tt, axis=1).sum()
                if best is None or e < best[0]: best = (e, Tt)
        X3.append(C); X2.append(best[1])
    return np.vstack(X3), np.vstack(X2)
for it in range(3):
    X3, X2 = match(p)
    r = least_squares(res, p, args=(X3, X2), f_scale=6); p = r.x
    e = np.linalg.norm(project(p, X3) - X2, axis=1)
    print(f"tur {it}: köşe hatası medyan {np.median(e):.1f}px ort {e.mean():.1f}px")
Rm = rodrigues(p[1:4]); t = p[4:7]
KJ.update(f=float(p[0]), R=Rm.tolist(), t=t.tolist(), cam=(-Rm.T @ t).tolist())
json.dump(KJ, open(__file__.rsplit('/', 1)[0] + '/kamera3d.json', 'w'))
print('odak', round(p[0] / 1920 * 36, 1), 'mm, kamera', np.round(-Rm.T @ t, 1))
