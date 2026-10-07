"""Config: one commented YAML template is the single source of defaults."""
import copy
import yaml

FASTENER_RE = r"螺钉|螺栓|螺丝|螺母|铆钉|挡圈|卡簧|销钉|垫片|垫圈|screw|bolt|nut|rivet|washer|circlip|pin"

DEFAULT_YAML = r"""
# stepreel 配置文件。只改你想改的行，其余保持默认。
# 时间单位都是秒；距离单位是"模型尺寸"，1.0 = 整个装配体对角线长度。

output:
  file: out.mp4
  resolution: [1920, 1080]     # 竖屏用 [1080, 1920]
  fps: 24

preset: null                   # 一键风格名（见 README「风格预设」）；下面改过的值会覆盖它，没改的跟随预设
style: dark-studio             # 场景：dark-studio | clean-white | tech-blue | graphite | champagne | violet | mirror | concrete
lighting: auto                 # 打光：rim | softbox | dramatic | neon | threepoint | golden；auto = 跟场景搭配
grade: neutral                 # 调色：neutral | contrast | cool | warm | tealorange | mono
accent: null                   # 主色（塑料件和副标题），例 "#F25213"；null = 用风格默认色
speed: 1.0                     # 整体节奏，>1 更快，<1 更慢

model:
  rotate: [0, 0, 0]            # 模型整体旋转（度），朝向不对时调
  up_axis: auto                # 保留

timeline:
  intro: 2.0                   # 装配状态展示
  explode: 2.2                 # 爆炸过程
  hold: 1.6                    # 爆炸状态停留
  assemble: 1.6                # 合拢过程
  outro: 0.8                   # 结尾停留

explode:
  mode: layers                 # layers 分层拆开 | radial 向四周散开 | sequential 逐个拆解
  axis: auto                   # auto | x | y | z
  spread: 1.0                  # 整体爆炸距离倍数
  stagger: 0.4                 # 外层零件比内层早多少秒出发
  groups:                      # 从上到下匹配零件名（正则），先匹配先生效；delay 越小越早飞
    - name: fasteners
      match: "FASTENERS"
      distance: 1.5
      delay: 0.0
    - name: parts
      match: ".*"
      distance: 1.0
      delay: 0.35
  overrides: []                # 单独指定某些零件，例：
  #  - match: "舵机"
  #    direction: [1, 0, 0]    # 世界坐标方向
  #    distance: 0.4
  #    delay: 0.8

materials:                     # 从上到下匹配零件名；material 可写库名或 {type, color}
  - {match: "碳纤维|carbon", material: carbon}
  - {match: "打印|printed|3d", material: {type: plastic, color: ACCENT}}
  - {match: "尼龙|衬套|nylon|bushing", material: nylon}
  - {match: "FASTENERS", material: steel}
  - {match: "板|座|架|护|壳|盖|bracket|plate|mount|housing|cover|frame", material: {type: plastic, color: ACCENT}}
  - {match: "铝|alu", material: aluminum}
  - {match: "钢|steel|轴|shaft", material: steel}
  - {match: "铜|brass|copper", material: brass}
  - {match: "橡胶|rubber|tire|轮胎", material: rubber}
  - {match: "码盘|horn", material: aluminum}
  - {match: "舵机|电机|motor|servo", material: {type: plastic, color: "#151517"}}
  - {match: "电路|pcb", material: pcb}
  - {match: "齿轮|gear", material: {type: plastic, color: "#E8E6E1"}}
  - {match: ".*", material: {type: plastic, color: ACCENT}}

camera:
  preset: orbit                # 运镜，共 23 种（orbit/hero/topdown/turntable/reveal/pushin/pullback/insideout/
                               # flyover/corkscrew/descend/pendulum/profile/macro/lowrise/quarter/spiralin/drift/
                               # crane/crashzoom/bullettime/vertigo/skim），效果见 README 或界面缩略图
  start_angle: -70             # 环绕起始角度（度，仅 orbit）
  end_angle: -5                # 环绕结束角度（仅 orbit）
  elevation: null              # 俯视角（度）；null = 用运镜默认
  zoom: 1.0                    # >1 拉远，<1 推近
  lens: 40
  dof: true

titles: []                     # 字幕，例：
#  - {text: "产品名", style: title, start: 0.3, end: 2.2, position: bottom-left}
#  - {text: "PRODUCT NAME", style: subtitle, start: 0.5, end: 2.2, position: bottom-left}
#  - {text: "165", style: stat, caption: "个零件", start: 3.4, end: 5.9, position: top-left}
#  - {text: "SolidWorks 建模 · 代码渲染", style: caption, start: 7.0, end: 8.2, position: bottom}
font: auto                     # 或字体文件路径；auto 会找系统中文字体
text:
  enabled: true                # false = 不加任何文字（自己在剪辑软件里加）
  style: classic               # 字幕样式：classic 经典 | minimal 极简细字 | impact 粗体冲击 | tech 科技标注 | editorial 杂志衬线 | cinema 电影字幕
  color: auto                  # auto | white | black | accent | "#RRGGBB"
  size: 1.0                    # 文字整体大小倍数
  position: auto               # auto（跟随样式）| bottom-left | bottom | center | top-left
  animation: auto              # auto（跟随样式）| fade 淡入 | rise 上滑 | type 打字机 | expand 展开
  backdrop: shadow             # shadow 阴影 | plate 半透明底板 | none
  clean_copy: false            # true = 正式渲染时额外导出一份无文字版（xxx_clean.mp4）

audio:
  enabled: true
  music: null                  # 背景音乐文件路径；null = 自动合成
  sfx: true                    # 爆炸/合拢音效

render:
  samples: 32                  # 越高越干净越慢
  device: auto                 # auto | gpu | cpu
"""

