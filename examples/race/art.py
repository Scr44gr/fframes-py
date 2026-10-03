"""Small SVG drawing primitives and a deterministic crumpled-paper texture."""

from html import escape
from math import cos, pi, sin
from pathlib import Path

INK = "#212345"
WHITE = "#fff9e8"
BLUE = "#348dcb"
YELLOW = "#ffdc59"
CORAL = "#fb674c"


def noise(seed: float) -> float:
    """Return a reproducible unit value for decorative placement."""
    value = sin(seed * 127.1 + 311.7) * 43758.5453
    return value % 1


def smooth(value: float) -> float:
    """Clamp and ease a transition without overshoot."""
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


def group(content: str, transform: str = "", opacity: float = 1.0) -> str:
    """Wrap artwork in a transformed SVG group."""
    return f'<g transform="{transform}" opacity="{opacity:.4f}">{content}</g>'


def path(data: str, fill: str, *, stroke: str = INK, width: float = 4, cut: bool = False) -> str:
    """Draw a path with an optional white paper-cut border."""
    attrs = f'd="{data}" stroke-linejoin="round" stroke-linecap="round"'
    border = f'<path {attrs} fill="{fill}" stroke="{WHITE}" stroke-width="{width + 10}"/>'
    ink = f'<path {attrs} fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
    return (border if cut else "") + ink


def ellipse(
    x: float, y: float, rx: float, ry: float, fill: str, *, stroke: str = "none", width: float = 3
) -> str:
    """Draw an ellipse in scene coordinates."""
    return (
        f'<ellipse cx="{x:.2f}" cy="{y:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
    )


def text(
    words: str, x: float, y: float, size: float, fill: str = WHITE, *, outline: bool = False
) -> str:
    """Draw centered rounded lettering, optionally with a dark outline."""
    attrs = (
        f'x="{x}" y="{y}" text-anchor="middle" font-family="Arial Rounded MT Bold,DejaVu Sans" '
        f'font-weight="bold" font-size="{size}"'
    )
    content = escape(words)
    border = f'<text {attrs} fill="{fill}" stroke="{INK}" stroke-width="9">{content}</text>'
    return (border if outline else "") + f'<text {attrs} fill="{fill}">{content}</text>'


def tag(words: str, x: float, y: float, color: str, size: float = 24) -> str:
    """Draw a small cut-paper name label."""
    half = len(words) * size * 0.34 + 20
    return group(
        path(f"M {-half} -34 L {half} -38 L {half + 5} 10 L {-half - 5} 14 Z", color, cut=True)
        + text(words, 0, 0, size, INK),
        f"translate({x:.2f} {y:.2f}) rotate(-2)",
    )


def star(x: float, y: float, radius: float, color: str, rotation: float = 0) -> str:
    """Draw a five-pointed paper star."""
    points = [
        (
            cos(i * pi / 5 - pi / 2) * radius * (1 if i % 2 == 0 else 0.43),
            sin(i * pi / 5 - pi / 2) * radius * (1 if i % 2 == 0 else 0.43),
        )
        for i in range(10)
    ]
    data = "M " + " L ".join(f"{a:.2f} {b:.2f}" for a, b in points) + " Z"
    return group(path(data, color, stroke=WHITE, width=2), f"translate({x} {y}) rotate({rotation})")


def paper_texture(destination: Path) -> str:
    """Synthesize lit folds and fibers as vectors, avoiding bitmap image resolvers."""
    folds: list[str] = []
    for i in range(27):
        x = noise(i + 20) * 1480 - 100
        y = noise(i + 250) * 920 - 100
        dx = cos(i * 2.31) * (240 + noise(i + 53) * 450)
        dy = sin(i * 2.31) * (170 + noise(i + 53) * 320)
        data = (
            f"M {x:.2f} {y:.2f} L {x + dx * 0.46:.2f} {y + dy * 0.44:.2f} "
            f"L {x + dx:.2f} {y + dy:.2f}"
        )
        folds.extend(
            group(path(data, "none", stroke=INK, width=width), opacity=opacity)
            for width, opacity in ((24, 0.014), (11, 0.022), (4, 0.032), (1.2, 0.04))
        )
        folds.append(group(path(data, "none", stroke=WHITE, width=3), "translate(2 -2)", 0.14))
        facet = (
            f"M {x:.2f} {y:.2f} L {x + dx:.2f} {y + dy:.2f} "
            f"L {x + dx * 0.6 - dy * 0.24:.2f} {y + dy * 0.5 + dx * 0.15:.2f} Z"
        )
        folds.append(group(path(facet, WHITE if i % 2 else INK, width=0), opacity=0.025))
    fibers = (
        ellipse(
            noise(i + 183) * 1280,
            noise(i + 829) * 720,
            0.25 + noise(i) * 0.65,
            0.2,
            WHITE if i % 2 else INK,
        )
        for i in range(1500)
    )
    result = group("".join(folds)) + group("".join(fibers), opacity=0.10)
    destination.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">' + result + "</svg>",
        encoding="utf-8",
    )
    return result


def sticker(content: str, transform: str) -> str:
    """Lift a character slightly off the paper background with a soft shadow."""
    return group(f'<g filter="url(#shadow)">{content}</g>', transform)


def definitions() -> str:
    """Return the shared palette, paper shadows and atmosphere gradients."""
    return f"""<defs>
      <linearGradient id="sky" x2="0" y2="1"><stop stop-color="#71dce2"/>
        <stop offset="1" stop-color="#fff0bd"/></linearGradient>
      <radialGradient id="sea" cx=".32" cy=".26" r=".8">
        <stop stop-color="#8cf4eb"/><stop offset=".45" stop-color="#34a9d7"/>
        <stop offset="1" stop-color="#284285"/></radialGradient>
      <radialGradient id="atmosphere"><stop offset=".76" stop-color="#49defb" stop-opacity="0"/>
        <stop offset=".87" stop-color="#7cf5fc" stop-opacity=".6"/>
        <stop offset="1" stop-color="#4ea6ff" stop-opacity="0"/></radialGradient>
      <linearGradient id="shade"><stop offset=".4" stop-color="#13193a" stop-opacity="0"/>
        <stop offset="1" stop-color="#13193a" stop-opacity=".72"/></linearGradient>
      <linearGradient id="shell" x2="0" y2="1"><stop stop-color="#ff9d58"/>
        <stop offset="1" stop-color="{CORAL}"/></linearGradient>
      <filter id="shadow" x="-.3" y="-.3" width="1.6" height="1.7">
        <feGaussianBlur in="SourceAlpha" stdDeviation="3"/><feOffset dx="3" dy="7"/>
        <feComponentTransfer><feFuncA type="linear" slope=".22"/></feComponentTransfer>
        <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <clipPath id="globe"><circle r="215"/></clipPath>
    </defs>"""
