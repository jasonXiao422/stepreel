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

If missing, install once from the unzipped stepreel folder (uv fetches the right Python and Blender module automatically):

```bash
uv tool install .            # on Windows the bundled bin/uv.exe works too
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
| "像发布会 / 赛博 / 电商 / 奢侈品 ..." | pick a `preset` first (list below), then override single fields |
| "转一圈 / 电商展示" | `camera.preset: turntable` |
| "大气一点 / 仰拍" | `camera.preset: hero` |
| "从上往下看 / 像图纸" | `camera.preset: topdown` or `profile` |
| "先特写再拉远" | `camera.preset: reveal` or `pullback` |
| "从里面飞出来 / 穿越" | `camera.preset: insideout` |
| "贴着表面拍 / 微距" | `camera.preset: skim` or `macro` |
| "一个一个拆 / 像装配说明书" | `explode.mode: sequential` |
| "柔和明亮 / 戏剧化 / 赛博 / 标准 / 夕阳" | `lighting: softbox / dramatic / neon / threepoint / golden` |
| "高级感 / 冷色调 / 胶片感 / 电影感 / 黑白" | `grade: contrast / cool / warm / tealorange / mono` |
| "竖屏 / 抖音" | `output.resolution: [1080, 1920]` |
| "镜头近一点 / 角度高一点" | `camera.zoom`, `camera.elevation` |
| "加标题 / 卖点" | `titles` (styles: title, subtitle, stat, caption) |
| "字幕换个风格 / 字太小 / 换颜色" | `text.style` (classic / minimal / impact / tech / editorial / cinema), `text.size`, `text.color` |
| "不要文字 / 我自己剪辑加字" | `text.enabled: false` |
| "字看不清" | `text.backdrop: plate` |
| "要一份没字的" | `text.clean_copy: true` (writes `<output>_clean.mp4`) |
| "用我的音乐" | `audio.music: path` |
| "模型躺倒了 / 朝向不对" | `model.rotate: [90, 0, 0]` etc. |

Presets: `keynote` 发布会, `midnight` 午夜影棚, `cyberrig` 赛博装配线, `launch` 众筹首发, `teardown` 拆解纪录, `macrovelvet` 微距质感, `shopwindow` 电商橱窗, `heavymetal` 重工金属, `dronepass` 无人机掠影, `bullettime` 子弹时间, `blueprint` 蓝图档案, `filmreel` 胶片广告, `viralshorts` 竖屏快闪, `violetluxe` 暗夜紫金, `insideout` 破壳而出.
Cameras: `orbit` 环绕, `turntable` 转台, `pendulum` 钟摆, `drift` 缓慢漂移, `quarter` 四分之一定格, `bullettime` 子弹时间, `pushin` 缓慢推进, `pullback` 一镜拉远, `reveal` 细节揭幕, `crashzoom` 急推冲击, `vertigo` 希区柯克变焦, `insideout` 破壳而出, `macro` 微距特写, `skim` 贴面掠过, `hero` 英雄仰拍, `flyover` 低空横掠, `corkscrew` 螺旋上升, `spiralin` 螺旋俯冲, `descend` 高空降落, `crane` 摇臂升起, `lowrise` 贴地仰升, `topdown` 俯视, `profile` 正侧平移.
Scenes (`style`): `dark-studio` 暗场影棚, `clean-white` 白色影棚, `tech-blue` 科技蓝, `graphite` 石墨灰棚, `champagne` 香槟米色, `violet` 暗夜紫, `mirror` 镜面黑, `concrete` 工业水泥.

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
