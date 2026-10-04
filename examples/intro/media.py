"""Typography, developing images, synchronized video and shader transitions."""

import numpy as np

from examples.intro.drawing import (
    BEAT,
    BG,
    BONE,
    COND,
    GREY,
    INK,
    MONO,
    ORANGE,
    N,
    Painter,
    Pen,
    cubic,
    enter,
    noise,
    out,
    prog,
    pulse,
    spring,
    timecode,
)
from examples.intro.effects import effect, grid, guest, tunnel


def typography(p: Painter[N]) -> N:
    """Move the original eight marquee rows and change the lit row on each beat."""
    texts = (
        "TEXT · SHAPED · MEASURED · WRAPPED · ",
        "KERNING · LIGATURES · 60 FPS · ",
        "EVERY GLYPH ON THE GPU · ",
        "TEXT · TEXT · TEXT · TEXT · ",
        "FONTS COMPILED INTO THE BINARY · ",
        "TYPOGRAPHY IS CODE · ",
        "TEXT · SHAPED · MEASURED · ",
        "WORD BY WORD · LINE BY LINE · ",
    )
    lb = p.b
    lit = (np.floor(np.maximum(lb, 0)).astype(np.int64) * 3 + 1) % len(texts)
    rows = []
    for i, text in enumerate(texts):
        width = p.measure(text, COND, 160)
        direction = -1 if i % 2 == 0 else 1
        appear = out(prog(lb, i * 0.05, 0.6 + i * 0.05))
        offset = (
            np.mod(lb * BEAT * (260 + i * 37 % 140) * direction, width)
            - width
            + (1 - appear) * 900 * direction
        )
        hot = lit == i
        fill = tuple(ORANGE if v else "#00000000" for v in hot)
        border = tuple("#00000000" if v else "#4b4741" for v in hot)
        rows.append(
            p.group(
                tuple(
                    p.text(
                        offset + k * width,
                        150 + i * 140,
                        text,
                        160,
                        fill,
                        family=COND,
                        pen=Pen(border, 1.6),
                    )
                    for k in range(4)
                ),
                alpha=0.7 + np.where(hot, pulse(lb, 5) * 0.3, 0),
            )
        )
    return p.group(
        (
            *rows,
            p.rect((120, 360, 690, 270), BG),
            p.text(150, 560, "TEXT", 170, spacing=-6),
            p.label(154, 408, "01", ORANGE, 26),
            p.label(154, 610, "SHAPED · MEASURED · WRAPPED"),
        ),
        alpha=1 - enter(prog(lb, 5.7, 6)),
    )


def image(p: Painter[N]) -> N:
    """Develop the beta poster through the unmodified dither shader."""
    lb = p.b
    poster = effect(
        p,
        "develop",
        {"uReveal": prog(lb, 0, 0.7), "uProgress": cubic(prog(lb, 0.9, 3.1)) * 1.02},
        {"uInk": "#1a1210", "uHot": ORANGE},
        vectors={"uImg": (1920, 1080)},
        image=p.assets["intro_beta_poster_jpg"],
        box=(560, 300, 1060, 596),
    )
    return p.group(
        (
            p.group(
                (poster, p.corners(542, 282, 1096, 632, 22)),
                scale=0.94 + 0.06 * out(prog(lb, 0, 0.6)),
                origin=(960, 598),
            ),
            p.text(150, 220, "IMAGE", 120, spacing=-4, alpha=prog(lb, 0.2, 0.3)),
            p.label(154, 110, "02", ORANGE, 26),
            p.label(560, 956, "BETA_POSTER.JPG · 2024"),
            p.label(1620, 956, "DITHER → COLOR · ONE SKSL PASS", ORANGE, anchor="end"),
        ),
        alpha=1 - enter(prog(lb, 3.7, 4)),
    )


def film(p: Painter[N], x: float) -> N:
    """Draw both rows of film sprocket holes."""
    return p.group(
        tuple(
            p.rect((x + 10 + i * 770 / 21, y, 14, 10), "#2d2a27", radius=2)
            for i in range(22)
            for y in (274, 760)
        )
    )