DEFAULTS = yaml.safe_load(DEFAULT_YAML)

STYLES = {  # backgrounds
    "dark-studio": {
        "accent": "#F25213", "lighting": "rim",
        "world": (0.006, 0.007, 0.01), "world_strength": 1.0,
        "floor": {"color": "#020203", "rough": 0.6},
        "look": "AgX - Medium High Contrast",
        "text": "#FFFFFF", "text_dim": "#C8C8C8",
    },
    "clean-white": {
        "accent": "#2F6BFF", "lighting": "softbox",
        "world": (0.85, 0.86, 0.88), "world_strength": 0.6,
        "floor": {"color": "#E9EAEC", "rough": 0.6},
        "look": "AgX - Base Contrast",
        "text": "#16181D", "text_dim": "#4A4F59",
    },
    "tech-blue": {
        "accent": "#00C2FF", "lighting": "neon",
        "world": (0.003, 0.01, 0.025), "world_strength": 1.0,
        "floor": {"color": "#020814", "rough": 0.5},
        "look": "AgX - High Contrast",
        "text": "#FFFFFF", "text_dim": "#9ED8FF",
    },
    "graphite": {
        "accent": "#E03A2F", "lighting": "softbox",
        "world": (0.045, 0.047, 0.05), "world_strength": 1.0,
        "floor": {"color": "#3A3D42", "rough": 0.5},
        "look": "AgX - Medium High Contrast",
        "text": "#FFFFFF", "text_dim": "#C9CCD1",
    },
    "champagne": {
        "accent": "#B46A4A", "lighting": "softbox",
        "world": (0.82, 0.78, 0.72), "world_strength": 0.65,
        "floor": {"color": "#E8E0D4", "rough": 0.6},
        "look": "AgX - Base Contrast",
        "text": "#2A241C", "text_dim": "#6B6154",
    },
    "violet": {
        "accent": "#E0B45C", "lighting": "dramatic",
        "world": (0.012, 0.008, 0.02), "world_strength": 1.0,
        "floor": {"color": "#0A0712", "rough": 0.35},
        "look": "AgX - High Contrast",
        "text": "#FFFFFF", "text_dim": "#CBB8E8",
    },    "mirror": {
        "accent": "#FF5A1F", "lighting": "rim",
        "world": (0.004, 0.004, 0.005), "world_strength": 1.0,
        "floor": {"color": "#050506", "rough": 0.12, "spec": 0.12}, "no_top_light": True,
        "look": "AgX - Medium High Contrast",
        "text": "#FFFFFF", "text_dim": "#C8C8C8",
    },
    "concrete": {
        "accent": "#F2B705", "lighting": "threepoint",
        "world": (0.11, 0.11, 0.105), "world_strength": 0.8,
        "floor": {"color": "#6E6C68", "rough": 0.85, "noise": True},
        "look": "AgX - Medium High Contrast",
        "text": "#FFFFFF", "text_dim": "#E2E0DA",
    },
}

