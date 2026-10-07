"""Render the UI thumbnails from an example model.

usage: python tools/make_thumbs.py model.step stepreel.yaml out_dir [camera scene lighting grade preset] [--only name,name]
Animated .webp for cameras and presets, .jpg stills for scenes, lighting and grades.
"""
import copy
import os
import sys

import bpy  # noqa: F401  (must import before stepreel.build)
from PIL import Image

from stepreel import config as C
from stepreel.build import build
from stepreel.convert import step_to_glb
from stepreel.overlay import grade

args = [a for a in sys.argv[1:]]
only = None
if "--only" in args:
    i = args.index("--only"); only = set(args[i + 1].split(",")); del args[i:i + 2]
step, cfgp, out = args[:3]
kinds = args[3:] or ["camera", "scene", "lighting", "grade", "preset"]
os.makedirs(out, exist_ok=True)
glb = step_to_glb(step, ".")
tmp = os.path.abspath(os.path.join(out, "_tmp")); os.makedirs(tmp, exist_ok=True)
with open(cfgp, encoding="utf-8") as f:
    import yaml
    user = yaml.safe_load(f) or {}
user.pop("titles", None)


def cfg_for(**over):
    u = copy.deepcopy(user)
    for k, v in over.items():
        if isinstance(v, dict):
            u.setdefault(k, {}).update(v)
        else:
            u[k] = v
    c = C.load_dict(u)
    c["titles"] = []
    c["output"]["resolution"] = [1920, 1080]
    return c


def render_frames(cfg, times, res, samples):
    build(cfg, glb, "preview", tmp)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.cycles.samples = samples
    frames = []
    for i, t in enumerate(times):
        sc.frame_set(int(round(t * cfg["output"]["fps"])) + 1)
        p = os.path.join(tmp, f"t_{i:03d}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        frames.append(Image.open(p).convert("RGB"))
    return frames


def vig(cfg):
    return 0.25 if cfg["style"] not in ("clean-white", "champagne") else 0.0


def animated(cfg, path, n):
    times = [cfg["duration"] * i / n for i in range(n)]
    fr = [grade(f, cfg["grade"], vig(cfg)) for f in render_frames(cfg, times, (320, 180), 4)]
    fr[0].save(path, save_all=True, append_images=fr[1:], duration=int(1000 * cfg["duration"] / n), loop=0, quality=70)


def still(cfg, path, t=None):
    if t is None:
        t = cfg["timeline"]["intro"] + cfg["timeline"]["explode"] + 0.2
    im = render_frames(cfg, [t], (400, 225), 12)[0]
    grade(im, cfg["grade"], vig(cfg)).save(path, quality=85)


def want(name):
    return only is None or name in only


if "camera" in kinds:
    for cam in C.CAMERAS:
        if want(cam):
            animated(cfg_for(camera={"preset": cam}), os.path.join(out, f"camera-{cam}.webp"), 16)
            print("camera", cam, flush=True)
if "scene" in kinds:
    for sc_ in C.STYLES:
        if want(sc_):
            still(cfg_for(style=sc_, lighting="auto", accent=None), os.path.join(out, f"scene-{sc_}.jpg"))
            print("scene", sc_, flush=True)
if "lighting" in kinds:
    for light in C.LIGHTS:
        if want(light):
            still(cfg_for(lighting=light), os.path.join(out, f"lighting-{light}.jpg"))
            print("lighting", light, flush=True)
if "grade" in kinds:
    ref = render_frames(cfg_for(), [1.2], (400, 225), 12)[0]
    for g in C.GRADES:
        if want(g):
            grade(ref, g, 0.25).save(os.path.join(out, f"grade-{g}.jpg"), quality=85)
            print("grade", g, flush=True)
if "preset" in kinds:
    for name in C.PRESETS:
        if want(name):
            u = {k: v for k, v in user.items() if k in ("explode", "model")}
            c = C.load_dict({**u, "preset": name})
            c["titles"] = []; c["output"]["resolution"] = [1920, 1080]
            animated(c, os.path.join(out, f"preset-{name}.webp"), 14)
            print("preset", name, flush=True)