def video(p: Painter[N]) -> N:
    """Decode both original feeds and replace the right background at beat four."""
    lb = p.b
    left, right = out(prog(lb, 0, 0.7)), out(prog(lb, 0.5, 1.2))
    keyed = (lb >= 4).astype(np.float64)
    flicker = np.where(lb < 4.25, (noise(lb * 211) > 0.5).astype(np.float64), 1)
    return p.group(
        (
            p.group(
                (
                    p.text(150, 220, "VIDEO", 120, spacing=-4),
                    p.label(154, 110, "03", ORANGE, 26),
                    p.group(
                        (
                            film(p, 150),
                            p.image(
                                p.assets["intro_left_clip_mp4"], (150, 300, 790, 444), video=True
                            ),
                            p.label(
                                150,
                                814,
                                tuple(f"LEFT.MP4  {v}" for v in timecode(p.local_seconds + 28)),
                            ),
                        ),
                        alpha=left,
                        y=(1 - left) * 80,
                    ),
                    p.label(1770, 220, "DECODED BY FFMPEG · IN SYNC TO THE FRAME", anchor="end"),
                ),
                alpha=1 - enter(prog(lb, 5.75, 6)),
            ),
            p.group(
                (
                    film(p, 980),
                    p.group(
                        (
                            p.image(
                                p.assets["intro_right_clip_mp4"], (980, 300, 790, 444), video=True
                            ),
                        ),
                        alpha=1 - keyed,
                    ),
                    p.group(
                        (
                            p.group((tunnel(p),), mask=(980, 300, 790, 444)),
                            p.group((guest(p, (980, 300, 790, 444), 0),), alpha=flicker),
                        ),
                        alpha=keyed,
                    ),
                    p.label(
                        980, 814, tuple(f"RIGHT.MP4  {v}" for v in timecode(p.local_seconds + 246))
                    ),
                    p.label(1770, 814, "CHROMA KEY · SKSL", ORANGE, anchor="end", alpha=keyed),
                ),
                alpha=right,
                y=(1 - right) * 80,
            ),
        )
    )


def shader(p: Painter[N]) -> N:
    """Expand the tunnel into the frame while turning the guest into a halftone print."""
    lb = p.b
    reveal = out(prog(lb, 0, 1))
    box = (
        980 * (1 - reveal),
        300 * (1 - reveal),
        790 + (1920 - 790) * reveal,
        444 + (1080 - 444) * reveal,
    )
    source = p.assets["intro_tunnel_sksl"].read_text(encoding="utf-8")
    lines = tuple(line for line in source.splitlines() if line.strip())
    code = tuple(
        p.text(
            150,
            300 + i * 26 - lb * 40,
            line[:60],
            17,
            "#d8d0c4",
            family=MONO,
            alpha=(((300 + i * 26 - lb * 40) >= 250) & ((300 + i * 26 - lb * 40) < 900)).astype(
                np.float64
            )
            * 0.85,
        )
        for i, line in enumerate(lines)
    )
    return p.group(
        (
            p.group((tunnel(p),), mask=box),
            guest(
                p,
                (
                    980 + (860 - 980) * reveal,
                    300 + (150 - 300) * reveal,
                    790 + (1280 - 790) * reveal,
                    444 + (720 - 444) * reveal,
                ),
                prog(lb, 0.8, 1.6),
            ),
            p.group(
                (
                    p.rect((120, 250, 720, 650), "#0b0b0bb8"),
                    p.group(code, mask=(120, 250, 720, 650)),
                    p.corners(120, 250, 720, 650, 18, ORANGE),
                    p.label(140, 935, "TUNNEL.SKSL · RAYMARCHED · 80 STEPS/PIXEL", ORANGE),
                ),
                alpha=prog(lb, 1, 1.6),
            ),
            p.group(
                (p.text(150, 220, "SHADER", 120, spacing=-4), p.label(154, 110, "04", ORANGE, 26)),
                alpha=prog(lb, 0.8, 0.9),
                y=(1 - spring(lb - 0.8)) * 50,
            ),
            p.group(
                (
                    p.rect((860, 850, 930, 120), ORANGE),
                    p.text(890, 940, "ALL IN ONE FRAME.", 74, INK, spacing=-2),
                ),
                alpha=prog(lb, 4, 4.1),
                y=(1 - spring(lb - 4)) * 60,
            ),
        ),
        alpha=1 - enter(prog(lb, 7.7, 8)),
    )


