"""Original node-count build-up and recorded benchmark figures, without rerunning them."""

import numpy as np

from examples.shared.intro.drawing import (
    BEAT,
    BG,
    BONE,
    GREY,
    INK,
    MONO,
    ORANGE,
    SERIF,
    N,
    Painter,
    Pen,
    cubic,
    enter,
    noise,
    out,
    prog,
    spring,
)
from examples.shared.intro.effects import grid

REMOTION, GPU, CPU = 121.1321, 4.074223, 69.74039
REMOTION_LABEL, GPU_LABEL = "REMOTION 4.0", "FFRAMES · SKIA ON METAL"
BENCH_NOTE = "M5 MAX · REMOTION 4.0.529 · SERIAL · H.264 MP4 · MEDIANS"


def scale(p: Painter[N]) -> N:
    """Fill the original 3,334-node wall; retain its deliberately larger headline count."""
    lb = p.b
    shrink = cubic(prog(lb, 3, 4))
    size = 1 - 0.72 * shrink
    heading = p.group(
        (
            p.slam(150, 440, "HOW", 330, lb, dx=-260, dy=0),
            p.slam(150, 760, "FAST?", 330, lb - 1, dx=260, dy=0, color=ORANGE),
        ),
        x=(150 - 150 * size) * shrink,
        y=34 * shrink,
        scale=size,
    )
    fill = cubic(prog(lb, 4, 12))
    nodes = []
    shown = np.zeros_like(lb)
    if np.any((lb >= 4) & (lb < 14)):
        labels = ("ff", "fx", "0x", "60", "rs", "gp", "sk", "vk", "mt", "tx")
        for i in range(3334):
            col, row = i % 62, i // 62
            key = col / 62 * 0.7 + row / 54 * 0.3
            visible = key <= fill * 1.02
            shown += visible
            color = noise(i * 1.37 + np.floor(lb * 4))
            fresh = fill * 1.02 - key < 0.03
            colors = tuple(
                ORANGE if new or h > 0.97 else "#b3aca2" if h > 0.55 else "#6b665f"
                for new, h in zip(fresh, color, strict=True)
            )
            word = labels[int(float(noise(float(i))) * len(labels)) % len(labels)]
            nodes.append(
                p.text(
                    150 + col * 1620 / 62,
                    345 + row * 555 / 54,
                    word,
                    13,
                    colors,
                    family=MONO,
                    weight=500,
                    alpha=visible.astype(np.float64),
                )
            )
    count = np.floor(shown / 3334 * 100000 + 0.5).astype(np.int64)
    wall = p.group(
        (
            *nodes,
            p.rect((1010, 130, 760, 140), BG),
            p.text(1770, 232, tuple(f"{n:,}" for n in count), 110, spacing=-3, anchor="end"),
            p.label(1770, 290, "TEXT NODES TO RENDER", ORANGE, 20, "end"),
            p.label(150, 940, "ONE FRAME = 100,000 TEXT NODES  \u00d7  300 FRAMES", size=20),
        ),
        alpha=(lb >= 4) * (1 - enter(prog(lb, 13.6, 14))),
    )
    local = lb - 14
    countdown = p.group(
        (
            p.text(
                960,
                470 + (1 - spring(local)) * 40,
                "REMOTION",
                120,
                GREY,
                spacing=-3,
                anchor="middle",
            ),
            p.text(
                960,
                560,
                "vs",
                70,
                family=SERIF,
                italic=True,
                anchor="middle",
                alpha=prog(local, 0.5, 0.55),
            ),
            p.text(
                960,
                690 + (1 - spring(local - 0.5)) * 40,
                "FFRAMES",
                120,
                ORANGE,
                spacing=-3,
                anchor="middle",
                alpha=prog(local, 0.5, 0.55),
            ),
        ),
        alpha=(local >= 0) * (1 - prog(local, 1.55, 1.6)),
    )
    return p.group((p.group((wall, heading), alpha=(lb < 14).astype(np.float64)), countdown))


def benchmark(p: Painter[N]) -> N:
    """Play the pinned upstream export measurements as a time-lapse."""
    lb = p.b
    return p.group(
        (
            p.group((grid(p, 2, 0.62, 0.35),), alpha=((lb < 16) | (lb >= 22)).astype(np.float64)),
            race(p),
            result(p),
            table(p),
        )
    )


