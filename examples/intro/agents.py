"""The original agent loop, terminal cards and breakdown typography."""

import math

import numpy as np

from examples.intro.drawing import (
    BG,
    BONE,
    DIM,
    GREY,
    MONO,
    ORANGE,
    SERIF,
    N,
    Painter,
    Pen,
    Pixels,
    cubic,
    enter,
    prog,
    spring,
    typed,
)
from examples.intro.effects import contour
from examples.intro.opening import PROMPT

CARD_BEATS = (175, 179, 183, 187, 191, 195)
NODES = ("WRITE", "TIMELINE", "INSPECT", "STRIP", "FRAME", "RENDER")
CARD_NODES = (1, 2, 3, 4, 0, 5)
COMMANDS = (
    "cargo run -- timeline",
    "cargo run -- inspect",
    "cargo run -- strip all -n 30",
    "cargo run -- frame Shader@2.7s",
    "cargo run -- audio analyze",
    "cargo run -- render --draft",
)
LINES = (
    (
        ("1920x1080 @ 60 fps, 7650 frames (127.50s)", BONE),
        ("#0   PromptScene      0.00s..2.15s", GREY),
        ("#1   OriginScene      2.15s..16.70s", GREY),
        ("#2   CodeScene       16.70s..23.97s", GREY),
        ("#3   GpuScene        23.97s..27.60s", GREY),
        ("audio music.wav       0.000s..127.500s", ORANGE),
    ),
    (
        ("checked 540 frames: 13 findings", BONE),
        ("0 errors · 13 warnings: marquee rows and", GREY),
        ("type that overflows the canvas on purpose", GREY),
    ),
    (),
    (),
    (
        ("integrated -14.1 LUFS, range 10.3 LU", BONE),
        ("true peak -1.2 dBTP, clipped samples 0", BONE),
        ("GpuScene        23.97s..27.60s   -13.0 LUFS", GREY),
        ("BenchmarkScene  45.78s..60.33s   -13.0 LUFS", GREY),
    ),
    (("out.mp4 frames 0..7650 (0.00s..127.50s)", GREY), ("960x540 in 5.3s", ORANGE)),
)


def agents(p: Painter[N]) -> N:
    """Reveal the six workflow steps, then the source's closing confession."""
    lb = p.b
    cards = []
    active = np.full_like(lb, -1, dtype=np.int64)
    for i, beat in enumerate(CARD_BEATS):
        start = beat - 160
        end = CARD_BEATS[i + 1] - 160 if i + 1 < len(CARD_BEATS) else 40
        selected = (lb >= start) & (lb < end)
        active = np.where(selected, CARD_NODES[i], active)
        cards.append(p.group((card(p, i, lb - start),), alpha=selected.astype(np.float64)))
    body = p.group(
        (
            p.text(
                150,
                235 + (1 - spring(lb)) * 60,
                "BUILT FOR THE",
                110,
                spacing=-4,
                alpha=prog(lb, 0, 0.1),
            ),
            p.text(
                150,
                345 + (1 - spring(lb - 1.5)) * 60,
                "AGENTIC LOOP.",
                110,
                ORANGE,
                spacing=-4,
                alpha=prog(lb, 1.5, 1.6),
            ),
            ring(p, active.astype(np.float64)),
            p.group((prompt_card(p),), alpha=(lb < 15).astype(np.float64)),
            *cards,
        ),
        alpha=(lb < 40) * (1 - enter(prog(lb, 39.6, 40))),
    )
    local = lb - 40
    collapse = enter(prog(local, 7.3, 8))
    confession = p.group(
        (
            p.slam(150, 470, "THIS VIDEO WAS", 138, local, dy=160),
            p.slam(150, 630, "MADE BY AN AGENT.", 138, local - 1, dy=160, color=ORANGE),
            p.text(
                156,
                712,
                "in Rust, with fframes. No timeline editor was opened.",
                54,
                family=SERIF,
                italic=True,
                alpha=prog(local, 3, 3.4),
            ),
        ),
        alpha=(local >= 0) * (1 - collapse),
        scale=1 - collapse * 0.15,
        origin=(960, 540),
    )
    return p.group(
        (contour(p, (1370 / 1920, 590 / 1080), 0.9, 20, 0.3 * prog(lb, 0, 2)), body, confession)
    )


