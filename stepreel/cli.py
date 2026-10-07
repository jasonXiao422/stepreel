"""stepreel command line.

  stepreel init                       写一份带注释的配置文件 stepreel.yaml
  stepreel inspect 模型.STEP           列出零件、自动材质和爆炸分组（给人和 AI 看）
  stepreel preview 模型.STEP           几十秒出低清草稿 + 一张缩略图总览
  stepreel still   模型.STEP --at 1 4  渲染指定时刻的高质量静帧
  stepreel render  模型.STEP           正式渲染成片
  stepreel blend   模型.STEP           导出 .blend，用 Blender 软件手动精调
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

from . import config as C


def _cfg(args):
    path = args.config or ("stepreel.yaml" if os.path.exists("stepreel.yaml") else None)
    cfg = C.load(path)
    if getattr(args, "vertical", False):
        cfg["output"]["resolution"] = [1080, 1920]
    if path:
        print(f"[stepreel] 使用配置 {path}")
    return cfg


def _glb(args):
    from .convert import step_to_glb
    if not os.path.exists(args.model):
        raise SystemExit(f"找不到文件 {args.model}")
    return step_to_glb(args.model, ".", getattr(args, "quality", "normal"))


def _workdir(tag, cfg, glb):
    key = hashlib.sha1((json.dumps(cfg, sort_keys=True, default=str) + glb).encode()).hexdigest()[:10]
    d = os.path.join(".stepreel", f"{tag}_{key}")
    os.makedirs(os.path.join(d, "frames"), exist_ok=True)
    return d


def _ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which("ffmpeg")
        if not exe:
            raise SystemExit("找不到 ffmpeg")
        return exe


def _progress_render(bpy, sc, frames_dir):
    for f in glob.glob(os.path.join(frames_dir, "f_*.png")):
        if os.path.getsize(f) == 0:  # leftover placeholder from an interrupted run
            os.remove(f)
    total = (sc.frame_end - sc.frame_start) // sc.frame_step + 1
    done = len(glob.glob(os.path.join(frames_dir, "f_*.png")))
    if done < total:
        print(f"[stepreel] 渲染 {total} 帧（已完成 {done}），{sc.render.resolution_x}x{sc.render.resolution_y}，设备 {sc.cycles.device}")
        t0 = time.time()
        bpy.ops.render.render(animation=True)
        print(f"[stepreel] 渲染完成，用时 {time.time() - t0:.0f} 秒")


def _compose(cfg, frames_dir, out_dir, step=1):
    from PIL import Image
    from .overlay import draw_titles
    os.makedirs(out_dir, exist_ok=True)
    fps = cfg["output"]["fps"]
    files = sorted(glob.glob(os.path.join(frames_dir, "f_*.png")))
    for i, f in enumerate(files):
        t = i * step / fps
        img = Image.open(f).convert("RGB")
        img = draw_titles(img, t, cfg["titles"], cfg["style"], cfg.get("font"))
        img.save(os.path.join(out_dir, f"c_{i + 1:04d}.png"), compress_level=1)
    return files


def _encode(cfg, comp_dir, audio, out, step=1):
    fps = cfg["output"]["fps"] / step
    cmd = [_ffmpeg(), "-y", "-loglevel", "error", "-framerate", str(fps),
           "-i", os.path.join(comp_dir, "c_%04d.png")]
    if audio:
        cmd += ["-i", audio]
    cmd += ["-vf", "fade=t=in:st=0:d=0.4,fade=t=out:st=%.2f:d=0.4" % (cfg["duration"] - 0.4),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print(f"[stepreel] 输出 {out}")


def _contact_sheet(comp_dir, out, n=8):
    from PIL import Image
    files = sorted(glob.glob(os.path.join(comp_dir, "c_*.png")))
    if not files:
        return
    pick = [files[int(i * (len(files) - 1) / (n - 1))] for i in range(n)]
    ims = [Image.open(p) for p in pick]
    w = 480; h = int(ims[0].height * w / ims[0].width)
    cols = 4; rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), (20, 20, 20))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
    sheet.save(out)
    print(f"[stepreel] 缩略图总览 {out}")


def _make_video(args, mode):
    cfg = _cfg(args)
    glb = _glb(args)
    import bpy
    from .build import build
    from .audio import synth
    wd = _workdir(mode, cfg, os.path.basename(glb))
    frames = os.path.abspath(os.path.join(wd, "frames"))
    ev = build(cfg, glb, mode, frames)
    print(f"[stepreel] {ev['parts']} 个零件，爆炸轴 {ev['axis']}，时长 {cfg['duration']:.1f} 秒")
    _progress_render(bpy, bpy.context.scene, frames)
    comp = os.path.join(wd, "comp")
    step = bpy.context.scene.frame_step
    _compose(cfg, frames, comp, step)
    audio = None
    if cfg["audio"]["enabled"]:
        audio = synth(os.path.join(wd, "audio.wav"), cfg["duration"], ev,
                      music=cfg["audio"]["music"], sfx=cfg["audio"]["sfx"])
        if cfg["audio"]["music"]:
            mixed = os.path.join(wd, "mix.wav")
            subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-i", cfg["audio"]["music"], "-i", audio,
                            "-filter_complex", "[0:a]volume=0.7[m];[m][1:a]amix=inputs=2:duration=shortest",
                            "-t", str(cfg["duration"]), mixed], check=True)
            audio = mixed
    out = args.output or (cfg["output"]["file"] if mode == "render" else "preview.mp4")
    _encode(cfg, comp, audio, out, step)
    if mode == "preview":
        _contact_sheet(comp, os.path.splitext(out)[0] + "_sheet.png")


def cmd_init(args):
    if os.path.exists(args.output) and not args.force:
        raise SystemExit(f"{args.output} 已存在（加 --force 覆盖）")
    text = C.DEFAULT_YAML.lstrip()
    text = re.sub(r"^style: \S+", f"style: {args.style}", text, flags=re.M)
    if args.vertical:
        text = text.replace("resolution: [1920, 1080]", "resolution: [1080, 1920]")
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[stepreel] 已生成 {args.output}")


def cmd_inspect(args):
    cfg = _cfg(args)
    glb = _glb(args)
    import bpy  # noqa
    from .build import load_parts, summarize, pick_axis, obj_bbox
    parts = load_parts(glb, cfg["model"]["rotate"])
    rows = summarize(parts)
    for r in rows:
        r["material"] = next((m["material"] for m in cfg["materials"] if re.search(m["match"], r["name"], re.I)), None)
        r["group"] = next((g["name"] for g in cfg["explode"]["groups"] if re.search(g["match"], r["name"], re.I)), None)
    axis = "xyz"[pick_axis([obj_bbox(o) for o in parts])]
    info = {"file": os.path.basename(args.model), "instances": len(parts), "unique_parts": len(rows),
            "auto_explode_axis": axis, "units": "1.0 = assembly diagonal", "parts": rows}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print(f"{len(parts)} 个零件实例，{len(rows)} 种零件，自动爆炸轴 {axis}")
    for r in rows:
        mat = r["material"] if isinstance(r["material"], str) else (r["material"] or {}).get("color", "")
        print(f"  {r['count']:>3} × {r['name'][:40]:<40} 材质 {mat:<10} 分组 {r['group']}")
    print(f"[stepreel] 详细清单已写入 {args.output}")


def cmd_still(args):
    cfg = _cfg(args)
    glb = _glb(args)
    import bpy
    from PIL import Image
    from .build import build
    from .overlay import draw_titles
    wd = _workdir("still", cfg, os.path.basename(glb))
    build(cfg, glb, "render", os.path.join(wd, "frames"))
    sc = bpy.context.scene
    for t in args.at:
        f = int(round(t * cfg["output"]["fps"])) + 1
        sc.frame_set(f)
        out = f"still_{t:.1f}s.png"
        sc.render.filepath = os.path.abspath(out)
        bpy.ops.render.render(write_still=True)
        img = draw_titles(Image.open(out).convert("RGB"), t, cfg["titles"], cfg["style"], cfg.get("font"))
        img.save(out)
        print(f"[stepreel] 静帧 {out}")


def cmd_blend(args):
    cfg = _cfg(args)
    glb = _glb(args)
    import bpy
    from .build import build
    wd = _workdir("blend", cfg, os.path.basename(glb))
    build(cfg, glb, "render", os.path.abspath(os.path.join(wd, "frames")))
    out = os.path.abspath(args.output or "stepreel_scene.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print(f"[stepreel] 已保存 {out}，用 Blender 打开即可手动调整")


def main(argv=None):
    p = argparse.ArgumentParser(prog="stepreel", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, out_default=None):
        sp.add_argument("model", help="STEP 文件")
        sp.add_argument("-c", "--config", help="配置文件（默认读当前目录 stepreel.yaml）")
        sp.add_argument("-o", "--output", default=out_default)
        sp.add_argument("--vertical", action="store_true", help="竖屏 1080x1920")
        sp.add_argument("--quality", choices=["draft", "normal", "fine"], default="normal", help="网格精度")

    s = sub.add_parser("init"); s.add_argument("-o", "--output", default="stepreel.yaml")
    s.add_argument("--style", default="dark-studio", choices=list(C.STYLES)); s.add_argument("--vertical", action="store_true")
    s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_init)
    s = sub.add_parser("inspect"); common(s, "parts.json"); s.set_defaults(fn=cmd_inspect)
    s = sub.add_parser("preview"); common(s); s.set_defaults(fn=lambda a: _make_video(a, "preview"))
    s = sub.add_parser("render"); common(s); s.set_defaults(fn=lambda a: _make_video(a, "render"))
    s = sub.add_parser("still"); common(s); s.add_argument("--at", type=float, nargs="+", default=[1.0, 4.0])
    s.set_defaults(fn=cmd_still)
    s = sub.add_parser("blend"); common(s); s.set_defaults(fn=cmd_blend)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