# (name, direction from model, relative distance, power per d^2, relative size, color)
LIGHTS = {
    "rim": [
        ("key", (-0.6, -0.8, 0.9), 1.0, 15, 0.6, (1, 0.97, 0.93)),
        ("fill", (0.9, -0.4, 0.3), 1.0, 3, 0.8, (0.85, 0.9, 1.0)),
        ("rim_cool", (-0.7, 0.7, 0.3), 1.0, 28, 0.3, (0.35, 0.6, 1.0)),
        ("rim_warm", (0.8, 0.6, 0.4), 1.0, 28, 0.3, (1.0, 0.45, 0.15)),
        ("top", (0.0, 0.0, 1.0), 1.1, 4, 1.2, (1, 1, 1)),
    ],
    "softbox": [
        ("key", (-0.6, -0.7, 1.0), 1.0, 10, 1.4, (1, 0.98, 0.95)),
        ("fill", (0.9, -0.3, 0.5), 1.0, 6, 1.6, (1, 1, 1)),
        ("back", (0.0, 0.9, 0.6), 1.0, 8, 1.0, (1, 1, 1)),
        ("top", (0.0, 0.0, 1.0), 1.1, 5, 1.6, (1, 1, 1)),
    ],
    "dramatic": [
        ("key", (-0.35, -0.25, 1.0), 1.0, 40, 0.25, (1, 0.95, 0.88)),
        ("rim", (0.6, 0.8, 0.25), 1.0, 14, 0.2, (0.6, 0.75, 1.0)),
    ],
    "neon": [
        ("key", (-0.6, -0.8, 0.9), 1.0, 6, 0.6, (0.9, 0.95, 1.0)),
        ("cyan", (-0.8, 0.6, 0.55), 1.0, 12, 0.3, (0.0, 0.8, 1.0)),
        ("magenta", (0.85, 0.5, 0.6), 1.0, 16, 0.3, (1.0, 0.15, 0.75)),
        ("top", (0.0, 0.0, 1.0), 1.1, 3, 1.2, (0.7, 0.85, 1.0)),
    ],    "threepoint": [
        ("key", (-0.7, -0.6, 0.7), 1.0, 14, 0.9, (1, 0.97, 0.92)),
        ("fill", (0.8, -0.5, 0.35), 1.0, 5, 1.2, (0.92, 0.95, 1.0)),
        ("back", (0.2, 0.9, 0.7), 1.0, 18, 0.5, (1, 1, 1)),
    ],
    "golden": [
        ("sun", (-0.9, -0.2, 0.35), 1.0, 30, 0.5, (1.0, 0.72, 0.42)),
        ("sky", (0.3, 0.6, 1.0), 1.1, 4, 1.6, (0.55, 0.68, 1.0)),
        ("bounce", (0.8, -0.6, 0.1), 1.0, 3, 1.2, (1.0, 0.85, 0.7)),
    ],
}

GRADES = ["neutral", "contrast", "cool", "warm", "tealorange", "mono"]
CAMERAS = ["orbit", "hero", "topdown", "turntable", "reveal", "pushin", "pullback", "insideout", "flyover",
           "corkscrew", "descend", "pendulum", "profile", "macro", "lowrise", "quarter", "spiralin", "drift",
           "crane", "crashzoom", "bullettime", "vertigo", "skim"]

