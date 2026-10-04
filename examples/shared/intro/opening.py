"""Cold open, repository history and the source-code reveal."""

from datetime import date

import numpy as np

from examples.shared.intro.drawing import (
    BEAT,
    BG,
    BONE,
    DISPLAY,
    DOWNBEAT,
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
    typed,
)
from examples.shared.intro.effects import contour

PROMPT = "make an intro video for fframes. make it stunning."
RELEASE = "v1.2.0"
LINES_OF_RUST = 89_372


def prompt(p: Painter[N]) -> N:
    """Type the original prompt, then reveal its recorded agent output."""
    t = p.seconds
    after = t - (DOWNBEAT - BEAT)
    flash = np.where(after > 0, np.exp(-np.maximum(after, 0) * 9), 0)
    counts = np.minimum(np.maximum(8 + (t - 0.02) * 44, 0).astype(np.int64), len(PROMPT))
    shown = typed(PROMPT, counts.astype(np.float64))
    split = PROMPT.index(". ") + 2
    first = tuple(s[:split] for s in shown)
    second = tuple(s[split:] for s in shown)
    cx = 240 + np.where(counts <= split, counts, counts - split) * 38.4 + 4
    cy = np.where(counts <= split, 522, 612) - 50
    cursor = ((counts < len(PROMPT)) | (np.mod(t * 3, 1) < 0.55)) & (after <= 0)
    output = (
        (True, "Explored skills/fframes-video"),
        (False, "Read SKILL.md, design.md, audio.md"),
        (True, "Edited src/lib.rs"),
        (True, "Ran cargo run --release -- timeline"),
        (True, "Ran cargo run --release -- strip all -n 24"),
    )
    lines = []
    for i, (done, text) in enumerate(output):
        y = 560 + i * 44
        mark = (
            p.circle(172, y - 9, 7, ORANGE)
            if done
            else p.path(f"M204 {y - 26}V{y - 9}H222", Pen(GREY, 2))
        )
        lines.append(
            p.group(
                (mark, p.text(200 if done else 236, y, text, 28, "#b9b4ab", family=MONO)),
                alpha=prog(after, 0.05 + i * 0.07, 0.11 + i * 0.07),
            )
        )
    panel = p.group(
        (
            p.text(
                160, 366, "CODEX  ·  ~/dev/fframes", 22, GREY, family=MONO, weight=500, spacing=2
            ),
            p.text(1760, 366, RELEASE, 28, GREY, family=MONO, weight=500, spacing=2, anchor="end"),
            p.rect(
                (140, 400, 1640, 270),
                "#0f0e0dd9",
                radius=18,
                pen=Pen(tuple(ORANGE if a > 0 else "#4a4640" for a in after), 2),
            ),
            p.text(180, 522, "\u203a", 64, ORANGE, family=MONO, weight=600),
            p.text(240, 522, first, 64, family=MONO, weight=500),
            p.text(240, 612, second, 64, ORANGE, family=MONO, weight=500),
            p.rect((cx, cy, 32, 64), ORANGE, alpha=cursor.astype(np.float64)),
        ),
        y=-out(prog(after, 0, 0.25)) * 200,
    )
    return p.group(
        (contour(p, (0.74, 0.62), 0.6, 16, 0.35 + flash * 0.4), panel, p.group(tuple(lines), y=-40))
    )


