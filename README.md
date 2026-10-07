# stepreel

**把 CAD 装配体（STEP）一键变成产品级爆炸动画。**
Turn a STEP assembly into a studio-quality exploded-view video with one command.

```bash
stepreel render 我的装配体.STEP
```

- 支持 SolidWorks、Fusion 360、Creo、Inventor、UG 等导出的 STEP / STP
- 按零件名自动分材质（碳纤维、铝、钢、尼龙、塑料……），中英文名都认
- 自动判断爆炸方向，紧固件先飞、外层先出、内层后出
- 自动构图，镜头环绕推拉，工作室灯光
- 字幕、配乐、音效全部内置，无需素材
- 一个 YAML 文件微调一切；也可以导出 .blend 用 Blender 手动精修
- 自带 Claude Code skill：用中文描述想要的效果，AI 帮你改配置

## 安装

只需要先装 [uv](https://docs.astral.sh/uv/)（一行命令），然后：

```bash
uv tool install git+https://github.com/<owner>/stepreel
```

uv 会自动下载正确的 Python 版本、Blender 核心模块、STEP 转换库和 ffmpeg。**不需要单独安装 Blender 软件。**

有 NVIDIA / AMD / Apple 显卡会自动用显卡渲染。

## 30 秒上手

```bash
stepreel inspect 装配体.STEP     # 看看识别出哪些零件、各用什么材质
stepreel init                   # 生成带中文注释的配置文件 stepreel.yaml
stepreel preview 装配体.STEP     # 低清草稿 + 缩略图总览，先看节奏
stepreel render 装配体.STEP      # 正式成片 out.mp4
```

其他：

```bash
stepreel init --style clean-white --vertical   # 白底风格 + 竖屏（抖音 / 小红书）
stepreel still 装配体.STEP --at 1 4.5           # 只渲染两张高清静帧，检查质感
stepreel blend 装配体.STEP -o scene.blend      # 导出场景，用 Blender 手动精修
```

## 配置示例

只写和默认不同的部分：

```yaml
style: dark-studio            # dark-studio | clean-white | tech-blue

explode:
  spread: 1.2                 # 炸开得更开
  overrides:
    - match: "电机|motor"     # 电机最后从侧面抽出
      direction: [1, 0, 0]
      distance: 0.3
      delay: 0.9

materials:                    # 加在最前面的规则优先
  - {match: "外壳|housing", material: {type: anodized, color: "#2B2D31"}}

titles:
  - {text: "产品名", style: title, start: 0.3, end: 2.2, position: bottom-left}
  - {text: "165", style: stat, caption: "个零件", start: 3.4, end: 5.9, position: top-left}
```

完整选项见 `stepreel init` 生成的文件，每一行都有中文注释。

## 和 Claude Code 一起用

把 `skill/` 文件夹复制到 `~/.claude/skills/stepreel/`，然后在 Claude Code 里直接说：

> 用 gearbox.STEP 做一个 10 秒竖屏爆炸动画，白色背景，电机最后飞出来，标题写"XX 减速模组"

Claude 会读零件清单、写配置、看预览图、再正式渲染。整个过程模型只处理零件清单和一个几十行的配置文件，token 消耗很低。

## 小技巧

- **零件命名决定材质。** 在 SolidWorks 里把零件名写清楚（含"碳纤维""铝""螺钉"等），自动分配会更准。
- **模型朝向不对**：配置里 `model.rotate: [90, 0, 0]`。
- **渲染中断**：重新运行同一命令会从断点继续。
- **网格太粗或太慢**：`--quality fine` / `--quality draft`。

## 工作原理

```
STEP ──cascadio──▶ 网格(GLB) ──Blender(bpy)──▶ 材质/爆炸/镜头/灯光 ──Cycles──▶ 帧序列
                                                                  ──Pillow──▶ 字幕
                                                                  ──numpy───▶ 合成音频
                                                                  ──ffmpeg──▶ MP4
```

## License

MIT. 生成的视频归你所有。
