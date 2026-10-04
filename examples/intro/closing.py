"""Flying frames, feature recap, install prompt and original wordmark finale."""

import numpy as np

from examples.intro.drawing import (
    BEAT,
    BG,
    BONE,
    DISPLAY,
    EMBER,
    GREY,
    INK,
    MONO,
    ORANGE,
    PAPER,
    SERIF,
    N,
    Painter,
    Pen,
    enter,
    noise,
    out,
    prog,
    pulse,
    spring,
    typed,
)
from examples.intro.effects import contour, grid
from examples.intro.opening import RELEASE

RENDER_SECONDS = 79.6


def render(p: Painter[N]) -> N:
    """Fly the original ten thumbnails toward the camera, sorting their changing depths."""
    lb = p.b
    cards, depths = [], []
    for k in range(14):
        phase = np.mod(lb * BEAT * 0.45 + k / 14, 1)
        z = 7 + (0.35 - 7) * phase
        side = -1 if k % 2 == 0 else 1
        x = 960 + side * (620 + float(noise(k * 3.1)) * 520) / z
        y = 540 + (-330 + float(noise(k * 7.7)) * 300) / z
        w, h = 520 / z, 520 / z * 9 / 16
        opacity = prog(phase, 0, 0.2) * (1 - prog(phase, 0.85, 1)) * prog(lb, 0, 0.3)
        cards.append(
            p.group(
                (
                    p.image(p.assets[f"intro_fly_{k % 10}_jpg"], (x - w / 2, y - h / 2, w, h)),
                    p.rect((x - w / 2, y - h / 2, w, h), None, pen=Pen("#ece8e159", 1)),
                ),
                alpha=opacity,
            )
        )
        depths.append(-z)
    title_width = p.measure("THIS VIDEO.", DISPLAY, 120) - 44
    count = np.floor(7650 * out(prog(lb, 0, 3)) + 0.5).astype(np.int64)
    seconds = RENDER_SECONDS * out(prog(lb, 4, 6))
    return p.group(
        (
            grid(p, 6, 0.5, 0.9 + pulse(lb, 6) * 0.4),
            p.ordered(tuple(cards), tuple(depths)),
            p.fade(),
            p.group(
                (
                    p.rect((120, 120, title_width + 60, 150), ORANGE),
                    p.text(150, 232, "THIS VIDEO.", 120, INK, spacing=-4),
                ),
                x=(1 - spring(lb - 0.5)) * -200,
                alpha=prog(lb, 0.5, 0.6),
            ),
            p.group(
                (
                    p.text(150, 820, tuple(f"{n:,}" for n in count), 190, spacing=-8),
                    p.text(
                        160,
                        880,
                        "FRAMES · 1920\u00d71080 · 60 FPS",
                        30,
                        family=MONO,
                        weight=600,
                        spacing=6,
                    ),
                ),
                y=(1 - spring(lb)) * 70,
                alpha=prog(lb, 0, 0.08),
            ),
            p.group(
                (
                    p.text(
                        1770,
                        820,
                        tuple(f"{s:.1f}s" for s in seconds),
                        190,
                        ORANGE,
                        spacing=-8,
                        anchor="end",
                    ),
                    p.text(
                        1770,
                        880,
                        "TO RENDER · SKIA ON METAL",
                        30,
                        family=MONO,
                        weight=600,
                        spacing=6,
                        anchor="end",
                    ),
                ),
                y=(1 - spring(lb - 4)) * 70,
                alpha=prog(lb, 4, 4.08),
            ),
            p.group(
                (
                    p.rect((1330, 170, 440, 64), ORANGE),
                    p.text(
                        1550,
                        214,
                        f"{127.5 / RENDER_SECONDS:.1f}\u00d7 REAL TIME",
                        30,
                        INK,
                        family=MONO,
                        weight=700,
                        spacing=3,
                        anchor="middle",
                    ),
                ),
                alpha=prog(lb, 8, 8.3),
            ),
        ),
        alpha=1 - enter(prog(lb, 15.7, 16)),
    )


def recap(p: Painter[N]) -> N:
    """Land one feature per beat, preserving the source alternating backgrounds."""
    lb = p.b
    names = ("TEXT", "IMAGES", "VIDEO", "SHADERS", "AUDIO", "GPU", "EFFECTS", "AGENTS")
    index = np.floor(np.maximum(lb, 0)).astype(np.int64)
    local = lb - index
    palette = ((ORANGE, INK), (BG, BONE), (PAPER, INK))
    background = tuple(palette[int(i) % 3][0] for i in index)
    foreground = tuple(palette[int(i) % 3][1] for i in index)
    feature = p.group(
        (
            p.rect((0, 0, 1920, 1080), background),
            p.group(
                (
                    p.text(
                        960,
                        690,
                        tuple(names[min(int(i), 7)] for i in index),
                        360,
                        foreground,
                        spacing=-16,
                        anchor="middle",
                    ),
                ),
                scale=1 + (1 - out(local / 0.4)) * 0.12,
                origin=(960, 560),
            ),
            p.text(
                150,
                200,
                tuple(f"{i + 1:02}" for i in index),
                30,
                foreground,
                family=MONO,
                weight=600,
                spacing=6,
            ),
            p.text(
                1770, 200, "/ 08", 30, foreground, family=MONO, weight=600, spacing=6, anchor="end"
            ),
        ),
        alpha=(index < 8).astype(np.float64),
    )
    local = lb - 8
    return p.group(
        (
            feature,
            p.group(
                (
                    p.rect((0, 0, 1920, 1080), BG),
                    p.slam(960, 520, "ALL OF IT.", 220, local, dy=170, anchor="middle"),
                    p.slam(
                        960,
                        760,
                        "in Rust.",
                        220,
                        local - 2,
                        dy=170,
                        color=ORANGE,
                        family=SERIF,
                        anchor="middle",
                        italic=True,
                    ),
                ),
                alpha=(local >= 0) * (1 - enter(prog(local, 3.7, 4))),
            ),
        )
    )


