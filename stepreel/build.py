"""Build the Blender scene from a GLB + config. Runs inside the bpy module."""
import math
import re

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from .config import STYLES


# ---------------------------------------------------------------- import
def load_parts(glb, rotate_deg=(0, 0, 0)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    parts = [o for o in bpy.data.objects if o.type == "MESH"]
    if not parts:
        raise SystemExit("STEP 里没有读到任何实体零件")
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            bpy.data.objects.remove(o)

    R = Euler([math.radians(a) for a in rotate_deg]).to_matrix().to_4x4()
    for o in parts:
        o.matrix_world = R @ o.matrix_world
    lo, hi = bbox_all(parts)
    c, diag = (lo + hi) / 2, float(np.linalg.norm(hi - lo)) or 1.0
    M = Matrix.Scale(1.0 / diag, 4) @ Matrix.Translation(Vector(-c))
    for o in parts:
        o.matrix_world = M @ o.matrix_world
    for o in parts:
        for p in o.data.polygons:
            p.use_smooth = True
    return parts


def part_name(o):
    return re.sub(r"\.\d{3}$", "", o.data.name if o.data else o.name)


def obj_bbox(o):
    pts = np.array([list(o.matrix_world @ Vector(c)) for c in o.bound_box])
    return pts.min(0), pts.max(0)


def bbox_all(objs):
    bbs = [obj_bbox(o) for o in objs]
    return np.min([b[0] for b in bbs], 0), np.max([b[1] for b in bbs], 0)


def summarize(parts):
    """Compact part list for humans and LLMs: unique names, counts, size, position."""
    rows = {}
    for o in parts:
        n = part_name(o)
        lo, hi = obj_bbox(o)
        r = rows.setdefault(n, {"name": n, "count": 0, "size": (hi - lo).round(3).tolist(),
                                "center": ((lo + hi) / 2).round(3).tolist()})
        r["count"] += 1
    return sorted(rows.values(), key=lambda r: -max(r["size"]))


# ---------------------------------------------------------------- materials
def _hex(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)


LIB = {
    "steel": dict(color=(0.72, 0.73, 0.75), metal=1.0, rough=0.22),
    "aluminum": dict(color=(0.8, 0.82, 0.85), metal=1.0, rough=0.32),
    "brass": dict(color=(0.85, 0.6, 0.25), metal=1.0, rough=0.25),
    "nylon": dict(color=(0.82, 0.8, 0.74), metal=0.0, rough=0.5),
    "rubber": dict(color=(0.02, 0.02, 0.02), metal=0.0, rough=0.85),
    "pcb": dict(color=(0.02, 0.18, 0.08), metal=0.0, rough=0.35, coat=0.6),
    "carbon": dict(color=(0.02, 0.021, 0.024), metal=0.0, rough=0.32, coat=1.0, weave=True),
}


def make_material(spec, cache={}):
    if isinstance(spec, str):
        if spec not in LIB:
            raise SystemExit(f"未知材质 {spec}，可选: {', '.join(LIB)}，或写 {{type: plastic, color: '#RRGGBB'}}")
        key, p = spec, dict(LIB[spec])
    else:
        t = spec.get("type", "plastic")
        base = dict(LIB.get(t, dict(metal=0.0, rough=0.5)))
        if t == "anodized":
            base.update(metal=0.9, rough=0.35)
        if t == "plastic":
            base.update(metal=0.0, rough=spec.get("roughness", 0.5))
        base["color"] = _hex(spec["color"]) if "color" in spec else base.get("color", (0.5, 0.5, 0.5))
        key, p = repr(sorted(spec.items())), base
    if key in cache and cache[key].name in bpy.data.materials:
        return cache[key]
    m = bpy.data.materials.new(str(spec)[:40])
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*p["color"], 1)
    b.inputs["Metallic"].default_value = p.get("metal", 0)
    b.inputs["Roughness"].default_value = p.get("rough", 0.5)
    b.inputs["Coat Weight"].default_value = p.get("coat", 0)
    m.diffuse_color = (*p["color"], 1)  # used by fast preview
    m.metallic, m.roughness = p.get("metal", 0), p.get("rough", 0.5)
    if p.get("weave"):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        chk = nt.nodes.new("ShaderNodeTexChecker")
        chk.inputs["Scale"].default_value = 1500.0
        chk.inputs["Color1"].default_value = (0.012, 0.012, 0.014, 1)
        chk.inputs["Color2"].default_value = (0.045, 0.047, 0.052, 1)
        nt.links.new(tc.outputs["Object"], chk.inputs["Vector"])
        nt.links.new(chk.outputs["Color"], b.inputs["Base Color"])
    cache[key] = m
    return m


