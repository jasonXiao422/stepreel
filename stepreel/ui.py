"""Local web UI: `stepreel ui`. Standard library only; every heavy step runs the CLI in a subprocess."""
import json
import mimetypes
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import yaml

from . import config as C

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("video/mp4", ".mp4")

ROOT = Path(os.environ.get("STEPREEL_HOME", Path.home() / "stepreel-projects"))
WEB = Path(__file__).parent / "web"
JOBS = {}
QUEUE = queue.Queue()
LOCK = threading.Lock()

MATERIALS = {  # UI choice -> config material
    "carbon": "carbon", "steel": "steel", "aluminum": "aluminum", "brass": "brass",
    "nylon": "nylon", "rubber": "rubber", "pcb": "pcb",
    "accent": {"type": "plastic", "color": "ACCENT"},
    "black": {"type": "plastic", "color": "#151517"},
    "white": {"type": "plastic", "color": "#E8E6E1"},
    "anodized": {"type": "anodized", "color": "#2B2D31"},
}
QUALITY = {"standard": ([1280, 720], 16), "high": ([1920, 1080], 32)}


def library():
    """Everything the UI offers, from the single source in config.py / overlay.py."""
    from . import overlay as O
    def items(info, kind, ext):
        return [{"id": k, "name": v[0], "desc": v[1], **({"group": v[2]} if len(v) > 2 else {}),
                 "thumb": f"/thumbs/{kind}-{k}.{ext}"} for k, v in info.items()]
    presets = []
    for k, p in C.PRESETS.items():
        c = p["config"]
        res = c.get("output", {}).get("resolution")
        presets.append({"id": k, "name": p["name"], "desc": p["desc"], "thumb": f"/thumbs/preset-{k}.webp",
                        "set": {"style": c.get("style"), "lighting": c.get("lighting"), "grade": c.get("grade"),
                                "camera": c.get("camera", {}).get("preset"), "accent": c.get("accent"),
                                "speed": c.get("speed", 1.0), "spread": c.get("explode", {}).get("spread", 1.0),
                                "mode": c.get("explode", {}).get("mode", "layers"),
                                "aspect": "vertical" if res and res[1] > res[0] else "landscape"}})
    return {"presets": presets,
            "scene": [dict(i, accent=C.STYLES[i["id"]]["accent"], lighting=C.STYLES[i["id"]]["lighting"])
                      for i in items(C.SCENE_INFO, "scene", "jpg")],
            "camera": items(C.CAMERA_INFO, "camera", "webp"), "camera_groups": C.CAMERA_GROUPS,
            "lighting": items(C.LIGHT_INFO, "lighting", "jpg"),
            "grade": items(C.GRADE_INFO, "grade", "jpg"),
            "mode": [{"id": k, "name": v[0], "desc": v[1]} for k, v in C.EXPLODE_INFO.items()],
            "text": [{"id": k, "name": v["name"], "desc": v["desc"], "thumb": f"/thumbs/text-{k}.jpg"}
                     for k, v in O.TEXT_STYLES.items()],
            "text_samples": [{"id": k, **v} for k, v in O.TEXT_SAMPLES.items()],
            "text_positions": O.TEXT_POSITIONS, "text_anims": O.TEXT_ANIMS, "text_backdrops": O.TEXT_BACKDROPS}


def version_info():
    """Installed version only. No network calls: updates are distributed by the author directly."""
    from . import __version__
    return {"current": __version__}


def _cli(*args):
    return [sys.executable, "-m", "stepreel", *args]