def done(p: Painter[N]) -> N:
    """Type the original cargo command during the silent bar."""
    command = "cargo fframes new my-video"
    counts = np.floor(prog(p.b, 0.2, 3.2) * len(command))
    x = 960 - (len(command) + 2) * 24 / 2
    caret = (counts < len(command)) | ((counts >= len(command)) & (np.mod(p.b * 2, 1) > 0.5))
    return p.group(
        (
            p.rect((0, 0, 1920, 1080), "#050505"),
            p.text(x, 555, "$", 40, ORANGE, family=MONO, weight=600),
            p.text(x + 48, 555, typed(command, counts), 40, family=MONO, weight=500),
            p.rect(
                (x + (2 + counts) * 24 + 2, 522, 20, 44), ORANGE, alpha=caret.astype(np.float64)
            ),
        )
    )


def outro(p: Painter[N]) -> N:
    """Animate the source serif wordmark, three echoes, commands and fade to black."""
    lb = p.b
    fade = prog(p.seconds, 125.9, 127.5)
    width = p.measure("fframes", SERIF, 300, italic=True)
    step = p.measure("f", SERIF, 300, italic=True) * 0.78
    x0 = 960 - (width + step * 3) / 2 + step * 3
    echoes = []
    for k, color in reversed(tuple(enumerate((ORANGE, "#c4531c", EMBER)))):
        motion = spring(lb - 0.5 - k * 0.5, 170, 15)
        echoes.append(
            p.text(
                x0 - step * (k + 1) * motion,
                520,
                "f",
                300,
                color,
                family=SERIF,
                italic=True,
                alpha=np.clip(motion, 0, 1) * (1 - k * 0.18),
            )
        )
    commands = []
    for i, (command, note) in enumerate(
        (
            ("npx skills add https://fframes.studio", "WITH YOUR CODING AGENT"),
            ("cargo fframes new my-video", "OR BY HAND"),
        )
    ):
        at, y = 8 + i, 760 + i * 78
        commands.append(
            p.group(
                (
                    p.rect((400, y - 44, 1120, 62), "#0f0e0de6", pen=Pen("#3d3a35", 1.5)),
                    p.text(428, y, "$", 26, ORANGE, family=MONO, weight=600),
                    p.text(458, y, command, 26, family=MONO, weight=500),
                    p.text(
                        1500, y, note, 15, GREY, family=MONO, weight=500, spacing=2, anchor="end"
                    ),
                ),
                alpha=prog(lb, at, at + 0.1),
                y=(1 - spring(lb - at)) * 30,
            )
        )
    tag = prog(lb, 4, 4.6)
    return p.group(
        (
            contour(p, (0.5, 0.47), 1.1, 18, 0.25 + 0.5 * (1 - out(prog(lb, 0, 6)))),
            p.group(
                (
                    *echoes,
                    p.group(
                        (p.text(x0, 520, "fframes", 300, family=SERIF, italic=True),),
                        scale=1 + (1 - out(lb / 0.5)) * 0.25,
                        origin=(960, 520),
                        alpha=np.minimum(spring(lb, 260, 20), 1),
                    ),
                    p.text(
                        1470,
                        265,
                        RELEASE,
                        28,
                        GREY,
                        family=MONO,
                        weight=500,
                        spacing=2,
                        anchor="end",
                        alpha=tag,
                    ),
                    p.text(
                        960,
                        590,
                        "video vibe coding framework that is actually fast",
                        30,
                        family=MONO,
                        weight=500,
                        spacing=2,
                        anchor="middle",
                        alpha=tag,
                    ),
                    *commands,
                    p.text(
                        960,
                        990,
                        "GITHUB.COM/DMTRKOVALENKO/FFRAMES",
                        26,
                        ORANGE,
                        family=MONO,
                        weight=600,
                        spacing=3,
                        anchor="middle",
                        alpha=prog(lb, 12, 12.5),
                    ),
                ),
                alpha=1 - fade,
            ),
            p.rect((0, 0, 1920, 1080), BONE, alpha=np.exp(-lb * 9)),
            p.rect((0, 0, 1920, 1080), "#000000", alpha=fade),
        )
    )
