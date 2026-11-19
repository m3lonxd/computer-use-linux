"""Computer Use Linux hero sahnesi: 3D klavye + Tux (Blender, Cycles).

Kullanım:
  blender -b -P sahne.py -- --out taban.png [--samples 128] [--press KEY] [--res 1920x1080]
--press verilirse o tuş basılı render edilir (aynı kamera, aynı ışık).
"""
import bpy, bmesh, math, sys, argparse
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="/tmp/taban.png")
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--press", default="")
ap.add_argument("--res", default="1920x1080")
ap.add_argument("--blend", default="")
ap.add_argument("--mode", default="proc", choices=["proc", "proj"])
ap.add_argument("--frac", type=float, default=1.0)
ap.add_argument("--border", default="")   # x0,y0,x1,y1 (0-1, alttan) yalnız bu bölge render edilir
ap.add_argument("--exr", action="store_true")
ap.add_argument("--batch", default="")   # çıktı klasörü: taban + her görünür tuş için yarı/tam basılı bölge renderı
ap.add_argument("--fracs", default="0.5,1.0")   # basış kareleri (TRAVEL oranı)
ap.add_argument("--skip-base", action="store_true")
ap.add_argument("--dump", default="")    # tuşların ekran şekillerini JSON olarak yaz, render alma
A = ap.parse_args(argv)

U = 0.01905            # 1u (m)
TRAVEL = 0.0038        # basış derinliği (m)

