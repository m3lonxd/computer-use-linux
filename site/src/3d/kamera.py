"""Hero karesindeki tuş merkezlerinden (2D) ve ANSI yerleşiminden (düzlem) kamerayı çözer."""
import re, json, numpy as np, itertools
s = open(__import__('os').path.join(__import__('os').path.dirname(__file__), '..', '..', 'assets', 'site.js'), encoding='utf-8').read()
K = {m.group(1): np.array(list(map(int, m.group(2).split(','))), float).reshape(4, 2) for m in re.finditer(r'\["([^"]+)",\[([\d,]+)\]\]', s)}
C2 = {k: v.mean(0) for k, v in K.items()}
def ansi(fgap):
    P = {"Esc": (0.5, 1 + fgap), "F1": (2.5, 1 + fgap), "F2": (3.5, 1 + fgap), "F3": (4.5, 1 + fgap), "F5": (7.0, 1 + fgap), "F6": (8.0, 1 + fgap), "F7": (9.0, 1 + fgap),
         "~": (0.5, 0), "1": (1.5, 0), "2": (2.5, 0), "3": (3.5, 0), "4": (4.5, 0), "6": (6.5, 0), "7": (7.5, 0), "8": (8.5, 0),
         "Tab": (0.75, -1), "Q": (2.0, -1), "W": (3.0, -1), "E": (4.0, -1), "T": (6.0, -1), "Y": (7.0, -1),
         "Caps": (0.875, -2), "A": (2.25, -2), "S": (3.25, -2), "D": (4.25, -2), "G": (6.25, -2),
         "Z": (2.75, -3), "X": (3.75, -3), "C": (4.75, -3)}
    return P
def homog(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A += [[-x, -y, -1, 0, 0, 0, u * x, u * y, u], [0, 0, 0, -x, -y, -1, v * x, v * y, v]]
    _, _, Vt = np.linalg.svd(np.array(A)); H = Vt[-1].reshape(3, 3); return H / H[2, 2]
def proj(H, p):
    q = H @ np.array([p[0], p[1], 1.0]); return q[:2] / q[2]
best = None
for fgap in (0.0, 0.25, 0.5):
    P = ansi(fgap); keys = [k for k in P if k in C2]
    src = [P[k] for k in keys]; dst = [C2[k] for k in keys]
    H = homog(src, dst)
    err = {k: float(np.linalg.norm(proj(H, P[k]) - C2[k])) for k in keys}
    m = np.median(list(err.values()))
    print(f"F-sıra boşluğu {fgap}: medyan hata {m:.1f}px, en kötü", sorted(err.items(), key=lambda x: -x[1])[:4])
    if best is None or m < best[0]: best = (m, fgap, H, err, keys)
m, fgap, H, err, keys = best
# aykırıları at (>3 medyan), yeniden çöz
P = ansi(fgap); good = [k for k in keys if err[k] < max(3 * m, 12)]
H = homog([P[k] for k in good], [C2[k] for k in good])
err2 = {k: float(np.linalg.norm(proj(H, P[k]) - C2[k])) for k in keys}
print("seçilen boşluk", fgap, "kullanılan", len(good), "/", len(keys), "medyan", round(np.median([err2[k] for k in good]), 1), "aykırı:", [k for k in keys if k not in good])
# odak: ana nokta merkezde, kare piksel. H = K [r1 r2 t] (düzlem birimi U)
W, Hh = 1920, 1080; cx, cy = W / 2, Hh / 2
T = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]]); Hc = T @ H
h1, h2 = Hc[:, 0], Hc[:, 1]
# r1·r2=0 ve |r1|=|r2|: f^2 çözümü
f2a = -(h1[0] * h2[0] + h1[1] * h2[1]) / (h1[2] * h2[2])
f2b = (h1[0]**2 + h1[1]**2 - h2[0]**2 - h2[1]**2) / (h2[2]**2 - h1[2]**2)
print("f^2 adayları", f2a, f2b)
f = float(np.sqrt(np.mean([v for v in (f2a, f2b) if v > 0])))
Ki = np.linalg.inv(np.diag([f, f, 1.0]))
r1 = Ki @ h1; r2 = Ki @ h2; lam = 2 / (np.linalg.norm(r1) + np.linalg.norm(r2))
r1 *= lam; r2 *= lam; t = Ki @ Hc[:, 2] * lam; r3 = np.cross(r1, r2)
R = np.column_stack([r1, r2, r3]); U_, _, Vt = np.linalg.svd(R); R = U_ @ Vt
if t[2] < 0: R[:, :2] *= -1; t = -t; R[:, 2] = np.cross(R[:, 0], R[:, 1])
print("odak (px)", round(f, 1), "-> 36mm sensörde", round(f / W * 36, 1), "mm")
json.dump(dict(f=f, R=R.tolist(), t=t.tolist(), fgap=fgap, H=H.tolist(), good=good), open('kamera.json', 'w'))