# Display names for the UI and docs: key -> (名称, 说明[, 分组])
SCENE_INFO = {
    "dark-studio": ("暗场影棚", "黑色背景，产品片最常用"),
    "clean-white": ("白色影棚", "干净白底，官网和电商常用"),
    "tech-blue": ("科技蓝", "深蓝夜色，科技发布感"),
    "graphite": ("石墨灰棚", "中性深灰，突出金属质感"),
    "champagne": ("香槟米色", "暖米色工作台，柔和高级"),
    "violet": ("暗夜紫", "深紫背景，适合配金色点缀"),
    "mirror": ("镜面黑", "地面带倒影，奢华发布感"),
    "concrete": ("工业水泥", "粗糙水泥地面，硬朗工业风"),
}
LIGHT_INFO = {
    "rim": ("轮廓光", "冷暖边光勾出轮廓"),
    "softbox": ("柔光棚", "均匀明亮，像官网产品图"),
    "dramatic": ("单灯戏剧", "一盏顶光，明暗强烈"),
    "neon": ("霓虹", "青色和品红边光"),
    "threepoint": ("三点布光", "主光、补光、背光，最稳妥的标准布光"),
    "golden": ("黄昏暖阳", "低角度暖色侧光，像傍晚阳光"),
}
GRADE_INFO = {
    "neutral": ("原色", "不做额外调色"),
    "contrast": ("高对比", "更硬朗、更饱和"),
    "cool": ("冷调科技", "暗部偏青，干净利落"),
    "warm": ("暖调胶片", "柔和、有颗粒感"),
    "tealorange": ("青橙电影", "暗部青、亮部橙，好莱坞大片色"),
    "mono": ("黑白纪实", "黑白高反差，纪录片气质"),
}
CAMERA_GROUPS = ["经典环绕", "推拉变焦", "微距穿越", "航拍升降", "工程视角"]
CAMERA_INFO = {
    "orbit": ("环绕", "绕着产品转大半圈，最通用", "经典环绕"),
    "turntable": ("转台", "镜头不动，产品自转一圈", "经典环绕"),
    "pendulum": ("钟摆", "左右来回摆动，节奏感强", "经典环绕"),
    "drift": ("缓慢漂移", "几乎不动的轻微移动，沉稳高级", "经典环绕"),
    "quarter": ("四分之一定格", "停在几个角度依次切换，像多机位", "经典环绕"),
    "bullettime": ("子弹时间", "零件悬停时镜头大幅环绕", "经典环绕"),
    "pushin": ("缓慢推进", "从远到近一路推上去", "推拉变焦"),
    "pullback": ("一镜拉远", "从局部特写一路拉到全景", "推拉变焦"),
    "reveal": ("细节揭幕", "先特写，再拉开看全貌", "推拉变焦"),
    "crashzoom": ("急推冲击", "爆炸瞬间猛地推近，冲击力强", "推拉变焦"),
    "vertigo": ("希区柯克变焦", "主体大小不变，背景透视在变", "推拉变焦"),
    "insideout": ("破壳而出", "镜头从机器内部飞出来", "微距穿越"),
    "macro": ("微距特写", "长焦浅景深，贴着零件拍", "微距穿越"),
    "skim": ("贴面掠过", "沿着零件表面低空滑过", "微距穿越"),
    "hero": ("英雄仰拍", "低角度推近，显得高大有分量", "航拍升降"),
    "flyover": ("低空横掠", "像无人机贴地扫过", "航拍升降"),
    "corkscrew": ("螺旋上升", "绕着产品边转边升高", "航拍升降"),
    "spiralin": ("螺旋俯冲", "从高空盘旋着压下来", "航拍升降"),
    "descend": ("高空降落", "从正上方慢慢降到平视", "航拍升降"),
    "crane": ("摇臂升起", "从近处特写升到高空俯瞰", "航拍升降"),
    "lowrise": ("贴地仰升", "从地面视角慢慢抬高", "航拍升降"),
    "topdown": ("俯视", "从正上方看，像图纸", "工程视角"),
    "profile": ("正侧平移", "长焦近乎正交的侧视，像三视图", "工程视角"),
}
EXPLODE_INFO = {
    "layers": ("分层拆开", "沿一个方向一层层分开"),
    "radial": ("向四周散开", "从中心向外炸开"),
    "sequential": ("逐个拆解", "一种零件一种零件依次飞出，像装配说明书"),
}