def assign_materials(parts, rules):
    seen = {}
    for o in parts:
        n = part_name(o)
        if n not in seen:
            spec = next((r["material"] for r in rules if re.search(r["match"], n, re.I)), "steel")
            seen[n] = make_material(spec)
        o.data.materials.clear()
        o.data.materials.append(seen[n])


# ---------------------------------------------------------------- explode plan
def pick_axis(bbs):
    """Axis along which parts are stacked = projections onto the other two axes overlap most."""
    lo = np.array([b[0] for b in bbs]); hi = np.array([b[1] for b in bbs])
    best, score_best = 2, -1
    for a in range(3):
        b, c = [i for i in range(3) if i != a]
        ob = np.clip(np.minimum(hi[:, None, b], hi[None, :, b]) - np.maximum(lo[:, None, b], lo[None, :, b]), 0, None)
        oc = np.clip(np.minimum(hi[:, None, c], hi[None, :, c]) - np.maximum(lo[:, None, c], lo[None, :, c]), 0, None)
        area = (hi[:, b] - lo[:, b]) * (hi[:, c] - lo[:, c]) + 1e-9
        s = (ob * oc / np.minimum(area[:, None], area[None, :])).sum() - len(bbs)
        if s > score_best:
            best, score_best = a, s
    return best


def plan_explode(parts, ex, timeline):
    bbs = [obj_bbox(o) for o in parts]
    centers = np.array([(lo + hi) / 2 for lo, hi in bbs])
    glo, ghi = bbox_all(parts)
    C = (glo + ghi) / 2
    axis = {"x": 0, "y": 1, "z": 2}.get(ex["axis"]) if ex["axis"] != "auto" else pick_axis(bbs)
    half = max((ghi - glo)[axis] / 2, 1e-6)
    radial_max = max(np.linalg.norm(centers - C, axis=1).max(), 1e-6)
    D, spread = 0.45, ex["spread"]
    plan = []
    for o, ctr in zip(parts, centers):
        n = part_name(o)
        g = next((g for g in ex["groups"] if re.search(g["match"], n, re.I)), {"distance": 1.0, "delay": 0.3})
        if ex["mode"] == "radial":
            v = ctr - C
            r = np.linalg.norm(v) / radial_max
            d = v / (np.linalg.norm(v) + 1e-9) * D * spread * g["distance"] * (0.3 + 0.7 * r)
        else:
            r = (ctr[axis] - C[axis]) / half
            s = 0 if abs(r) < 0.03 else np.sign(r)
            d = np.zeros(3)
            d[axis] = D * spread * g["distance"] * (0.85 * r + 0.15 * s)
            r = abs(r)
        delay = g["delay"] + (1 - min(r, 1)) * ex["stagger"]
        for ov in ex.get("overrides", []):
            if re.search(ov["match"], n, re.I):
                if "direction" in ov:
                    u = np.array(ov["direction"], float); u /= np.linalg.norm(u) + 1e-9
                    d = u * ov.get("distance", 0.3) * spread
                elif "distance" in ov:
                    d = d / (np.linalg.norm(d) + 1e-9) * ov["distance"] * spread
                delay = ov.get("delay", delay)
        plan.append((o, Vector(d), delay))
    return plan, "xyz"[axis]


