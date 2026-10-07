"""Bump the version everywhere, record release notes, commit and tag.

usage:
  python tools/release.py 0.4.0 "新增 xx 运镜" "修复 xx 问题"   # bump + notes + commit
  git push                                                      # GitHub Actions builds the zip and publishes Release v0.4.0
  python tools/release.py --notes 0.4.0                         # print notes (used by the workflow)
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGES = ROOT / "CHANGELOG.md"
DOWNLOAD_HINT = "解压 zip 后双击 start-stepreel.bat（Mac 双击 start-stepreel.command），详见压缩包里的 使用说明.txt。已安装旧版的用户同样操作，会自动升级。"


def notes_for(ver):
    text = CHANGES.read_text(encoding="utf-8") if CHANGES.exists() else ""
    m = re.search(rf"^## v{re.escape(ver)}\n(.*?)(?=^## v|\Z)", text, re.M | re.S)
    body = m.group(1).strip() if m else ""
    return (body + "\n\n" if body else "") + DOWNLOAD_HINT


def sub(path, pattern, repl):
    p = ROOT / path
    raw = p.read_bytes().decode("utf-8")
    new, n = re.subn(pattern, repl, raw, flags=re.M)
    if n != 1:
        raise SystemExit(f"{path}: 没找到版本号位置")
    p.write_bytes(new.encode("utf-8"))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--notes":
        print(notes_for(sys.argv[2]))
        return
    if len(sys.argv) < 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        raise SystemExit(__doc__)
    ver, items = sys.argv[1], sys.argv[2:]
    sub("pyproject.toml", r'^version = "[^"]+"', f'version = "{ver}"')
    sub("stepreel/__init__.py", r'^__version__ = "[^"]+"', f'__version__ = "{ver}"')
    sub("start-stepreel.bat", r'^set "VER=[^"]+"', f'set "VER={ver}"')
    sub("start-stepreel.command", r"^VER=\S+", f"VER={ver}")
    if items:
        old = CHANGES.read_text(encoding="utf-8") if CHANGES.exists() else "# 更新记录\n"
        head, _, rest = old.partition("\n")
        entry = f"\n## v{ver}\n" + "".join(f"- {i}\n" for i in items)
        CHANGES.write_text(head + "\n" + entry + rest, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-qm", f"Release v{ver}"], cwd=ROOT, check=True)
    print(f"已准备 v{ver}。运行 git push 后会自动打包并发布。")


if __name__ == "__main__":
    main()
