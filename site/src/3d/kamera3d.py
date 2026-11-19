import re, json, numpy as np
def rodrigues(rv):
    th = np.linalg.norm(rv)
    if th < 1e-12: return np.eye(3)
    k = rv / th; Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * Kx @ Kx
def to_rotvec(Rm):
    th = np.arccos(np.clip((np.trace(Rm) - 1) / 2, -1, 1))
    if th < 1e-9: return np.zeros(3)
    return th / (2 * np.sin(th)) * np.array([Rm[2, 1] - Rm[1, 2], Rm[0, 2] - Rm[2, 0], Rm[1, 0] - Rm[0, 1]])
class _R:
    def __init__(s, x): s.x = x
def least_squares(fun, p0, args=(), loss=None, f_scale=1.0, iters=300):
    """Levenberg-Marquardt, sayısal Jacobian, Cauchy benzeri ağırlık (soft_l1)."""
    p = np.array(p0, float); lam = 1e-3
    def cost(p):
        r = fun(p, *args); w = 1 / np.sqrt(1 + (r / f_scale) ** 2); return r, w, np.sum((r * w) ** 2)
    r, w, c = cost(p)
    for _ in range(iters):
        J = np.empty((r.size, p.size))
        for i in range(p.size):
            d = np.zeros_like(p); d[i] = 1e-6 * max(1, abs(p[i])); J[:, i] = (fun(p + d, *args) - r) / d[i]
        Jw = J * w[:, None]; rw = r * w
        A = Jw.T @ Jw; g = Jw.T @ rw
        while True:
            step = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), -g)
            r2, w2, c2 = cost(p + step)
            if c2 < c: p, r, w, c = p + step, r2, w2, c2; lam = max(lam / 3, 1e-9); break
            lam *= 4
            if lam > 1e9: return _R(p)
        if np.linalg.norm(step) < 1e-10 * (1 + np.linalg.norm(p)): break
    return _R(p)
s = open('/home/omarchy/nexremote/site/assets/site.js', encoding='utf-8').read()
K = {m.group(1): np.array(list(map(int, m.group(2).split(','))), float).reshape(4, 2) for m in re.finditer(r'\["([^"]+)",\[([\d,]+)\]\]', s)}
C2 = {k: v.mean(0) for k, v in K.items()}
U = 19.05  # mm
# yerleşim (U); en iyi varyasyon: 5, R, F eksik; F5 x=6.0; F-sıra boşluğu 0.25
L = {"Esc": (0.5, 1.25, 0), "F1": (2.5, 1.25, 0), "F2": (3.5, 1.25, 0), "F3": (4.5, 1.25, 0), "F5": (6.0, 1.25, 0), "F6": (7.0, 1.25, 0), "F7": (8.0, 1.25, 0),
     "~": (0.5, 0, 1), "1": (1.5, 0, 1), "2": (2.5, 0, 1), "3": (3.5, 0, 1), "4": (4.5, 0, 1), "6": (5.5, 0, 1), "7": (6.5, 0, 1), "8": (7.5, 0, 1),
     "Tab": (0.75, -1, 2), "Q": (2.0, -1, 2), "W": (3.0, -1, 2), "E": (4.0, -1, 2), "T": (5.0, -1, 2), "Y": (6.0, -1, 2),
     "Caps": (0.875, -2, 3), "A": (2.25, -2, 3), "S": (3.25, -2, 3), "D": (4.25, -2, 3), "G": (5.25, -2, 3),
     "Z": (2.75, -3, 4), "X": (3.75, -3, 4), "C": (4.75, -3, 4)}
ZR = {0: 11.8, 1: 11.0, 2: 9.2, 3: 8.8, 4: 9.4}   # üst yüz yüksekliği (mm), sahne.py ile aynı
keys = [k for k in L if k in C2]
X3 = np.array([[L[k][0] * U, L[k][1] * U, ZR[L[k][2]]] for k in keys]); X2 = np.array([C2[k] for k in keys])
W, H = 1920, 1080
def project(p, X):
    f, rv, t = p[0], p[1:4], p[4:7]
    Rm = rodrigues(rv); Xc = X @ Rm.T + t
    return np.column_stack([f * Xc[:, 0] / Xc[:, 2] + W / 2, f * Xc[:, 1] / Xc[:, 2] + H / 2])
def res(p, X, Y): return (project(p, X) - Y).ravel()
# başlangıç: önceki homografi çözümünden
k0 = json.load(open('kamera.json')); R0 = np.array(k0['R']); t0 = np.array(k0['t']) * U
p0 = np.r_[k0['f'], to_rotvec(R0), t0]
r = least_squares(res, p0, args=(X3, X2), loss='soft_l1', f_scale=6)
e = np.linalg.norm(project(r.x, X3) - X2, axis=1)
print('medyan', round(float(np.median(e)), 1), 'px; en kötü', sorted(zip(keys, e.round(1)), key=lambda x: -x[1])[:6])
good = [i for i in range(len(keys)) if e[i] < max(3 * np.median(e), 10)]
r = least_squares(res, r.x, args=(X3[good], X2[good]), loss='soft_l1', f_scale=4)
e = np.linalg.norm(project(r.x, X3) - X2, axis=1)
print('aykırılar atıldıktan sonra medyan', round(float(np.median(e)), 1), 'px; atılan', [keys[i] for i in range(len(keys)) if i not in good])
f = r.x[0]; Rm = rodrigues(r.x[1:4]); t = r.x[4:7]
cam_pos = -Rm.T @ t
print('odak', round(f, 1), 'px =', round(f / W * 36, 1), 'mm (36mm sensör); kamera konumu (mm)', cam_pos.round(1))
json.dump(dict(f=float(f), R=Rm.tolist(), t=t.tolist(), layout=L, ZR=ZR, cam=cam_pos.tolist()), open('kamera3d.json', 'w'))