def preview(p: Painter[N]) -> N:
    """Grow the native-player recording into a full-frame kinetic type takeover."""
    lb = p.b
    full = out(prog(lb, 16, 16.7))
    x, y, w, h = 590 * (1 - full), 262 * (1 - full), 1180 + 740 * full, 660.8 + 414.4 * full
    radius, scale = 14 * (1 - full), 0.9 + 0.1 * spring(lb - 0.5)
    cx, cy = x + w / 2, y + h / 2
    shadow = p.group(
        (p.rect((x, y + 18, w, h), "#000000", radius=radius, alpha=0.55 * (1 - full)),), blur=24
    )
    window = p.group(
        (
            shadow,
            p.group(
                (p.image(p.assets["intro_preview_capture_mp4"], (x, y, w, h), video=True),),
                mask=(x, y, w, h),
                radius=radius,
            ),
            p.rect((x, y, w, h), None, pen=Pen("#3d3a35", 1.5), radius=radius, alpha=1 - full),
        ),
        alpha=prog(lb, 0.5, 0.6),
        matrix=(
            scale,
            0,
            0,
            scale,
            cx * (1 - scale),
            cy * (1 - scale) + (1 - spring(lb - 0.5)) * 120,
        ),
    )
    side = 1 - prog(lb, 15.8, 16.1)
    keys = []
    for i, (key, what) in enumerate(
        (("SPACE", "PLAY / PAUSE"), ("H  L", "SEEK A SECOND"), ("J  K", "STEP A FRAME"))
    ):
        at, ky = 3 + i * 0.5, 560 + i * 78
        keys.append(
            p.group(
                (
                    p.rect((150, ky - 38, 120, 54), "#161514", pen=Pen("#ece8e180", 1.5), radius=8),
                    p.text(210, ky - 3, key, 20, family=MONO, weight=600, anchor="middle"),
                    p.text(290, ky - 3, what, 18, GREY, family=MONO, weight=500, spacing=2),
                ),
                alpha=prog(lb, at, at + 0.1),
                x=(1 - spring(lb - at)) * -60,
            )
        )
    takeover = [p.rect((0, 0, 1920, 1080), "#050505", alpha=prog(lb, 16, 16.5) * 0.6)]
    for tokens, baseline, color, direction in (
        ((("NO", 16), ("BROWSER", 17)), 380, BONE, -1),
        ((("AT", 18), ("ALL", 19)), 690, ORANGE, 1),
        ((("ANYWHERE", 20),), 1000, BONE, -1),
    ):
        first = tokens[0][1]
        texts = tuple(" ".join(word for word, at in tokens if beat >= at) for beat in lb)
        drift = direction * np.maximum(lb - first, 0) * 34
        takeover.append(
            p.slam(
                60 + drift + (-140 if direction > 0 else 0),
                baseline,
                texts,
                330,
                lb - first,
                dy=220,
                color=color,
            )
        )
    return p.group(
        (
            grid(p, 1.5, 0.7, 0.3),
            p.group(
                (
                    p.slam(150, 205, "WATCH IT", 110, lb),
                    p.slam(820, 205, "LIVE.", 110, lb - 1, color=ORANGE),
                ),
                alpha=side,
            ),
            window,
            p.group(
                (
                    p.text(
                        150,
                        330,
                        "NATIVE PREVIEW WINDOW",
                        20,
                        GREY,
                        family=MONO,
                        weight=500,
                        spacing=3,
                    ),
                    p.text(150, 380, "$", 26, ORANGE, family=MONO, weight=600),
                    p.text(180, 380, "cargo run -- preview", 26, family=MONO, weight=500),
                    p.text(150, 440, "GPU · WITH SOUND", 20, family=MONO, weight=500, spacing=2),
                    p.text(
                        150, 472, "NO BROWSER, NO BUNDLER", 20, family=MONO, weight=500, spacing=2
                    ),
                ),
                alpha=prog(lb, 2, 2.4) * side,
            ),
            p.group(
                (
                    *keys,
                    p.callout(
                        (1310, 274), (1310, 170), "REAL-TIME, FRAME BY FRAME", prog(lb, 6, 6.8)
                    ),
                    p.callout(
                        (944, 892), (560, 975), "PLAY · SEEK · LOOP · SCRUB", prog(lb, 8, 8.8), BONE
                    ),
                ),
                alpha=side,
            ),
            p.group(tuple(takeover)),
        ),
        alpha=1 - enter(prog(lb, 31.5, 32)),
    )