# ---------------------------------------------------------------- temizlik
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def mat(name, base, rough=0.5, metal=0.0, coat=0.0, sheen=0.0, emit=None, emit_s=0.0, noise=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Sheen Weight"].default_value = sheen
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_s
    if noise:
        # toz/doku: pürüzlülüğe ve renge hafif gürültü
        tx = nt.nodes.new("ShaderNodeTexNoise"); tx.inputs["Scale"].default_value = 900; tx.inputs["Detail"].default_value = 6
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough - noise; mr.inputs["To Max"].default_value = rough + noise
        nt.links.new(tx.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
        tx2 = nt.nodes.new("ShaderNodeTexNoise"); tx2.inputs["Scale"].default_value = 40
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
        mix.inputs["A"].default_value = (*base, 1); mix.inputs["B"].default_value = (base[0] * 1.35, base[1] * 1.35, base[2] * 1.35, 1)
        nt.links.new(tx2.outputs["Fac"], mix.inputs["Factor"]); nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m

M_CAP = mat("kapak", (0.020, 0.019, 0.023), rough=0.5, sheen=0.35, noise=0.16)
def dust(m, amount=0.55, scale=1800, col=(0.16, 0.15, 0.15), width=0.06):
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    src = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].is_linked else None
    tx = nt.nodes.new("ShaderNodeTexNoise"); tx.inputs["Scale"].default_value = scale; tx.inputs["Detail"].default_value = 2
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = amount; cr.color_ramp.elements[1].position = amount + width
    nt.links.new(tx.outputs["Fac"], cr.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    if src: nt.links.new(src, mix.inputs["A"])
    mix.inputs["B"].default_value = (*col, 1)
    nt.links.new(cr.outputs["Color"], mix.inputs["Factor"]); nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
dust(M_CAP, amount=0.5, scale=70, col=(0.05, 0.048, 0.05), width=0.25)    # geniş leke/toz filmi
dust(M_CAP, amount=0.46, scale=2600, col=(0.24, 0.23, 0.22))              # ince toz zerresi
dust(M_CAP, amount=0.6, scale=420, col=(0.20, 0.19, 0.18))                # iri toz
def grime(m):
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    src = b.inputs["Base Color"].links[0].from_socket
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.003
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 0.85
    nt.links.new(src, mul.inputs["A"]); nt.links.new(ao.outputs["AO"], mul.inputs["B"]) if False else None
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.2; cr.color_ramp.elements[0].color = (0.35, 0.33, 0.33, 1)
    nt.links.new(ao.outputs["AO"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], mul.inputs["B"])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    ed = nt.nodes.new("ShaderNodeValToRGB"); ed.color_ramp.elements[0].position = 0.52; ed.color_ramp.elements[1].position = 0.6
    nt.links.new(geo.outputs["Pointiness"], ed.inputs["Fac"])
    wear = nt.nodes.new("ShaderNodeMix"); wear.data_type = "RGBA"
    wear.inputs["B"].default_value = (0.09, 0.085, 0.085, 1)
    nt.links.new(mul.outputs["Result"], wear.inputs["A"]); nt.links.new(ed.outputs["Color"], wear.inputs["Factor"])
    nt.links.new(wear.outputs["Result"], b.inputs["Base Color"])
grime(M_CAP)
M_LEG = mat("harf", (0.40, 0.37, 0.37), rough=0.7)
M_CASE = mat("kasa", (0.16, 0.06, 0.32), rough=0.42, metal=0.85)
M_PLATE = mat("plaka", (0.01, 0.01, 0.012), rough=0.6)
M_DESK = mat("masa", (0.035, 0.03, 0.03), rough=0.75, noise=0.1)

# ---------------------------------------------------------------- kapak
def keycap(w_u, row):
    """OEM benzeri kapak: alt 18mm, üst ~12.7mm, yükseklik satıra göre, yuvarlatılmış."""
    bw = w_u * U - 0.00105; bd = U - 0.00105
    tw = bw - 0.0052; td = bd - 0.0058
    h = {0: 0.0118, 1: 0.0110, 2: 0.0092, 3: 0.0088, 4: 0.0094, 5: 0.0100}[row]
    bm = bmesh.new()
    hb, ht = 0.0, h
    vb = [bm.verts.new(v) for v in ((-bw/2, -bd/2, hb), (bw/2, -bd/2, hb), (bw/2, bd/2, hb), (-bw/2, bd/2, hb))]
    off = 0.0012  # üst yüz arkaya kayık (eğimli ön duvar)
    vt = [bm.verts.new(v) for v in ((-tw/2, -td/2 + off, ht), (tw/2, -td/2 + off, ht), (tw/2, td/2 + off, ht), (-tw/2, td/2 + off, ht))]
    bm.faces.new(vb[::-1]); bm.faces.new(vt)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    me = bpy.data.meshes.new("kapak"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("kapak", me); sc.collection.objects.link(ob)
    bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = 0.0019; bv.segments = 6; bv.limit_method = "NONE"
    ss = ob.modifiers.new("ss", "SUBSURF"); ss.levels = 2; ss.render_levels = 2
    # çanak: üstten silindir çıkarılır
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.06, depth=bw + 0.01,
                                        location=(0, off, ht + 0.06 - 0.0007), rotation=(0, math.pi / 2, 0))
    cyl = bpy.context.active_object; cyl.display_type = "WIRE"; cyl.hide_render = True
    bo = ob.modifiers.new("canak", "BOOLEAN"); bo.object = cyl; bo.operation = "DIFFERENCE"; bo.solver = "EXACT"
    ob.data.materials.append(M_CAP)
    for p in ob.data.polygons: p.use_smooth = True
    return ob, cyl, h, off

def legend(txt, ob, h, off, row):
    bpy.ops.object.text_add(location=(0, 0, 0))
    t = bpy.context.active_object; t.data.body = txt
    t.data.size = 0.0052 if len(txt) <= 3 else 0.0030
    t.data.align_x = "CENTER"; t.data.align_y = "CENTER"
    t.data.extrude = 0.00004
    t.data.materials.append(M_LEG)
    t.parent = ob
    t.location = (0.0, off + 0.0012, h - 0.0002)
    return t

# ---------------------------------------------------------------- yerleşim
# Fotoğraftaki dizilim (yapay zekâ üretimi): sayı sırasında 5, Q sırasında R, ana sırada F yok.
# (ad, genişlik_U, x_merkez_U) ; y: satır * -1U, F-sırası +1.25U
ROWS = [
    (0, 1.25, [("Esc", 1, 0.5), ("F1", 1, 2.5), ("F2", 1, 3.5), ("F3", 1, 4.5), ("F5", 1, 6.0), ("F6", 1, 7.0), ("F7", 1, 8.0), ("F8", 1, 9.0), ("F9", 1, 10.5), ("F10", 1, 11.5), ("F11", 1, 12.5)]),
    (1, 0.0, [("~", 1, 0.5), ("1 !", 1, 1.5), ("2 @", 1, 2.5), ("3 #", 1, 3.5), ("4 %", 1, 4.5), ("6 ^", 1, 5.5), ("7 &", 1, 6.5), ("8 *", 1, 7.5), ("9 (", 1, 8.5), ("0 )", 1, 9.5), ("-", 1, 10.5), ("=", 1, 11.5), ("Bksp", 2, 13.0)]),
    (2, -1.0, [("Tab", 1.5, 0.75), ("Q", 1, 2.0), ("W", 1, 3.0), ("E", 1, 4.0), ("T", 1, 5.0), ("Y", 1, 6.0), ("U", 1, 7.0), ("I", 1, 8.0), ("O", 1, 9.0), ("P", 1, 10.0), ("[", 1, 11.0), ("]", 1, 12.0)]),
    (3, -2.0, [("Caps", 1.75, 0.875), ("A", 1, 2.25), ("S", 1, 3.25), ("D", 1, 4.25), ("G", 1, 5.25), ("H", 1, 6.25), ("J", 1, 7.25), ("K", 1, 8.25), ("L", 1, 9.25), (";", 1, 10.25), ("Enter", 2.25, 11.875)]),
    (4, -3.0, [("Shift", 2.25, 1.125), ("Z", 1, 2.75), ("X", 1, 3.75), ("C", 1, 4.75), ("V", 1, 5.75), ("B", 1, 6.75), ("N", 1, 7.75), ("M", 1, 8.75), (",", 1, 9.75), (".", 1, 10.75)]),
    (5, -4.0, [("Ctrl", 1.25, 0.625), ("Alt", 1.25, 1.875), ("", 6.25, 5.625)]),
]
import json
HERE = __file__.rsplit("/", 1)[0]
FIT = json.load(open(HERE + "/uydurma.json"))
XC = {}
for _row, _y, _keys in ROWS:
    for _n, _w, _x in _keys: XC[_n.split(" ")[0]] = (_row, _x)
def row_fit(row, xc):
    """Fotoğrafta konumu bilinmeyen tuş: aynı sıradaki en yakın uydurulmuş tuşun dönüşümü."""
    c = [(abs(XC[k][1] - xc), FIT[k]) for k in FIT if k in XC and min(XC[k][0], 4) == min(row, 4)]
    if not c: c = [(0, v) for v in FIT.values()]
    return min(c, key=lambda t: t[0])[1]
caps = {}
root = bpy.data.objects.new("klavye", None); sc.collection.objects.link(root)
for row, yrow, keys in ROWS:
    for name, w, xc in keys:
        ob, cyl, h, off = keycap(w, min(row, 4))
        key = name.split(" ")[0]
        dx, dy, th, sc_ = FIT.get(key) or row_fit(row, xc)
        ob.location = (xc * U + dx / 1000, yrow * U + dy / 1000, 0.0015)
        ob.rotation_euler = (0, 0, th); ob.scale = (sc_, sc_, 1)
        cyl.parent = ob; cyl.location = (0, off, h + 0.06 - 0.0007); cyl.rotation_euler = (0, math.pi / 2, 0)
        if name: legend(name, ob, h, off, row)
        ob.parent = root
        caps[name.split(" ")[0]] = ob
# kasa ve plaka (mm -> m); sol-ön köşe fotoğraftaki gibi kadrajda, sağ ve arka kadraj dışı
X0, X1, Y0, Y1 = -0.75 * U, 14.6 * U, -4.75 * U, 1.9 * U
bpy.ops.mesh.primitive_cube_add(location=((X0 + X1) / 2, (Y0 + Y1) / 2, -0.0085))
case = bpy.context.active_object; case.scale = ((X1 - X0) / 2, (Y1 - Y0) / 2, 0.010)
cb = case.modifiers.new("b", "BEVEL"); cb.width = 0.0025; cb.segments = 5
case.data.materials.append(M_CASE)
bpy.ops.mesh.primitive_plane_add(size=1, location=((X0 + X1) / 2, (Y0 + Y1) / 2, 0.0012))
pl = bpy.context.active_object; pl.scale = (X1 - X0 - 0.004, Y1 - Y0 - 0.004, 1); pl.data.materials.append(M_PLATE)
# kasa altı mor LED şeridi
bpy.ops.mesh.primitive_cube_add(location=((X0 + X1) / 2, (Y0 + Y1) / 2, -0.0190))
led = bpy.context.active_object; led.scale = ((X1 - X0) / 2 + 0.0004, (Y1 - Y0) / 2 + 0.0004, 0.0009)
led.data.materials.append(mat("led", (0, 0, 0), emit=(0.62, 0.22, 1.0), emit_s=60))
# Tux etiketi (marka logosu) kasanın kameraya bakan sol yüzünde
SITE = __file__.rsplit("/src/", 1)[0]
st = bpy.data.materials.new("etiket"); st.use_nodes = True
nt = st.node_tree; b = nt.nodes["Principled BSDF"]
img = nt.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(SITE + "/assets/logo.png")
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs["A"].default_value = (0.10, 0.05, 0.20, 1)
nt.links.new(img.outputs["Color"], mx.inputs["B"]); nt.links.new(img.outputs["Alpha"], mx.inputs["Factor"])
nt.links.new(mx.outputs["Result"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.35
bpy.ops.mesh.primitive_circle_add(vertices=64, radius=0.0072, fill_type="NGON", location=(X0 - 0.00262, -1.7 * U, -0.0085), rotation=(math.pi / 2, 0, -math.pi / 2))
stk = bpy.context.active_object; stk.data.materials.append(st)
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.uv.cube_project(cube_size=0.0144); bpy.ops.object.mode_set(mode="OBJECT")
# gölge yakalayıcı zemin: gölge fotoğrafa düşer, zeminin kendisi görünmez
bpy.ops.mesh.primitive_plane_add(size=2, location=(0.1, 0, -0.0199))
bpy.context.active_object.is_shadow_catcher = True

# ---------------------------------------------------------------- ışık
def area(name, loc, rot, size, color, power):
    d = bpy.data.lights.new(name, "AREA"); d.size = size; d.color = color; d.energy = power
    o = bpy.data.objects.new(name, d); o.location = loc; o.rotation_euler = rot; sc.collection.objects.link(o)
    return o
CEN = Vector((5.0 * U, -1.2 * U, 0.0))
def aim(name, loc, size, color, power, at=CEN):
    o = area(name, loc, (0, 0, 0), size, color, power)
    o.rotation_euler = (at - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return o
# fotoğraf: öne bakan duvarlar bakır (sıcak ışık kamera solunda, alçakta),
# sağa bakan duvarlar mor (sağdan mor), üst yüzler loş gri (zayıf üst dolgu)
aim("sicak_on_sol", (-0.20, -0.22, 0.05), 0.10, (1.0, 0.46, 0.14), 2.1)
aim("mor_sag", (0.42, 0.06, 0.05), 0.18, (0.52, 0.22, 1.0), 2.0)
aim("ust", (0.08, -0.02, 0.40), 0.5, (0.75, 0.78, 0.95), 0.18)
aim("serin_arka", (0.05, 0.35, 0.25), 0.4, (0.6, 0.65, 0.85), 1.2)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.004, 0.006, 1)

# ---------------------------------------------------------------- kamera
# kamera3d.py fotoğraftaki tuş merkezlerinden çözdü (OpenCV ekseni: x sağ, y aşağı, z ileri; mm)
import json
KJ = json.load(open(__file__.rsplit("/", 1)[0] + "/kamera3d.json"))
from mathutils import Matrix
Rcv = Matrix(KJ["R"]); campos = Vector(KJ["cam"]) / 1000.0
Rbl = Rcv.transposed() @ Matrix(((1, 0, 0), (0, -1, 0), (0, 0, -1)))
cd = bpy.data.cameras.new("kam"); cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36.0
cd.lens = KJ["f"] / 1920.0 * 36.0
cam = bpy.data.objects.new("kam", cd); sc.collection.objects.link(cam); sc.camera = cam
cam.matrix_world = Matrix.Translation(campos) @ Rbl.to_4x4()
cd.dof.use_dof = True; cd.dof.aperture_fstop = 5.6
cd.dof.focus_distance = (campos - Vector((4.0 * U, -1.0 * U, 0.01))).length
cd.clip_start = 0.01

# ---------------------------------------------------------------- fotoğraf projeksiyonu
# proj modunda kapaklar, kasa ve plaka fotoğrafın kendisini taşır: UV'ler dinlenme konumunda
# kameradan yansıtılıp sabitlenir; basılan kapak dokusuyla birlikte iner. Işık kullanılmaz.
idx = {}
for i, (n, ob) in enumerate(sorted(caps.items())):
    ob.pass_index = i + 1; idx[n] = i + 1
if A.mode == "proj":
    PH = bpy.data.images.load(SITE + "/media/hero-foto.jpg")
    mp = bpy.data.materials.new("foto"); mp.use_nodes = True; nt = mp.node_tree
    for n_ in list(nt.nodes): nt.nodes.remove(n_)
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = PH; tx.interpolation = "Linear"; tx.extension = "EXTEND"
    em = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tx.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    targets = list(caps.values()) + [case, pl]
    for o in bpy.data.objects:
        if o.type == "FONT" or o.name.startswith("etiket") or o == stk: o.hide_render = True
    led.hide_render = True
    bpy.context.view_layer.update()
    for o in targets:
        if not o.data.uv_layers: o.data.uv_layers.new(name="UV")
        m = o.modifiers.new("proj", "UV_PROJECT"); m.projectors[0].object = cam
        m.aspect_x = 1920; m.aspect_y = 1080; m.uv_layer = o.data.uv_layers[0].name
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.convert(target="MESH")
        o.data.materials.clear(); o.data.materials.append(mp)
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0
    cd.dof.use_dof = False
    for l in [o for o in bpy.data.objects if o.type == "LIGHT"]: l.hide_render = True

# ---------------------------------------------------------------- döküm
if A.dump:
    from bpy_extras.object_utils import world_to_camera_view
    rw, rh = map(int, A.res.split("x")); sc.render.resolution_x = rw; sc.render.resolution_y = rh
    dg = bpy.context.evaluated_depsgraph_get(); D = {}
    for n, ob in caps.items():
        if not n: continue
        ev = ob.evaluated_get(dg); me = ev.to_mesh(); mw = ev.matrix_world
        pts = []
        for v in me.vertices:
            c = world_to_camera_view(sc, cam, mw @ v.co); pts.append((c.x * rw, (1 - c.y) * rh, (mw @ v.co).z))
        ev.to_mesh_clear()
        zmax = max(p[2] for p in pts)
        top = [(x, y) for x, y, z in pts if z > zmax - 0.0006]          # üst yüz (çanak dahil)
        D[n] = {"all": [(round(x, 1), round(y, 1)) for x, y, z in pts], "top": [(round(x, 1), round(y, 1)) for x, y in top]}
    json.dump(D, open(A.dump, "w")); print("DOKUM", A.dump, len(D)); raise SystemExit(0)

# ---------------------------------------------------------------- basış
if A.press:
    caps[A.press].location.z -= TRAVEL * A.frac

# ---------------------------------------------------------------- render
rw, rh = map(int, A.res.split("x"))
r = sc.render; r.engine = "CYCLES"; r.resolution_x = rw; r.resolution_y = rh; r.resolution_percentage = 100
r.filepath = A.out; r.image_settings.file_format = "PNG"
sc.cycles.samples = A.samples; sc.cycles.use_denoising = True; r.film_transparent = True
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -0.4
prefs = bpy.context.preferences.addons["cycles"].preferences
dev = "CPU"
try:
    prefs.compute_device_type = "ONEAPI"; prefs.get_devices()
    if any(d.type == "ONEAPI" for d in prefs.devices):
        for d in prefs.devices: d.use = d.type == "ONEAPI"
        dev = "GPU"
except Exception:
    pass
sc.cycles.device = dev
print("CIHAZ", dev)
vl = bpy.context.view_layer; vl.use_pass_object_index = True; vl.use_pass_z = True
if A.mode == "proj": sc.cycles.samples = min(A.samples, 8); sc.cycles.use_denoising = False
if A.border:
    x0, y0, x1, y1 = map(float, A.border.split(",")); r.use_border = True; r.use_crop_to_border = False
    r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y = x0, y0, x1, y1
if A.exr:
    r.image_settings.file_format = "OPEN_EXR_MULTILAYER"; r.image_settings.color_depth = "32"
    r.filepath = A.out.rsplit(".", 1)[0] + ".exr"
if A.batch:
    # Tek süreçte: önce tam kare taban, sonra her tuş için yalnız kendi bölgesi (aynı tohum,
    # aynı örnek sayısı) yarı ve tam basılı. Bölge tuşun ekran şeklinden 48 px geniş.
    import os
    os.makedirs(A.batch, exist_ok=True)
    DK = json.load(open(A.batch + "/dokum.json"))
    sc.cycles.seed = 7
    if not A.skip_base:
        r.filepath = A.batch + "/taban.png"; bpy.ops.render.render(write_still=True); print("TABAN")
    FR = [float(x) for x in A.fracs.split(",")]
    for n, v in DK.items():
        xs = [p[0] for p in v["all"]]; ys = [p[1] for p in v["all"]]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        if not (0 < cx < rw and 0 < cy < rh): continue
        x0, x1 = max(0, min(xs) - 48) / rw, min(rw, max(xs) + 48) / rw
        y0, y1 = 1 - min(rh, max(ys) + 48) / rh, 1 - max(0, min(ys) - 48) / rh
        r.use_border = True; r.use_crop_to_border = False
        r.border_min_x, r.border_min_y, r.border_max_x, r.border_max_y = x0, y0, x1, y1
        ob = caps[n]; z0 = ob.location.z
        for frac in FR:
            ob.location.z = z0 - TRAVEL * frac
            r.filepath = A.batch + "/%s_%d.png" % (n, round(frac * 100)); bpy.ops.render.render(write_still=True)
        ob.location.z = z0; print("TUS", n)
    r.use_border = False
    raise SystemExit(0)
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=A.blend)
bpy.ops.render.render(write_still=True)
print("YAZILDI", A.out)