def animate_explode(plan, timeline, fps):
    F = lambda s: int(round(s * fps)) + 1
    t_ex = timeline["intro"]
    t_as = timeline["intro"] + timeline["explode"] + timeline["hold"]
    maxd = max(p[2] for p in plan) if plan else 0
    for o, d, delay in plan:
        if d.length < 1e-6:
            continue
        p0 = o.location.copy()
        dur = max(0.5, timeline["explode"] - delay)
        o.keyframe_insert("location", frame=F(t_ex + delay))
        o.location = p0 + d; o.keyframe_insert("location", frame=F(t_ex + delay + dur))
        rdelay = (maxd - delay) * 0.6
        adur = max(0.45, timeline["assemble"] - rdelay)
        o.keyframe_insert("location", frame=F(t_as + rdelay))
        o.location = p0; o.keyframe_insert("location", frame=F(t_as + rdelay + adur))
    return {"explode_start": t_ex, "assemble_start": t_as,
            "assemble_end": t_as + timeline["assemble"], "fast_end": t_ex + 0.3}


# ---------------------------------------------------------------- camera / studio
def fit_distance(lo, hi, lens, aspect):
    r = float(np.linalg.norm(hi - lo)) / 2
    sensor = 36.0
    hfov = 2 * math.atan(sensor / 2 / lens)
    vfov = 2 * math.atan(math.tan(hfov / 2) / aspect) if aspect >= 1 else hfov
    hfov = hfov if aspect >= 1 else 2 * math.atan(math.tan(vfov / 2) * aspect)
    return r / math.sin(min(hfov, vfov) / 2) * 0.72


def setup_camera(cam_cfg, timeline, lo_a, hi_a, lo_e, hi_e, aspect, fps):
    sc = bpy.context.scene
    F = lambda s: int(round(s * fps)) + 1
    target = bpy.data.objects.new("target", None); sc.collection.objects.link(target)
    cd = bpy.data.cameras.new("cam"); cd.lens = cam_cfg["lens"]; cd.clip_start = 0.005
    if aspect < 1:
        cd.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    tr = cam.constraints.new("TRACK_TO"); tr.target = target
    if cam_cfg.get("dof", True):
        cd.dof.use_dof = True; cd.dof.focus_object = target; cd.dof.aperture_fstop = 5.6
    da = fit_distance(lo_a, hi_a, cam_cfg["lens"], aspect) * cam_cfg["zoom"]
    de = fit_distance(lo_e, hi_e, cam_cfg["lens"], aspect) * cam_cfg["zoom"] * 1.08
    ca, ce = Vector((lo_a + hi_a) / 2), Vector((lo_e + hi_e) / 2)
    t = timeline
    T = sum(t[k] for k in ("intro", "explode", "hold", "assemble", "outro"))
    a0, a1, el = cam_cfg["start_angle"], cam_cfg["end_angle"], math.radians(cam_cfg["elevation"])
    keys = [(0, da, ca), (t["intro"], da * 0.96, ca),
            (t["intro"] + t["explode"] * 0.85, de, ce), (t["intro"] + t["explode"] + t["hold"], de * 1.02, ce),
            (T - t["outro"], da, ca), (T, da * 0.97, ca)]
    for s, dist, ctr in keys:
        ang = math.radians(a0 + (a1 - a0) * s / T)
        cam.location = ctr + Vector((math.cos(ang) * math.cos(el), math.sin(ang) * math.cos(el), math.sin(el))) * dist
        cam.keyframe_insert("location", frame=F(s))
        target.location = ctr; target.keyframe_insert("location", frame=F(s))
    return da, de


