"""STEP -> GLB (tessellated, one node per part instance), cached next to the work dir."""
import hashlib
import os


def cache_dir(workdir="."):
    d = os.path.join(workdir, ".stepreel")
    os.makedirs(d, exist_ok=True)
    return d


def step_to_glb(step_path, workdir=".", quality="normal"):
    import cascadio
    st = os.stat(step_path)
    key = hashlib.sha1(f"{os.path.abspath(step_path)}|{st.st_size}|{st.st_mtime}|{quality}".encode()).hexdigest()[:12]
    out = os.path.join(cache_dir(workdir), f"model_{key}.glb")
    if not os.path.exists(out):
        tol = {"draft": (0.2, 0.8), "normal": (0.05, 0.5), "fine": (0.01, 0.2)}[quality]
        print(f"[stepreel] 转换 STEP → 网格（{quality}）...")
        cascadio.step_to_glb(step_path, out, tol_linear=tol[0], tol_angular=tol[1])
    return out
