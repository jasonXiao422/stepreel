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

style: dark-studio             # dark-studio | clean-white | tech-blue
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
  mode: layers                 # layers = 沿一个轴分层拆开；radial = 从中心向四周散开
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
  start_angle: -70             # 环绕起始角度（度）
  end_angle: -5                # 环绕结束角度
  elevation: 28                # 俯视角（度）
  zoom: 1.0                    # >1 拉远，<1 推近
  lens: 40
  dof: true

titles: []                     # 字幕，例：
#  - {text: "产品名", style: title, start: 0.3, end: 2.2, position: bottom-left}
#  - {text: "PRODUCT NAME", style: subtitle, start: 0.5, end: 2.2, position: bottom-left}
#  - {text: "165", style: stat, caption: "个零件", start: 3.4, end: 5.9, position: top-left}
#  - {text: "SolidWorks 建模 · 代码渲染", style: caption, start: 7.0, end: 8.2, position: bottom}
font: auto                     # 或字体文件路径；auto 会找系统中文字体

audio:
  enabled: true
  music: null                  # 背景音乐文件路径；null = 自动合成
  sfx: true                    # 爆炸/合拢音效

render:
  samples: 32                  # 越高越干净越慢
  device: auto                 # auto | gpu | cpu
"""

DEFAULTS = yaml.safe_load(DEFAULT_YAML)

STYLES = {
    "dark-studio": {
        "accent": "#F25213",
        "world": (0.006, 0.007, 0.01), "world_strength": 1.0,
        "floor": {"color": "#020203", "rough": 0.6},
        "lights": [  # (name, direction from target, relative distance, power per d^2, size, color)
            ("key", (-0.6, -0.8, 0.9), 1.0, 15, 0.6, (1, 0.97, 0.93)),
            ("fill", (0.9, -0.4, 0.3), 1.0, 3, 0.8, (0.85, 0.9, 1.0)),
            ("rim_cool", (-0.7, 0.7, 0.3), 1.0, 28, 0.3, (0.35, 0.6, 1.0)),
            ("rim_warm", (0.8, 0.6, 0.4), 1.0, 28, 0.3, (1.0, 0.45, 0.15)),
            ("top", (0.0, 0.0, 1.0), 1.1, 4, 1.2, (1, 1, 1)),
        ],
        "look": "AgX - Medium High Contrast",
        "text": "#FFFFFF", "text_dim": "#C8C8C8",
    },
    "clean-white": {
        "accent": "#2F6BFF",
        "world": (0.85, 0.86, 0.88), "world_strength": 0.6,
        "floor": {"color": "#E9EAEC", "rough": 0.6},
        "lights": [
            ("key", (-0.6, -0.7, 1.0), 1.0, 10, 1.2, (1, 0.98, 0.95)),
            ("fill", (0.9, -0.3, 0.5), 1.0, 5, 1.5, (1, 1, 1)),
            ("rim", (0.0, 0.9, 0.5), 1.0, 10, 0.8, (1, 1, 1)),
        ],
        "look": "AgX - Base Contrast",
        "text": "#16181D", "text_dim": "#4A4F59",
    },
    "tech-blue": {
        "accent": "#00C2FF",
        "world": (0.003, 0.01, 0.025), "world_strength": 1.0,
        "floor": {"color": "#020814", "rough": 0.25},
        "lights": [
            ("key", (-0.6, -0.8, 0.9), 1.0, 10, 0.6, (0.9, 0.95, 1.0)),
            ("rim_cyan", (-0.7, 0.7, 0.3), 1.0, 40, 0.3, (0.0, 0.75, 1.0)),
            ("rim_magenta", (0.8, 0.6, 0.4), 1.0, 30, 0.3, (0.8, 0.2, 1.0)),
            ("top", (0.0, 0.0, 1.0), 1.1, 5, 1.2, (0.7, 0.85, 1.0)),
        ],
        "look": "AgX - High Contrast",
        "text": "#FFFFFF", "text_dim": "#9ED8FF",
    },
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
    cfg = _merge(DEFAULTS, user)
    if cfg["style"] not in STYLES:
        raise SystemExit(f"未知风格 style: {cfg['style']}，可选: {', '.join(STYLES)}")
    style = STYLES[cfg["style"]]
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
