---
name: stepreel
description: Turn a CAD assembly (STEP/STP file from SolidWorks, Fusion, Creo, etc.) into a studio-quality exploded-view product video. Use when the user wants an explode animation, product showcase video, or assembly breakdown from a STEP file.
---

# stepreel: STEP 装配体 → 爆炸动画

All rendering is done by the `stepreel` CLI. Your job is to translate the user's wishes into a small `stepreel.yaml`, check a cheap preview, then render. Do not write Blender code yourself; if the CLI cannot express something, say so and suggest the `blend` command for manual tweaking.

## 0. Check install

```bash
stepreel --help
```

If missing, install once (uv fetches the right Python and Blender module automatically):

```bash
uv tool install git+https://github.com/<owner>/stepreel
```

## 1. Inspect the model (cheap, always do this first)

```bash
stepreel inspect model.step
```

Prints one line per unique part (count, auto material, explode group) and writes `parts.json` with sizes and centers (units: 1.0 = assembly diagonal). Read the console table; open `parts.json` only if you need sizes or positions. Never read the STEP file itself; it is huge.

## 2. Write the config

```bash
stepreel init            # add --style clean-white|tech-blue, --vertical for 9:16
```

Then edit `stepreel.yaml`. Keep edits minimal; untouched keys use defaults. Map user wishes like this:

| User says | Change |
|---|---|
| "慢一点 / 快一点" | scale `timeline.*` |
| "炸开更多 / 更紧凑" | `explode.spread` (0.6 to 1.8) |
| "从中心散开" | `explode.mode: radial` |
| "X 最后飞出 / 往侧面抽出" | `explode.overrides` with `match`, `direction`, `distance`, `delay` |
| "这个零件是铝的 / 换品牌色" | add a rule at the top of `materials` (first match wins) |
| "白色背景 / 苹果风" | `style: clean-white` |
| "转一圈 / 电商展示" | `camera.preset: turntable` |
| "大气一点 / 仰拍" | `camera.preset: hero` |
| "从上往下看 / 像图纸" | `camera.preset: topdown` |
| "先特写再拉远" | `camera.preset: reveal` |
| "一个一个拆 / 像装配说明书" | `explode.mode: sequential` |
| "柔和明亮 / 戏剧化 / 赛博" | `lighting: softbox / dramatic / neon` |
| "高级感 / 冷色调 / 胶片感" | `grade: contrast / cool / warm` |
| "竖屏 / 抖音" | `output.resolution: [1080, 1920]` |
| "镜头近一点 / 角度高一点" | `camera.zoom`, `camera.elevation` |
| "加标题 / 卖点" | `titles` (styles: title, subtitle, stat, caption) |
| "用我的音乐" | `audio.music: path` |
| "模型躺倒了 / 朝向不对" | `model.rotate: [90, 0, 0]` etc. |

Material library: `carbon, steel, aluminum, brass, nylon, rubber, pcb`, or `{type: plastic|anodized, color: "#RRGGBB"}`.
`match` is a case-insensitive regex on the part name; the literal `FASTENERS` expands to a built-in screw/bolt/nut/washer/pin pattern.

Write title copy from what the user tells you and from part names. Do not invent specs or performance numbers.

## 3. Preview (always before a full render)

```bash
stepreel preview model.step
```

Produces `preview.mp4` and `preview_sheet.png` (8 frames in one image). Look at the sheet image, not the video. Check: is the model fully in frame when exploded, does anything overlap badly, are titles readable and not covering the model. Fix the config and preview again. Limit yourself to 3 preview rounds, then show the user.

For a quality check of the look, render one or two stills instead of the whole film:

```bash
stepreel still model.step --at 1.0 4.5
```

## 4. Final render

```bash
stepreel render model.step            # writes output.file (default out.mp4)
```

Renders resume if interrupted. Uses GPU automatically if present. Tell the user roughly how long it will take: run it, note the per-frame time in the log after a few frames, and multiply.

## 5. Manual fine-tuning

```bash
stepreel blend model.step -o scene.blend
```

The user opens `scene.blend` in Blender (free, blender.org) to adjust cameras, lights, materials by hand.

## Token budget

A typical job: one `inspect` table, a 20 to 40 line YAML, one or two contact-sheet images. Avoid reading frame folders, logs in full, or the STEP text.