# One-click looks: a named, fully-tuned combination. User config still overrides any field.
PRESETS = {
    "keynote": {"name": "发布会", "desc": "白棚慢推，干净克制，像产品发布会开场", "config": {
        "style": "clean-white", "lighting": "softbox", "grade": "neutral", "accent": "#2F6BFF",
        "speed": 0.85, "camera": {"preset": "pushin"}, "explode": {"spread": 0.9}}},
    "midnight": {"name": "午夜影棚", "desc": "黑场冷暖轮廓光，经典产品片", "config": {
        "style": "dark-studio", "lighting": "rim", "grade": "cool", "accent": "#F25213",
        "speed": 1.0, "camera": {"preset": "orbit"}, "explode": {"spread": 1.0}}},
    "cyberrig": {"name": "赛博装配线", "desc": "霓虹螺旋上升，四散爆开，科技感拉满", "config": {
        "style": "tech-blue", "lighting": "neon", "grade": "contrast", "accent": "#00C2FF",
        "speed": 1.15, "camera": {"preset": "corkscrew"}, "explode": {"spread": 1.2, "mode": "radial"}}},
    "launch": {"name": "众筹首发", "desc": "爆点急推，节奏快，适合 Kickstarter 和新品预告", "config": {
        "style": "dark-studio", "lighting": "rim", "grade": "contrast", "accent": "#FF8A00",
        "speed": 1.25, "camera": {"preset": "crashzoom"}, "explode": {"spread": 1.3}}},
    "teardown": {"name": "拆解纪录", "desc": "暖米色工作台俯拍，零件逐个摆开，像拆解测评", "config": {
        "style": "champagne", "lighting": "softbox", "grade": "neutral", "accent": "#B46A4A",
        "speed": 0.9, "camera": {"preset": "topdown"}, "explode": {"spread": 1.1, "mode": "sequential"}}},
    "macrovelvet": {"name": "微距质感", "desc": "长焦浅景深贴着零件走，慢节奏，广告质感", "config": {
        "style": "dark-studio", "lighting": "dramatic", "grade": "warm", "accent": "#D4A24E",
        "speed": 0.7, "camera": {"preset": "macro"}, "explode": {"spread": 0.7}}},
    "shopwindow": {"name": "电商橱窗", "desc": "白底转台一圈，紧凑爆炸，详情页即插即用", "config": {
        "style": "clean-white", "lighting": "softbox", "grade": "neutral", "accent": "#16A06C",
        "speed": 1.0, "camera": {"preset": "turntable"}, "explode": {"spread": 0.85}}},
    "heavymetal": {"name": "重工金属", "desc": "灰棚单灯高反差，高空螺旋俯冲，大机械的分量感", "config": {
        "style": "graphite", "lighting": "dramatic", "grade": "contrast", "accent": "#E03A2F",
        "speed": 1.2, "camera": {"preset": "spiralin"}, "explode": {"spread": 1.6, "mode": "radial"}}},
    "dronepass": {"name": "无人机掠影", "desc": "贴地低空横掠，像航拍扫过装配线", "config": {
        "style": "dark-studio", "lighting": "rim", "grade": "cool", "accent": "#7FB2FF",
        "speed": 1.0, "camera": {"preset": "flyover"}, "explode": {"spread": 1.1}}},
    "bullettime": {"name": "子弹时间", "desc": "零件悬停时镜头大幅环摆，定格汇报的高光镜头", "config": {
        "style": "dark-studio", "lighting": "rim", "grade": "cool", "accent": "#9AE6FF",
        "speed": 0.95, "camera": {"preset": "bullettime"}, "explode": {"spread": 1.4},
        "timeline": {"hold": 2.4}}},
    "blueprint": {"name": "蓝图档案", "desc": "正侧长焦平移，逐个拆解，工程图纸气质", "config": {
        "style": "tech-blue", "lighting": "neon", "grade": "cool", "accent": "#7FD1FF",
        "speed": 0.95, "camera": {"preset": "profile"}, "explode": {"spread": 1.0, "mode": "sequential"}}},
    "filmreel": {"name": "胶片广告", "desc": "暖调颗粒慢漂移，复古商业片", "config": {
        "style": "champagne", "lighting": "softbox", "grade": "warm", "accent": "#B46A4A",
        "speed": 0.8, "camera": {"preset": "drift"}, "explode": {"spread": 0.95}}},
    "viralshorts": {"name": "竖屏快闪", "desc": "9:16 贴地仰升，快节奏，抖音小红书开箱", "config": {
        "style": "dark-studio", "lighting": "rim", "grade": "contrast", "accent": "#FF4D6D",
        "speed": 1.4, "camera": {"preset": "lowrise"}, "explode": {"spread": 1.2},
        "output": {"resolution": [1080, 1920]}}},
    "violetluxe": {"name": "暗夜紫金", "desc": "紫棚金色点缀，徐徐拉远，奢侈品开场", "config": {
        "style": "violet", "lighting": "dramatic", "grade": "warm", "accent": "#E0B45C",
        "speed": 0.8, "camera": {"preset": "pullback"}, "explode": {"spread": 0.9}}},
    "insideout": {"name": "破壳而出", "desc": "镜头从机器内部飞出，爆炸四散，本工具的招牌镜头", "config": {
        "style": "dark-studio", "lighting": "rim", "grade": "cool", "accent": "#66E0FF",
        "speed": 1.1, "camera": {"preset": "insideout"}, "explode": {"spread": 1.0, "mode": "radial"}}},
}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load(path=None):
    user = {}
    if path:
        with open(path, encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
    return load_dict(user)


def _changed(user, defaults):
    """Keep only values that differ from the defaults (an `init` file spells every default out)."""
    out = {}
    for k, v in (user or {}).items():
        d = defaults.get(k) if isinstance(defaults, dict) else None
        if isinstance(v, dict) and isinstance(d, dict):
            sub = _changed(v, d)
            if sub:
                out[k] = sub
        elif v != d:
            out[k] = v
    return out


def load_dict(user):
    base = DEFAULTS
    name = (user or {}).get("preset") or DEFAULTS.get("preset")
    if name:
        if name not in PRESETS:
            raise SystemExit(f"未知预设 preset: {name}，可选: {', '.join(PRESETS)}")
        base = _merge(DEFAULTS, PRESETS[name]["config"])
        user = _changed(user, DEFAULTS)  # only values the user actually changed override the preset
    cfg = _merge(base, user)
    if cfg["style"] not in STYLES:
        raise SystemExit(f"未知风格 style: {cfg['style']}，可选: {', '.join(STYLES)}")
    style = STYLES[cfg["style"]]
    if cfg.get("lighting", "auto") == "auto":
        cfg["lighting"] = style["lighting"]
    for key, allowed in (("lighting", LIGHTS), ("grade", GRADES)):
        if cfg[key] not in allowed:
            raise SystemExit(f"未知 {key}: {cfg[key]}，可选: {', '.join(allowed)}")
    if cfg["camera"].get("preset", "orbit") not in CAMERAS:
        raise SystemExit(f"未知运镜 camera.preset: {cfg['camera']['preset']}，可选: {', '.join(CAMERAS)}")
    cfg["_accent"] = cfg.get("accent") or style["accent"]
    sp = float(cfg.get("speed") or 1.0)
    if sp != 1.0:
        cfg["timeline"] = {k: v / sp for k, v in cfg["timeline"].items()}
    # resolve placeholders
    for g in cfg["explode"]["groups"]:
        g["match"] = g["match"].replace("FASTENERS", FASTENER_RE)
    for m in cfg["materials"]:
        m["match"] = m["match"].replace("FASTENERS", FASTENER_RE)
        mat = m["material"]
        if isinstance(mat, dict) and mat.get("color") == "ACCENT":
            mat["color"] = cfg["_accent"]
    t = cfg["timeline"]
    cfg["duration"] = t["intro"] + t["explode"] + t["hold"] + t["assemble"] + t["outro"]
    return cfg