def ring(p: Painter[N], active: Pixels) -> N:
    """Draw the ring, highlighted nodes and the ten-point orbiting comet."""
    lb = p.b
    draw = cubic(prog(lb, 2, 5))
    items = [
        p.group(
            (
                p.circle(
                    1370,
                    590,
                    250,
                    None,
                    pen=Pen(GREY, 1.5, (math.tau * 250 * draw, math.tau * 250)),
                ),
            ),
            rotation=-90,
            origin=(1370, 590),
        ),
        p.circle(1370, 590, 220, None, pen=Pen(DIM, 1, (4, 8)), alpha=draw),
    ]
    for k in range(10):
        angle = -math.pi / 2 + ((lb - 5) / 8 - k * 0.008) * math.tau
        items.append(
            p.circle(
                1370 + np.cos(angle) * 250,
                590 + np.sin(angle) * 250,
                7 - k * 0.5,
                ORANGE,
                alpha=(lb > 5).astype(np.float64) * (1 - k / 10),
            )
        )
    for i, name in enumerate(NODES):
        node_angle = -math.pi / 2 + i / 6 * math.tau
        cosine, sine = math.cos(node_angle), math.sin(node_angle)
        x, y = 1370 + cosine * 250, 590 + sine * 250
        at = 2.5 + i * 0.4
        hot = active == i
        size = np.where(hot, 26, 18)
        colors = tuple(ORANGE if on else BONE for on in hot)
        items.append(
            p.group(
                (
                    p.rect(
                        (
                            x - size / 2,
                            y - size / 2,
                            size * np.maximum(spring(lb - at), 0.05),
                            size * np.maximum(spring(lb - at), 0.05),
                        ),
                        tuple(ORANGE if on else BG for on in hot),
                        pen=Pen(colors, 2),
                    ),
                    p.text(
                        1370 + cosine * 294,
                        590 + sine * 294 + 8,
                        name,
                        22,
                        colors,
                        family=MONO,
                        weight=600,
                        spacing=3,
                        anchor="start" if cosine > 0.3 else "end" if cosine < -0.3 else "middle",
                    ),
                ),
                alpha=prog(lb, at, at + 0.1),
            )
        )
    items.append(
        p.group(
            (
                p.text(1370, 584, "the agent", 64, family=SERIF, italic=True, anchor="middle"),
                p.text(
                    1370,
                    626,
                    "NEVER WATCHES A VIDEO",
                    18,
                    GREY,
                    family=MONO,
                    weight=500,
                    spacing=3,
                    anchor="middle",
                ),
            ),
            alpha=prog(lb, 4, 4.5),
        )
    )
    return p.group(tuple(items))


def card(p: Painter[N], index: int, local: Pixels) -> N:
    """Show a typed command and the recorded lines or screenshot it produced."""
    command = COMMANDS[index]
    rows = []
    if index in (2, 3):
        name, aspect = ("strip", 1.887) if index == 2 else ("frame", 1.778)
        height = 84 + 744 / aspect + 28
        rows.append(
            p.group(
                (p.image(p.assets[f"intro_{name}_self_jpg"], (178, 524, 744, 744 / aspect)),),
                alpha=prog(local, 0.45, 0.6),
            )
        )
    else:
        lines = LINES[index]
        height = 110 + len(lines) * 36
        rows.extend(
            p.text(
                178,
                550 + i * 36,
                text,
                23,
                color,
                family=MONO,
                weight=500,
                alpha=prog(local, 0.5 + i * 0.08, 0.55 + i * 0.08),
            )
            for i, (text, color) in enumerate(lines)
        )
    return p.group(
        (
            p.rect((150, 440, 800, height), "#0e0d0ceb", pen=Pen("#3d3a35", 1.5)),
            p.rect((150, 440, 4, height), ORANGE),
            p.text(178, 492, "$", 25, ORANGE, family=MONO, weight=600),
            p.text(
                208,
                492,
                typed(command, np.minimum(local / 0.5 * len(command), len(command))),
                25,
                family=MONO,
                weight=500,
            ),
            p.rect((178, 510, 744, 1), "#3d3a35"),
            *rows,
        ),
        alpha=prog(local, 0, 0.08),
        x=(1 - spring(local)) * -80,
    )


def prompt_card(p: Painter[N]) -> N:
    """Recall the opening prompt before the first command card appears."""
    local = p.b - 6
    shown = typed(PROMPT, np.minimum(local / 3 * len(PROMPT), len(PROMPT)))
    return p.group(
        (
            p.text(
                150, 480, "IT STARTS WITH A PROMPT", 20, GREY, family=MONO, weight=500, spacing=3
            ),
            p.rect((150, 510, 800, 150), "#0e0d0ceb", pen=Pen(ORANGE, 2)),
            p.text(180, 572, "\u203a", 32, ORANGE, family=MONO, weight=600),
            p.text(220, 572, tuple(s[:33] for s in shown), 32, family=MONO, weight=500),
            p.text(220, 620, tuple(s[33:] for s in shown), 32, family=MONO, weight=500),
        ),
        alpha=prog(local, 0, 0.1),
        x=(1 - spring(local)) * -80,
    )