def origin(p: Painter[N]) -> N:
    """Derive history and typography from the pinned repository, not this wrapper."""
    commits = tuple(
        tuple(line.split("|", 2))
        for line in p.assets["intro_history"].read_text(encoding="utf-8").splitlines()
    )
    first, last = commits[0], commits[-1]
    days = (date.fromisoformat(last[1]) - date.fromisoformat(first[1])).days
    lb = p.b
    year = first[1][:4]
    glyphs = []
    for i, char in enumerate(year):
        prefix = p.measure(year[:i], DISPLAY, 440) - 8 * i if i else 0
        width = p.measure(char, DISPLAY, 440)
        s = 0.85 + 0.15 * spring(lb - i)
        glyphs.append(
            p.group(
                (p.text(0, 0, char, 440),),
                x=150 + prefix + width / 2 - width * s / 2,
                y=690 + (1 - spring(lb - i)) * 160,
                scale=s,
                alpha=prog(lb, i, i + 0.15),
            )
        )
    meta = prog(lb, 4, 4.4)
    title = p.group(
        (
            p.rect((1290, 800, 470, 150), "#0b0b0bb3", pen=Pen(GREY, 1.5)),
            p.path("M1290 850H1760 M1290 900H1760 M1400 800V950 M1600 850V950", Pen(GREY, 1.5)),
            *(
                p.text(x, y, text, 18, color, family=MONO, spacing=1.5)
                for x, y, text, color in (
                    (1306, 832, "TITLE", GREY),
                    (1416, 832, "FFRAMES — PROOF OF CONCEPT", BONE),
                    (1306, 882, "DRAWN", GREY),
                    (1416, 882, "dmtrKovalenko", BONE),
                    (1616, 882, "REV 1", GREY),
                    (1306, 932, "SHEET", GREY),
                    (1416, 932, f"1 OF {len(commits)}", BONE),
                    (1616, 932, first[1], ORANGE),
                )
            ),
        ),
        alpha=prog(lb, 6, 6.4),
    )
    first_exit = enter(prog(lb, 7.6, 8))
    first_commit = p.group(
        (
            p.text(
                160,
                220,
                typed("$ git log --reverse | head -1", lb / 0.8 * 28),
                30,
                GREY,
                family=MONO,
                weight=500,
            ),
            *glyphs,
            p.rect((160, 740, np.maximum((1 - (1 - prog(lb, 3, 4)) ** 4) * 1120, 0.5), 10), ORANGE),
            p.text(160, 826, first[0], 36, ORANGE, family=MONO, weight=600, alpha=meta),
            p.text(
                160 + 7 * 36 * 0.6 + 30,
                826,
                first[1] + "   Dmitriy Kovalenko",
                36,
                family=MONO,
                weight=500,
                alpha=meta,
            ),
            p.text(1030, 832, f"“{first[2]}”", 64, ORANGE, family=SERIF, italic=True, alpha=meta),
            p.callout(
                (160 + 7 * 36 * 0.6 / 2, 842),
                (160 + 7 * 36 * 0.6 / 2, 980),
                "FIRST COMMIT",
                prog(lb, 5, 5.8),
            ),
            p.callout(
                (1270, 520), (1420, 360), f"{days // 365} YEARS AGO", prog(lb, 5.5, 6.3), BONE
            ),
            title,
        ),
        alpha=(1 - first_exit) * (lb < 8),
        y=-first_exit * 120,
    )
    return p.group(
        (
            contour(p, (0.7 - prog(lb, 0, 32) * 0.25, 0.58), 0.8, 18, 0.42),
            first_commit,
            history(p, commits),
            stats(p, commits, days),
        )
    )


def history(p: Painter[N], commits: tuple[tuple[str, ...], ...]) -> N:
    """Scroll 24 neighboring commits while keeping the center row highlighted."""
    lb = p.b - 8
    position = cubic(prog(lb, 0.3, 7.4)) * (len(commits) - 1)
    current = np.floor(position + 0.5).astype(np.int64)
    first = np.floor(position).astype(np.int64) - 11
    rows = []
    for offset in range(24):
        indices = first + offset
        valid = (indices >= 0) & (indices < len(commits))
        records = tuple(commits[int(i)] for i in np.clip(indices, 0, len(commits) - 1))
        y = 560 + (indices - position) * 44
        opacity = np.maximum(1 - np.abs((y - 560) / 480), 0) ** 1.5 * valid
        hot = indices == current
        rows.append(
            p.group(
                (
                    p.text(
                        160,
                        y,
                        tuple(c[0] for c in records),
                        26,
                        tuple(ORANGE if v else "#6d4a36" for v in hot),
                        family=MONO,
                        weight=600,
                    ),
                    p.text(310, y, tuple(c[1] for c in records), 26, GREY, family=MONO, weight=500),
                    p.text(
                        510,
                        y,
                        tuple("".join(ch for ch in c[2] if ch.isascii())[:48] for c in records),
                        26,
                        tuple(BONE if v else "#8f8a82" for v in hot),
                        family=MONO,
                        weight=500,
                    ),
                ),
                alpha=opacity,
            )
        )
    records = tuple(commits[int(i)] for i in current)
    appear, leave = out(prog(lb, 0, 0.5)), enter(prog(lb, 7.6, 8))
    return p.group(
        (
            p.rect((140, 526, 1060, 48), ORANGE, alpha=0.12),
            p.rect((140, 526, 4, 48), ORANGE),
            *rows,
            p.text(
                1770, 600, tuple(c[1][:4] for c in records), 300, ORANGE, spacing=-10, anchor="end"
            ),
            p.text(
                1770,
                680,
                tuple(f"#{i + 1:03} / {len(commits)}" for i in current),
                36,
                family=MONO,
                weight=500,
                anchor="end",
            ),
            p.text(
                1770,
                730,
                tuple(c[1] for c in records),
                26,
                GREY,
                family=MONO,
                weight=500,
                anchor="end",
            ),
        ),
        alpha=appear * (1 - leave) * ((lb >= 0) & (lb < 8)),
        y=(1 - appear) * 80 - leave * 80,
    )