def race(p: Painter[N]) -> N:
    """Show two source timing lanes with their original completion stamps."""
    lb = p.b
    elapsed = prog(lb, 2, 14) * REMOTION
    rows = []
    for i, (name, sub, seconds, color, y) in enumerate(
        (
            (REMOTION_LABEL, "CHROME + REACT → H.264 MP4", REMOTION, GREY, 470),
            (GPU_LABEL, "RUST + SKIA → H.264 MP4", GPU, ORANGE, 700),
        )
    ):
        progress = np.minimum(elapsed / seconds, 1)
        done = progress >= 1
        completion = 2 + 12 * seconds / REMOTION
        flash = np.where(done, np.exp(-np.maximum(lb - completion, 0) * 6), 0)
        width = np.maximum(1620 * progress, 0.5)
        rows.append(
            p.group(
                (
                    p.text(150, y, name, 58, ORANGE if i else BONE, spacing=-2),
                    p.text(150, y + 34, sub, 18, GREY, family=MONO, weight=500, spacing=2.5),
                    p.rect((150, y + 56, 1620, 64), "#141312", pen=Pen("#2f2c29", 1.5)),
                    p.rect((150, y + 56, width, 64), color),
                    p.rect((150, y + 56, 1620, 64), BONE, alpha=flash * 0.6),
                    p.text(
                        1770,
                        y,
                        tuple(f"{s:.3f}s" for s in np.minimum(elapsed, seconds)),
                        52,
                        tuple(color if v else BONE for v in done),
                        family=MONO,
                        weight=600,
                        anchor="end",
                    ),
                    p.text(
                        170,
                        y + 100,
                        tuple(f"{int(np.floor(v * 300))} / 300 FRAMES" for v in progress),
                        22,
                        INK,
                        family=MONO,
                        weight=600,
                        spacing=2,
                        alpha=(width > 260).astype(np.float64),
                    ),
                    p.text(
                        1750,
                        y + 100 + (1 - spring(lb - completion)) * 20,
                        "DONE",
                        24,
                        INK,
                        family=MONO,
                        weight=700,
                        spacing=4,
                        anchor="end",
                        alpha=done.astype(np.float64),
                    ),
                ),
                alpha=prog(lb, 0.6 + i * 0.3, 0.7 + i * 0.3),
                x=(1 - spring(lb - 0.6 - i * 0.3)) * -120,
            )
        )
    return p.group(
        (
            p.slam(150, 250, "100,000 TEXT NODES", 120, lb, dy=140),
            p.label(
                154,
                310,
                "300 FRAMES · 3840\u00d72160 · H.264 MP4 · SAME LAYOUT, SAME FONT",
                size=20,
            ),
            *rows,
            p.label(
                1770,
                310,
                f"TIME-LAPSE \u00d7{REMOTION / (12 * BEAT):.1f} · MEASURED WALL CLOCK",
                ORANGE,
                20,
                "end",
                prog(lb, 2, 2.2),
            ),
        ),
        alpha=(lb < 16) * (1 - enter(prog(lb, 15.6, 16))),
    )


def result(p: Painter[N]) -> N:
    """Animate the measured ratio on the source orange field."""
    local = p.b - 16
    ratio = 1 + (REMOTION / GPU - 1) * out(prog(local, 0, 1.2))
    return p.group(
        (
            p.rect((0, 0, 1920, 1080), ORANGE),
            p.group(
                (p.text(130, 760, tuple(f"{n:.2f}\u00d7" for n in ratio), 480, INK, spacing=-30),),
                scale=1 + (1 - out(local / 0.35)) * 0.15,
                origin=(150, 760),
            ),
            p.text(
                150,
                900 + (1 - spring(local - 1)) * 60,
                "FASTER THAN REMOTION",
                120,
                INK,
                spacing=-4,
                alpha=prog(local, 1, 1.08),
            ),
            p.text(
                150, 170, "SAME 100,000 TEXT NODES", 22, INK, family=MONO, weight=600, spacing=4
            ),
            p.text(
                1770,
                170,
                "COMPLETE MP4 · MEDIAN WALL CLOCK",
                22,
                INK,
                family=MONO,
                weight=600,
                spacing=4,
                anchor="end",
            ),
            p.rect((150, 196, 1620, 3), INK),
        ),
        alpha=(local >= 0) * (local < 6) * (1 - enter(prog(local, 5.7, 6))),
    )


def table(p: Painter[N]) -> N:
    """Keep the three original pipeline measurements and reproduction note together."""
    local = p.b - 22
    rows = []
    for i, (name, seconds, color) in enumerate(
        ((REMOTION_LABEL, REMOTION, GREY), ("FFRAMES · CPU", CPU, BONE), (GPU_LABEL, GPU, ORANGE))
    ):
        at, y = 0.3 + i * 0.5, 520 + i * 130
        rows.append(
            p.group(
                (
                    p.rect((150, y - 70, 1620, 110), "#0f0e0dd9", pen=Pen("#2f2c29", 1.5)),
                    p.rect((150, y - 70, 6, 110), color),
                    p.text(190, y, name, 48, spacing=-1),
                    p.text(
                        1740,
                        y,
                        f"{seconds:.3f} s",
                        48,
                        color,
                        family=MONO,
                        weight=600,
                        anchor="end",
                    ),
                ),
                alpha=prog(local, at, at + 0.08),
                x=(1 - spring(local - at)) * 80,
            )
        )
    return p.group(
        (
            p.slam(150, 300, "THE NUMBERS", 110, local, dy=120),
            p.label(1740, 400, "WALL CLOCK", anchor="end"),
            *rows,
            p.label(154, 860, "RENDER + ENCODE + MP4", BONE),
            p.label(154, 900, BENCH_NOTE),
            p.label(154, 940, "REPRODUCE: RENDER-BENCH/VS-REMOTION IN THE FFRAMES REPO", ORANGE),
        ),
        alpha=(local >= 0) * (1 - enter(prog(local, 9.6, 10))),
    )