def setup_studio(style, lo_e, hi_e, dist):
    sc = bpy.context.scene
    st = STYLES[style]
    bpy.ops.mesh.primitive_plane_add(size=50, location=(0, 0, float(lo_e[2]) - 0.04))
    floor = bpy.context.object; floor.name = "floor"
    fm = make_material({"type": "plastic", "color": st["floor"]["color"], "roughness": st["floor"]["rough"]})
    floor.data.materials.append(fm)
    L = dist * 0.9
    for name, direc, rel, ppd, size, color in st["lights"]:
        l = bpy.data.lights.new(name, "AREA")
        d = L * rel
        l.energy = ppd * d * d; l.size = size * L * 0.6; l.color = color
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o)
        o.location = Vector(direc).normalized() * d
        o.rotation_euler = (-o.location).to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("world"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*st["world"], 1); bg.inputs[1].default_value = st["world_strength"]
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = st["look"]


def enable_gpu(want):
    sc = bpy.context.scene
    sc.cycles.device = "CPU"
    if want == "cpu":
        return "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for t in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
            try:
                prefs.compute_device_type = t
            except TypeError:
                continue
            prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == t]
            if devs:
                for d in prefs.devices:
                    d.use = d.type == t
                sc.cycles.device = "GPU"
                return t
    except Exception as e:  # noqa
        print("[stepreel] GPU 检测失败，使用 CPU:", e)
    return "CPU"


def setup_render(cfg, mode, frames_dir):
    sc = bpy.context.scene
    r = sc.render
    W, H = cfg["output"]["resolution"]
    r.fps = cfg["output"]["fps"]
    r.image_settings.file_format = "PNG"
    r.filepath = frames_dir.rstrip("/\\") + "/f_####"
    r.use_overwrite = False; r.use_placeholder = True  # resume interrupted renders
    if mode == "preview":
        # low-res, low-sample Cycles: fast on any machine and shows the real look
        r.engine = "CYCLES"
        r.resolution_x, r.resolution_y = W // 3, H // 3
        c = sc.cycles
        c.samples = 4; c.use_denoising = True; c.use_adaptive_sampling = False
        c.max_bounces = 2; c.diffuse_bounces = 1; c.glossy_bounces = 1; c.transmission_bounces = 0
        c.caustics_reflective = False; c.caustics_refractive = False
        sc.frame_step = 2
        return enable_gpu(cfg["render"]["device"])
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = W, H
    c = sc.cycles
    c.samples = cfg["render"]["samples"]; c.use_denoising = True; c.use_adaptive_sampling = True
    c.max_bounces = 4; c.diffuse_bounces = 2; c.glossy_bounces = 2; c.transmission_bounces = 0
    c.caustics_reflective = False; c.caustics_refractive = False
    return enable_gpu(cfg["render"]["device"])


# ---------------------------------------------------------------- entry
def build(cfg, glb, mode, frames_dir):
    fps = cfg["output"]["fps"]
    W, H = cfg["output"]["resolution"]
    parts = load_parts(glb, cfg["model"]["rotate"])
    assign_materials(parts, cfg["materials"])
    lo_a, hi_a = bbox_all(parts)
    plan, axis = plan_explode(parts, cfg["explode"], cfg["timeline"])
    ex_pts = []
    for o, d, _ in plan:
        lo, hi = obj_bbox(o); ex_pts += [lo + np.array(d), hi + np.array(d)]
    lo_e, hi_e = np.min(ex_pts, 0), np.max(ex_pts, 0)
    events = animate_explode(plan, cfg["timeline"], fps)
    da, de = setup_camera(cfg["camera"], cfg["timeline"], lo_a, hi_a, lo_e, hi_e, W / H, fps)
    setup_studio(cfg["style"], lo_e, hi_e, max(da, de))
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, int(round(cfg["duration"] * fps))
    device = setup_render(cfg, mode, frames_dir)
    n_fast = sum(1 for o, _, delay in plan if delay < 0.15)
    events.update(axis=axis, parts=len(parts), device=device, fast_parts=n_fast)
    return events
