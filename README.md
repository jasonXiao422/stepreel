# stepreel

**把 CAD 装配体（STEP）一键变成产品级爆炸动画。**
Turn a STEP assembly into a studio-quality exploded-view video with one command.

```bash
stepreel render 我的装配体.STEP
```

- 支持 SolidWorks、Fusion 360、Creo、Inventor、UG 等导出的 STEP / STP
- 按零件名自动分材质（碳纤维、铝、钢、尼龙、塑料……），中英文名都认
- 自动判断爆炸方向，紧固件先飞、外层先出、内层后出
- **15 种一键风格**：点一下，场景、运镜、打光、调色、节奏全部调好
- **23 种运镜**：环绕、推拉、希区柯克变焦、从机器内部飞出、贴面掠过、螺旋俯冲、三视图平移等
- 8 种场景、6 种打光、6 种调色，3 种拆解方式（分层、散开、逐个）
- 界面自带新手教程，每个选项都有说明
- 字幕、配乐、音效全部内置，无需素材
- 一个 YAML 文件微调一切；也可以导出 .blend 用 Blender 手动精修
- 自带 Claude Code skill：用中文描述想要的效果，AI 帮你改配置

## 最简单的用法：网页界面

1. 下载并解压本项目
2. **Windows**：双击 `start-stepreel.bat`　**macOS**：双击 `start-stepreel.command`
3. 第一次会自动安装（约 1 GB，几分钟），之后浏览器自动打开界面
4. 拖入 STEP 文件，选风格、填标题，点「生成预览」，满意后点「导出高清视频」

不需要会写代码，也不需要打开终端。模型只在你自己的电脑上处理，不会上传到网上。

**关于下载速度**：Windows 版已内置安装工具，并会依次尝试清华镜像、阿里云镜像和官方源，国内网络一般 3 到 15 分钟装完。中途失败直接重新双击即可，已下载的部分不会重来。

## 命令行安装