def _env():
    e = dict(os.environ)
    e.update(PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    return e


def project_dir(pid):
    if not re.fullmatch(r"[0-9a-f]{12}", pid or ""):
        raise ValueError("bad project id")
    return ROOT / pid


# ------------------------------------------------------------------ config from UI form
def text_cfg(f):
    """UI text options -> config `text` block (validated, unknown values fall back to defaults)."""
    from .overlay import TEXT_ANIMS, TEXT_BACKDROPS, TEXT_DEFAULTS, TEXT_POSITIONS, TEXT_STYLES
    out = dict(TEXT_DEFAULTS)
    out["enabled"] = bool(f.get("enabled", True))
    if f.get("style") in TEXT_STYLES:
        out["style"] = f["style"]
    c = str(f.get("color") or "auto")
    if c in ("auto", "white", "black", "accent") or re.fullmatch(r"#[0-9a-fA-F]{6}", c):
        out["color"] = c
    try:
        out["size"] = min(1.6, max(0.6, float(f.get("size", 1.0))))
    except (TypeError, ValueError):
        pass
    if f.get("position") in TEXT_POSITIONS:
        out["position"] = f["position"]
    if f.get("animation") in TEXT_ANIMS:
        out["animation"] = f["animation"]
    if f.get("backdrop") in TEXT_BACKDROPS:
        out["backdrop"] = f["backdrop"]
    out["clean_copy"] = bool(f.get("clean_copy", False))
    return out


def text_preview(q):
    """Render the current text settings over the chosen scene thumbnail (fast, Pillow only)."""
    import io
    from PIL import Image
    from .overlay import draw_titles
    style = q.get("style") if q.get("style") in C.STYLES else "dark-studio"
    bg = WEB / "thumbs" / f"scene-{style}.jpg"
    img = Image.open(bg).convert("RGB").resize((960, 540)) if bg.exists() else Image.new("RGB", (960, 540), (20, 23, 29))
    t = q.get("titles") or {}
    titles = []
    if t.get("name"):
        titles.append({"text": t["name"], "style": "title", "start": 0, "end": 99})
    if t.get("sub"):
        titles.append({"text": t["sub"], "style": "subtitle", "start": 0, "end": 99})
    if t.get("stat"):
        titles.append({"text": t["stat"], "style": "stat", "caption": t.get("statcap", ""), "start": 0, "end": 99})
    if t.get("end") and not (t.get("name") or t.get("sub")):
        titles.append({"text": t["end"], "style": "caption", "start": 0, "end": 99})
    accent = q.get("accent") if re.fullmatch(r"#[0-9a-fA-F]{6}", str(q.get("accent"))) else None
    img = draw_titles(img, 5.0, titles, style, None, accent, text_cfg(q.get("text") or {}))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def build_config(form):
    cfg = {
        "style": form.get("style", "dark-studio"),
        "speed": float(form.get("speed", 1.0)),
        "explode": {"spread": float(form.get("spread", 1.0)), "mode": form.get("mode", "layers")},
        "camera": {"zoom": float(form.get("zoom", 1.0)), "preset": form.get("camera", "orbit")},
        "lighting": form.get("lighting", "auto"),
        "grade": form.get("grade", "neutral"),
        "output": {"resolution": [1920, 1080]},
        "titles": [],
    }
    if form.get("accent"):
        cfg["accent"] = form["accent"]
    cfg["text"] = text_cfg(form.get("text") or {})
    vertical = form.get("aspect") == "vertical"
    res, samples = QUALITY.get(form.get("quality", "standard"), QUALITY["standard"])
    cfg["output"]["resolution"] = [res[1], res[0]] if vertical else list(res)
    cfg["render"] = {"samples": samples}
    # per-part materials chosen in the parts table go first so they win
    rules = []
    for name, choice in (form.get("materials") or {}).items():
        if choice in MATERIALS:
            rules.append({"match": "^" + re.escape(name) + "$", "material": MATERIALS[choice]})
    if rules:
        from .config import DEFAULTS
        cfg["materials"] = rules + DEFAULTS["materials"]
    late = [n for n, v in (form.get("last") or {}).items() if v]
    if late:
        cfg["explode"]["overrides"] = [{"match": "^" + re.escape(n) + "$", "delay": 0.9} for n in late]
    if form.get("preset") in C.PRESETS:
        cfg["preset"] = form["preset"]
    # title timing follows the real timeline (preset + speed)
    tl = C.load_dict(cfg)["timeline"]
    intro, ex, hold, asm = tl["intro"], tl["explode"], tl["hold"], tl["assemble"]
    total = intro + ex + hold + asm + tl["outro"]
    t = form.get("titles") or {}
    if t.get("name"):
        cfg["titles"].append({"text": t["name"], "style": "title", "start": 0.3, "end": intro + 0.2, "position": "bottom-left"})
    if t.get("sub"):
        cfg["titles"].append({"text": t["sub"], "style": "subtitle", "start": 0.5, "end": intro + 0.2, "position": "bottom-left"})
    if t.get("stat"):
        cfg["titles"].append({"text": t["stat"], "style": "stat", "caption": t.get("statcap", ""),
                              "start": intro + ex * 0.55, "end": intro + ex + hold - 0.1, "position": "top-left"})
    if t.get("end"):
        cfg["titles"].append({"text": t["end"], "style": "caption", "start": total - 1.2, "end": total + 0.2, "position": "bottom"})
    if not form.get("audio", True):
        cfg["audio"] = {"enabled": False}
    return cfg


# ------------------------------------------------------------------ jobs
def worker():
    while True:
        jid = QUEUE.get()
        job = JOBS[jid]
        if job["status"] == "cancelled":
            continue
        run_job(job)


def run_job(job):
    pdir = project_dir(job["project"])
    cfg_path = pdir / f"job_{job['id']}.yaml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(job["config"], f, allow_unicode=True, sort_keys=False)
    out = f"{job['mode']}_{job['id']}.mp4"
    job.update(status="running", phase="准备模型", started=time.time())
    cmd = _cli(job["mode"], "model.step", "-c", cfg_path.name, "-o", out)
    p = subprocess.Popen(cmd, cwd=pdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         env=_env(), text=True, encoding="utf-8", errors="replace", bufsize=1)
    job["proc"] = p
    tail = []
    for line in p.stdout:
        line = line.rstrip()
        tail = (tail + [line])[-30:]
        if "转换 STEP" in line:
            job["phase"] = "转换模型"
        elif "爆炸轴" in line:
            job["phase"] = "搭建场景"
        m = re.search(r"渲染 (\d+) 帧（已完成 (\d+)）", line)
        if m:
            job.update(total=int(m.group(1)), done=int(m.group(2)), phase="渲染中")
        elif "Saved:" in line:
            job["done"] = job.get("done", 0) + 1
        elif "渲染完成" in line:
            job["phase"] = "合成视频"
    p.wait()
    if job["status"] == "cancelled":
        return
    if p.returncode == 0 and (pdir / out).exists():
        job.update(status="done", phase="完成", output=out, finished=time.time())
        sheet = out.replace(".mp4", "_sheet.png")
        if (pdir / sheet).exists():
            job["sheet"] = sheet
        clean = out.replace(".mp4", "_clean.mp4")
        if (pdir / clean).exists():
            job["clean"] = clean
    else:
        job.update(status="error", phase="出错", log="\n".join(tail))


def public(job):
    return {k: v for k, v in job.items() if k not in ("proc", "config")}


# ------------------------------------------------------------------ HTTP
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n) if n else b""

    def _file(self, path):
        if not path.is_file():
            return self._json({"error": "文件不存在"}, 404)
        size = path.stat().st_size
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
            if m.group(1):
                start = int(m.group(1))
            if m.group(2):
                end = min(int(m.group(2)), size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-cache")
        if "download" in self.path:
            self.send_header("Content-Disposition", f"attachment; filename=\"{path.name}\"")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html"):
                return self._file(WEB / "index.html")
            if u.path == "/api/textpreview":
                body = text_preview(json.loads(parse_qs(u.query).get("q", ["{}"])[0]))
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            if u.path == "/api/library":
                return self._json(library())
            if u.path == "/api/version":
                return self._json(version_info())
            if u.path == "/api/jobs":
                return self._json([public(j) for j in sorted(JOBS.values(), key=lambda j: j["created"])])
            if m := re.fullmatch(r"/api/job/(\w+)", u.path):
                j = JOBS.get(m.group(1))
                return self._json(public(j)) if j else self._json({"error": "没有这个任务"}, 404)
            if m := re.fullmatch(r"/api/project/(\w+)", u.path):
                pdir = project_dir(m.group(1))
                return self._json(json.loads((pdir / "project.json").read_text(encoding="utf-8")))
            if m := re.fullmatch(r"/thumbs/([\w.\-]+)", u.path):
                return self._file(WEB / "thumbs" / m.group(1))
            if m := re.fullmatch(r"/files/(\w+)/([\w.\-]+)", u.path):
                return self._file(project_dir(m.group(1)) / m.group(2))
        except (ValueError, FileNotFoundError) as e:
            return self._json({"error": str(e)}, 404)
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/upload":
            return self.upload(parse_qs(u.query).get("name", ["model.step"])[0])
        if u.path == "/api/job":
            return self.new_job(json.loads(self._body() or b"{}"))
        if m := re.fullmatch(r"/api/job/(\w+)/cancel", u.path):
            j = JOBS.get(m.group(1))
            if j:
                j["status"] = "cancelled"; j["phase"] = "已取消"
                if j.get("proc") and j["proc"].poll() is None:
                    j["proc"].kill()
            return self._json({"ok": True})
        self._json({"error": "not found"}, 404)

    def upload(self, name):
        name = unquote(name)
        if not re.search(r"\.(step|stp)$", name, re.I):
            return self._json({"error": "请上传 .step 或 .stp 文件"}, 400)
        data = self._body()
        if not data.lstrip()[:20].upper().startswith(b"ISO-10303"):
            return self._json({"error": "这个文件不像 STEP 文件，请从 CAD 软件重新导出"}, 400)
        pid = uuid.uuid4().hex[:12]
        pdir = ROOT / pid
        pdir.mkdir(parents=True)
        (pdir / "model.step").write_bytes(data)
        r = subprocess.run(_cli("inspect", "model.step", "-o", "parts.json"), cwd=pdir, env=_env(),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not (pdir / "parts.json").exists():
            shutil.rmtree(pdir, ignore_errors=True)
            return self._json({"error": "读取模型失败：" + (r.stdout + r.stderr)[-600:]}, 500)
        info = json.loads((pdir / "parts.json").read_text(encoding="utf-8"))
        info.update(id=pid, name=name, size=len(data))
        (pdir / "project.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
        self._json(info)

    def new_job(self, body):
        try:
            project_dir(body.get("project"))
        except ValueError:
            return self._json({"error": "请先上传模型"}, 400)
        mode = body.get("mode", "preview")
        if mode not in ("preview", "render"):
            return self._json({"error": "bad mode"}, 400)
        jid = uuid.uuid4().hex[:8]
        JOBS[jid] = {"id": jid, "project": body["project"], "mode": mode, "status": "queued",
                     "phase": "排队中", "done": 0, "total": 0, "created": time.time(),
                     "config": build_config(body.get("form") or {})}
        QUEUE.put(jid)
        self._json(public(JOBS[jid]))


def serve(port=7860, open_browser=True):
    ROOT.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=worker, daemon=True).start()
    for p in range(port, port + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    url = f"http://127.0.0.1:{p}"
    print(f"[stepreel] 界面已启动：{url}")
    print(f"[stepreel] 项目文件保存在 {ROOT}")
    print("[stepreel] 关闭这个窗口即可退出")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