def stats(p: Painter[N], commits: tuple[tuple[str, ...], ...], days: int) -> N:
    """Animate the four source history statements."""
    since = date.fromisoformat(commits[0][1]).strftime("%b %Y").upper()
    until = date.fromisoformat(commits[-1][1]).strftime("%b %Y").upper()
    numbers = (
        (days // 365, "YEARS", f"{since} → {until}  ·  {days:,} DAYS"),
        (len(commits), "COMMITS", "FROM THE FIRST “POC” TO TODAY"),
        (LINES_OF_RUST, "LINES OF RUST", "FFMPEG · SVG · SKIA · EDITOR · CLI"),
    )
    results = []
    for i, (number, unit, caption) in enumerate(numbers):
        local = p.b - 16 - i * 4
        number_width = p.measure(f"{number:,}", DISPLAY, 400) - 10 * len(f"{number:,}")
        unit_width = p.measure(unit, DISPLAY, 110) - 3 * len(unit)
        next_to = 150 + number_width + 40 + unit_width < 1770
        ux, uy, cy = (number_width + 40, 0, 0) if next_to else (8, 130, 130)
        appear, leave = out(prog(local, 0, 0.7)), enter(prog(local, 3.65, 4))
        unit_in, cap = spring(local - 0.5), prog(local, 1, 1.4)
        shown = np.floor(number * out(prog(local, 0, 1.3)) + 0.5).astype(np.int64)
        results.append(
            p.group(
                (
                    p.text(0, 640, tuple(f"{n:,}" for n in shown), 400, spacing=-10),
                    p.text(
                        ux,
                        640 + uy + (1 - unit_in) * 60,
                        unit,
                        110,
                        ORANGE,
                        spacing=-3,
                        alpha=np.minimum(unit_in, 1),
                    ),
                    p.rect((4, 700 + cy, np.maximum(cap * 60, 0.5), 4), ORANGE),
                    p.text(4, 760 + cy, caption, 30, family=MONO, weight=500, spacing=3, alpha=cap),
                ),
                x=150 + (1 - appear) * 260 - leave * 300,
                alpha=(1 - leave) * ((local >= 0) & (local < 4)),
            )
        )
    local = p.b - 28
    results.append(
        p.group(
            (
                p.text(
                    160,
                    330,
                    "ONE IDEA",
                    34,
                    ORANGE,
                    family=MONO,
                    weight=600,
                    spacing=6,
                    alpha=np.minimum(spring(local), 1),
                ),
                p.slam(150, 620, "video =", 190, local - 1),
                p.slam(
                    905,
                    628,
                    "f(frame)",
                    270,
                    local - 2,
                    dx=260,
                    dy=0,
                    color=ORANGE,
                    family=SERIF,
                    italic=True,
                ),
            ),
            alpha=(local >= 0) * (1 - enter(prog(local, 3.7, 4))),
        )
    )
    return p.group(tuple(results))


KW, TY, PL, PU, ST = ORANGE, "#d9c7a8", BONE, "#8f8a82", "#f3a676"
CODE = (
    (("impl ", KW), ("Video ", TY), ("for ", KW), ("Intro ", TY), ("{", PU)),
    (
        ("    const ", KW),
        ("FPS", PL),
        (": ", PU),
        ("usize ", TY),
        ("= ", PU),
        ("60", ST),
        (";", PU),
    ),
    (),
    (
        ("    fn ", KW),
        ("render_frame", PL),
        ("(", PU),
        ("&self", KW),
        (", ", PU),
        ("frame", PL),
        (": ", PU),
        ("Frame", TY),
        (") -> ", PU),
        ("Svgr ", TY),
        ("{", PU),
    ),
    (
        ("        let ", KW),
        ("y ", PL),
        ("= ", PU),
        ("spring", PL),
        ("(frame.", PU),
        ("seconds", PL),
        ("());", PU),
    ),
    (
        ("        svgr!", KW),
        ("(<", PU),
        ("text ", PL),
        ("y", TY),
        ("={y}>", PU),
        ('"EVERY FRAME"', ST),
        ("</", PU),
        ("text", PL),
        (">)", PU),
    ),
    (("    }", PU),),
    (("}", PU),),
)


def code(p: Painter[N]) -> N:
    """Reveal colored source tokens and its live bouncing output."""
    lb = p.b
    total = sum(len(text) for row in CODE for text, _ in row)
    counts = (out(prog(lb, 0, 7)) ** 0.7 * total).astype(np.int64)
    left = counts.copy()
    caret_x, caret_y = np.full_like(lb, 150), np.full_like(lb, 300)
    tokens = []
    for i, row in enumerate(CODE):
        col = np.zeros_like(counts)
        y = 300 + i * 56
        active = left > 0
        for text, color in row:
            take = np.minimum(left, len(text))
            shown = tuple(text[: int(n)] for n in take)
            lead = np.asarray([len(s) - len(s.lstrip()) for s in shown])
            tokens.append(
                p.text(
                    150 + (col + lead) * 20.4,
                    y,
                    tuple(s.lstrip() for s in shown),
                    34,
                    color,
                    family=MONO,
                    weight=500,
                )
            )
            left -= take
            col += take
        caret_x = np.where(active | (col > 0), 150 + col * 20.4, caret_x)
        caret_y = np.where(active | (col > 0), y, caret_y)
    body = p.group(
        (
            p.text(150, 220, "SRC/LIB.RS", 22, GREY, family=MONO, weight=500, spacing=3),
            p.rect((150, 236, 1000, 1), GREY, alpha=0.5),
            *tokens,
            p.rect(
                (caret_x + 2, caret_y - 28, 16, 36),
                ORANGE,
                alpha=(np.mod(lb * 2, 1) < 0.6).astype(np.float64),
            ),
            p.callout(
                (150 + 13 * 20.4, 300 + 3 * 56 - 40),
                (150 + 13 * 20.4, 190),
                "CALLED FOR EVERY FRAME",
                prog(lb, 8, 8.8),
            ),
            p.callout(
                (150 + 13 * 20.4, 300 + 5 * 56 + 12),
                (520, 790),
                "RETURNS AN SVG TREE",
                prog(lb, 9, 9.8),
                BONE,
            ),
        ),
        alpha=1 - 0.75 * prog(lb, 12, 12.3),
    )
    appear, leave = out(prog(lb, 3, 4)), enter(prog(lb, 11.7, 12))
    output = p.group(
        (
            p.rect((1190, 320, 600, 338), "#141312", pen=Pen("#3a3733", 1.5)),
            p.corners(1176, 306, 628, 366, 18, ORANGE),
            p.group(
                (
                    p.text(
                        1490,
                        519 - (1 - spring(np.mod(lb, 1), 260, 14)) * 60,
                        "EVERY FRAME",
                        76,
                        spacing=-2,
                        anchor="middle",
                    ),
                ),
                mask=(1190, 320, 600, 338),
            ),
            p.label(1190, 702, "OUTPUT"),
            p.label(1790, 702, tuple(f"FRAME {int(n):05}" for n in p.frames), ORANGE, anchor="end"),
            p.callout((1490, 672), (1450, 820), "DRAWN BY SKIA ON THE GPU", prog(lb, 10, 10.8)),
        ),
        alpha=appear * (1 - leave),
        x=(1 - appear) * 120,
    )
    local = lb - 14
    bar = spring(local - 0.9)
    return p.group(
        (
            p.group(
                (
                    body,
                    output,
                    p.slam(150, 560, "EVERY", 250, lb - 12, dy=190),
                    p.slam(150, 800, "FRAME.", 250, lb - 13, dy=190, color=ORANGE),
                ),
                alpha=(lb < 14).astype(np.float64),
            ),
            p.group(
                (
                    p.rect((0, 0, 1920, 1080), BG),
                    p.text(
                        960,
                        560,
                        "RENDERED ON THE",
                        40,
                        GREY,
                        family=MONO,
                        weight=500,
                        spacing=12,
                        anchor="middle",
                        alpha=prog(local, 0, 0.2),
                    ),
                    p.rect((960 - 30 * bar, 600, np.maximum(60 * bar, 0.5), 4), ORANGE),
                ),
                alpha=(lb >= 14).astype(np.float64),
            ),
        )
    )


def gpu(p: Painter[N]) -> N:
    """Land the GPU drop and animate the original five-stage render pipeline."""
    lb = p.b
    shake = (1 - prog(lb, 0, 0.5)) * 14
    headline = p.group(
        (
            p.rect((0, 0, 1920, 1080), ORANGE),
            p.group(
                (
                    p.text(120, 880, "GPU", 760, INK, spacing=-40),
                    p.rect(
                        (1605, 765 + (1 - spring(lb - 1)) * -300, 115, 115),
                        INK,
                        alpha=prog(lb, 1, 1.05),
                    ),
                ),
                x=(noise(lb * 97) - 0.5) * shake,
                y=(noise(lb * 53 + 3) - 0.5) * shake,
                scale=1 + (1 - out(lb / 0.35)) * 0.18,
                origin=(150, 790),
            ),
            *(
                p.text(
                    x,
                    170,
                    text,
                    22,
                    INK,
                    family=MONO,
                    weight=600,
                    spacing=4,
                    anchor="end" if x == 1790 else "start",
                )
                for x, text in (
                    (130, "SKIA"),
                    (330, "METAL"),
                    (540, "VULKAN"),
                    (1790, "NO BROWSER IN THE LOOP"),
                )
            ),
            p.rect((130, 196, 1660, 3), INK),
        ),
        alpha=(lb < 2).astype(np.float64),
    )
    local = lb - 2
    nodes = (
        ("svgr!", "SVG TREE / FRAME"),
        ("SKIA", "GANESH, GPU"),
        ("METAL", "VULKAN ON LINUX"),
        ("FFMPEG", "H.264 · HEVC · VP9"),
        (".MP4", "OUT.MP4"),
    )
    boxes, links = [], []
    for i, (name, sub) in enumerate(nodes):
        at = 0.4 + i * 0.35
        boxes.append(
            p.group(
                (
                    p.rect(
                        (0, -70, 250, 140),
                        ORANGE if i == 2 else INK,
                        pen=Pen(ORANGE if i == 2 else "#5a564f", 2),
                    ),
                    p.text(125, 8, name, 40, INK if i == 2 else BONE, anchor="middle"),
                    p.text(
                        125,
                        46,
                        sub,
                        15,
                        INK if i == 2 else GREY,
                        family=MONO,
                        weight=500,
                        spacing=1.5,
                        anchor="middle",
                    ),
                ),
                x=190 + i * 330,
                y=640 + (1 - spring(local - at)) * 50,
                alpha=prog(local, at, at + 0.1),
            )
        )
    for i in range(4):
        at = 0.6 + i * 0.35
        xa = 440 + i * 330
        links.append(
            p.rect((xa, 639, np.maximum(80 * out(prog(local, at, at + 0.5)), 0.5), 2), "#5a564f")
        )
        links.extend(
            p.rect(
                (xa + np.mod(local * 2 + k / 3 + i * 0.21, 1) * 80 - 6, 636, 12, 8),
                ORANGE,
                alpha=(local > at + 0.5).astype(np.float64),
            )
            for k in range(3)
        )
    pipeline = p.group(
        (
            p.group(
                (
                    p.text(186, 330, "DIRECTLY ON", 120, spacing=-4),
                    p.text(186, 450, "THE GPU.", 120, ORANGE, spacing=-4),
                ),
                y=(1 - spring(local)) * 60,
                alpha=prog(local, 0, 0.1),
            ),
            *links,
            *boxes,
            p.label(190, 820, "NO HEADLESS BROWSER. NO SCREENSHOTS. NO REACT.", size=22),
            p.text(
                1730,
                450,
                "1920\u00d71080 · 60 FPS",
                30,
                ORANGE,
                family=MONO,
                weight=600,
                anchor="end",
                alpha=prog(local, 2, 2.2),
            ),
        ),
        alpha=(1 - enter(prog(local, 5.7, 6))) * (local >= 0),
    )
    return p.group((headline, pipeline))