只需要先装 [uv](https://docs.astral.sh/uv/)（一行命令），然后：

```bash
uv tool install git+https://github.com/jasonXiao422/stepreel
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
stepreel ui                                    # 打开网页界面
```

## 配置示例

只写和默认不同的部分：

```yaml
preset: cyberrig              # 一键风格，下面的设置会在它的基础上覆盖
style: dark-studio            # 场景
grade: tealorange             # 调色
camera:
  preset: insideout           # 运镜：从机器内部飞出

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

## 风格预设

配置里写一行 `preset: 名字`，其余字段仍可覆盖它。界面里就是上方的「一键风格」。

| preset | 名称 | 效果 |
|---|---|---|
| `keynote` | 发布会 | 白棚慢推，干净克制，像产品发布会开场 |
| `midnight` | 午夜影棚 | 黑场冷暖轮廓光，经典产品片 |
| `cyberrig` | 赛博装配线 | 霓虹螺旋上升，四散爆开，科技感拉满 |
| `launch` | 众筹首发 | 爆点急推，节奏快，适合 Kickstarter 和新品预告 |
| `teardown` | 拆解纪录 | 暖米色工作台俯拍，零件逐个摆开，像拆解测评 |
| `macrovelvet` | 微距质感 | 长焦浅景深贴着零件走，慢节奏，广告质感 |
| `shopwindow` | 电商橱窗 | 白底转台一圈，紧凑爆炸，详情页即插即用 |
| `heavymetal` | 重工金属 | 灰棚单灯高反差，高空螺旋俯冲，大机械的分量感 |
| `dronepass` | 无人机掠影 | 贴地低空横掠，像航拍扫过装配线 |
| `bullettime` | 子弹时间 | 零件悬停时镜头大幅环摆，定格汇报的高光镜头 |
| `blueprint` | 蓝图档案 | 正侧长焦平移，逐个拆解，工程图纸气质 |
| `filmreel` | 胶片广告 | 暖调颗粒慢漂移，复古商业片 |
| `viralshorts` | 竖屏快闪 | 9:16 贴地仰升，快节奏，抖音小红书开箱 |
| `violetluxe` | 暗夜紫金 | 紫棚金色点缀，徐徐拉远，奢侈品开场 |
| `insideout` | 破壳而出 | 镜头从机器内部飞出，爆炸四散，本工具的招牌镜头 |

## 运镜

| camera.preset | 名称 | 分类 | 效果 |
|---|---|---|---|
| `orbit` | 环绕 | 经典环绕 | 绕着产品转大半圈，最通用 |
| `turntable` | 转台 | 经典环绕 | 镜头不动，产品自转一圈 |
| `pendulum` | 钟摆 | 经典环绕 | 左右来回摆动，节奏感强 |
| `drift` | 缓慢漂移 | 经典环绕 | 几乎不动的轻微移动，沉稳高级 |
| `quarter` | 四分之一定格 | 经典环绕 | 停在几个角度依次切换，像多机位 |
| `bullettime` | 子弹时间 | 经典环绕 | 零件悬停时镜头大幅环绕 |
| `pushin` | 缓慢推进 | 推拉变焦 | 从远到近一路推上去 |
| `pullback` | 一镜拉远 | 推拉变焦 | 从局部特写一路拉到全景 |
| `reveal` | 细节揭幕 | 推拉变焦 | 先特写，再拉开看全貌 |
| `crashzoom` | 急推冲击 | 推拉变焦 | 爆炸瞬间猛地推近，冲击力强 |
| `vertigo` | 希区柯克变焦 | 推拉变焦 | 主体大小不变，背景透视在变 |
| `insideout` | 破壳而出 | 微距穿越 | 镜头从机器内部飞出来 |
| `macro` | 微距特写 | 微距穿越 | 长焦浅景深，贴着零件拍 |
| `skim` | 贴面掠过 | 微距穿越 | 沿着零件表面低空滑过 |
| `hero` | 英雄仰拍 | 航拍升降 | 低角度推近，显得高大有分量 |
| `flyover` | 低空横掠 | 航拍升降 | 像无人机贴地扫过 |
| `corkscrew` | 螺旋上升 | 航拍升降 | 绕着产品边转边升高 |
| `spiralin` | 螺旋俯冲 | 航拍升降 | 从高空盘旋着压下来 |
| `descend` | 高空降落 | 航拍升降 | 从正上方慢慢降到平视 |
| `crane` | 摇臂升起 | 航拍升降 | 从近处特写升到高空俯瞰 |
| `lowrise` | 贴地仰升 | 航拍升降 | 从地面视角慢慢抬高 |
| `topdown` | 俯视 | 工程视角 | 从正上方看，像图纸 |
| `profile` | 正侧平移 | 工程视角 | 长焦近乎正交的侧视，像三视图 |

## 场景、打光、调色

| 项目 | 可选值 |
|---|---|
| 场景 `style` | `dark-studio` 暗场影棚、`clean-white` 白色影棚、`tech-blue` 科技蓝、`graphite` 石墨灰棚、`champagne` 香槟米色、`violet` 暗夜紫、`mirror` 镜面黑、`concrete` 工业水泥 |
| 打光 `lighting` | `rim` 轮廓光、`softbox` 柔光棚、`dramatic` 单灯戏剧、`neon` 霓虹、`threepoint` 三点布光、`golden` 黄昏暖阳 |
| 调色 `grade` | `neutral` 原色、`contrast` 高对比、`cool` 冷调科技、`warm` 暖调胶片、`tealorange` 青橙电影、`mono` 黑白纪实 |

## 工作原理

```
STEP ──cascadio──▶ 网格(GLB) ──Blender(bpy)──▶ 材质/爆炸/镜头/灯光 ──Cycles──▶ 帧序列
                                                                  ──Pillow──▶ 字幕
                                                                  ──numpy───▶ 合成音频
                                                                  ──ffmpeg──▶ MP4
```

## 发布新版本（维护者）

```bash
python tools/release.py 0.4.0 "新增 xx 运镜" "修复 xx 问题"
git push
```

脚本会同步改好所有版本号、写入 CHANGELOG.md 并提交。推送后，GitHub Actions 发现版本号变了，就自动打包下载用的 zip（含 uv.exe）并发布到 Releases。版本号没变的推送不会触发发布。用户打开界面时会看到新版本提醒。

## 协议 License

GPL-3.0-or-later。可以自由使用、修改、再分发和出售，再分发时须附带源码并保持同一协议。
本项目依赖 Blender（GPL）等开源组件，第三方组件清单见 `NOTICE.txt`。
用本工具生成的视频归使用者所有，可商用。
