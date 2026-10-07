"""Render the UI preset thumbnails from an example model.
usage: python tools/make_thumbs.py model.step stepreel.yaml out_dir
"""
import os, sys, copy
import bpy
from PIL import Image
from stepreel import config as C
from stepreel.build import build
from stepreel.convert import step_to_glb
from stepreel.overlay import grade

step, cfgp, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
glb = step_to_glb(step, ".")
base = C.load(cfgp)
base["titles"] = []
tmp = os.path.abspath(os.path.join(out, "_tmp")); os.makedirs(tmp, exist_ok=True)


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


only = sys.argv[4:] or ["camera", "lighting", "grade"]
if "camera" in only:
    for cam in C.CAMERAS:
        cfg = copy.deepcopy(base); cfg["camera"]["preset"] = cam
        n = 16
        times = [cfg["duration"] * i / n for i in range(n)]
        fr = render_frames(cfg, times, (320, 180), 4)
        fr = [grade(f, "neutral", 0.25) for f in fr]
        fr[0].save(os.path.join(out, f"camera-{cam}.webp"), save_all=True, append_images=fr[1:],
                   duration=int(1000 * cfg["duration"] / n), loop=0, quality=70)
        print("camera", cam)

ref = None
if "lighting" in only or "grade" in only:
    for light in C.LIGHTS:
        cfg = copy.deepcopy(base); cfg["lighting"] = light
        t = cfg["timeline"]["intro"] + cfg["timeline"]["explode"] + 0.2
        im = grade(render_frames(cfg, [t], (400, 225), 12)[0], "neutral", 0.25)
        im.save(os.path.join(out, f"lighting-{light}.jpg"), quality=85)
        if light == "rim":
            ref = render_frames(cfg, [1.2], (400, 225), 12)[0]
        print("lighting", light)

if "grade" in only and ref is not None:
    for g in C.GRADES:
        grade(ref, g, 0.25).save(os.path.join(out, f"grade-{g}.jpg"), quality=85)
        print("grade", g)
