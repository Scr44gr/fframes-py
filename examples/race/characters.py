"""Articulated cartoon silhouettes for Mediabunny, Python and Rust."""

from math import cos, sin, tau

from .art import BLUE, CORAL, INK, WHITE, YELLOW, ellipse, group, path


def bunny(time: float, *, running: bool = True, surprised: bool = False) -> str:
    """Draw a right-facing rabbit with an articulated running cycle."""
    cycle = time * tau * 3.2 if running else 0.0
    kick = sin(cycle)
    hop = -abs(cos(cycle)) * 17 if running else sin(time * 3) * 3
    lavender = "#d2c0ff"
    light = "#f6eeff"
    parts: list[str] = []
    for side in (-1, 1):
        angle = side * kick * 48 - 12
        leg = path(
            "M -12 -42 Q -25 -5 7 1 L 49 7 Q 65 22 32 26 L -10 22 Q -46 10 -35 -32 Z",
            lavender,
            cut=True,
        )
        leg += path("M 7 10 L 37 12 M 1 17 L 30 20", "none", width=2)
        parts.append(group(leg, f"translate({side * 18} -12) rotate({angle:.1f})"))
    parts.append(ellipse(-58, -95, 28, 27, WHITE, stroke=INK, width=4))
    parts.append(
        path(
            "M -42 -167 Q 10 -200 42 -147 L 51 -76 Q 5 -42 -48 -71 Q -68 -118 -42 -167 Z",
            lavender,
            cut=True,
        )
    )
    parts.append(ellipse(2, -115, 28, 38, light))
    arm = path(
        "M -29 -156 Q -48 -128 -27 -112 L 13 -106 Q 29 -105 28 -122 L -7 -132 L -5 -158 Z",
        light,
        cut=True,
    )
    parts.append(group(arm, f"rotate({kick * 23:.1f} -14 -148)"))
    head: list[str] = []
    for x, rotation in ((-24, -26 - kick * 9), (15, -7 + kick * 12)):
        ear = path("M -13 6 C -48 -42 -34 -123 -12 -125 C 13 -124 20 -49 13 6 Z", light, cut=True)
        ear += path("M -9 -16 Q -31 -91 -12 -108 Q 3 -78 3 -12 Z", "#f692b4", width=2)
        head.append(group(ear, f"translate({x} -268) rotate({rotation:.1f})"))
    head.append(
        path(
            "M -62 -252 Q -61 -302 -12 -300 Q 42 -301 53 -263 L 82 -246 "
            "Q 106 -225 77 -207 L 31 -201 Q 8 -177 -29 -196 Q -69 -204 -62 -252 Z",
            light,
            cut=True,
        )
    )
    head.append(
        path("M -59 -260 Q -8 -275 51 -254 L 55 -237 Q -10 -256 -62 -243 Z", "#4ecfd2", width=3)
    )
    head.append(
        path("M -54 -252 L -87 -240 L -67 -231 L -96 -221 L -101 -242 Z", "#4ecfd2", cut=True)
    )
    head.append(ellipse(14, -246, 22, 29, WHITE, stroke=INK, width=3))
    head.append(ellipse(26 if not surprised else 18, -242, 7, 14 if not surprised else 10, INK))
    head.append(ellipse(29, -247, 2, 4, WHITE))
    head.append(path("M -6 -275 L 32 -269", "none", width=7))
    head.append(path("M 72 -243 Q 92 -248 88 -235 Q 80 -222 71 -232 Z", "#f47591", width=3))
    if surprised:
        head.append(ellipse(60, -211, 10, 13, INK))
        head.append(
            path("M -40 -311 L -48 -335 M -14 -317 L -14 -346", "none", stroke=WHITE, width=6)
        )
    else:
        head.append(path("M 33 -224 Q 57 -202 77 -220 Q 61 -193 40 -208 Z", INK, width=3))
        head.append(path("M 49 -215 L 50 -199 L 63 -199 L 65 -216 Z", WHITE, width=2))
    head.append(ellipse(-25, -222, 13, 8, "#f2afc9"))
    parts.append(group("".join(head), f"rotate({kick * 4:.1f} 0 -180)"))
    parts.append(ellipse(17, -150, 19, 19, "#7b67c3", stroke=WHITE, width=3))
    parts.append(
        path("M 6 -142 L 6 -160 L 17 -150 L 28 -160 L 28 -142", "none", stroke=WHITE, width=3)
    )
    return group("".join(parts), f"translate(0 {hop:.2f})")


def team(time: float, *, running: bool = True, celebrating: bool = False) -> str:
    """Draw Rust's running legs and pincers with Python riding its shell."""
    cycle = time * tau * 4.1 if running else time * 3
    bounce = -abs(sin(cycle)) * 8 if running else sin(time * 3) * 4
    parts: list[str] = []
    for side in (-1, 1):
        for index in range(3):
            phase = cycle + index * 1.5 + side
            foot = side * (91 + index * 17) + cos(phase) * 22
            knee = side * (83 + index * 14)
            height = -10 - max(0, sin(phase)) * 17 if running else -8
            leg = f"M {side * (54 + index * 12)} -74 L {knee:.1f} -43 L {foot:.1f} {height:.1f}"
            parts.append(path(leg, "none", stroke=WHITE, width=21))
            parts.append(path(leg, "none", stroke=INK, width=13))
            parts.append(path(leg, "none", stroke=CORAL, width=8))
    parts.append(
        path(
            "M -99 -104 Q -105 -149 -68 -167 Q -9 -190 61 -169 Q 106 -156 108 -111 "
            "L 116 -92 L 92 -91 L 100 -73 L 74 -78 L 77 -61 L 52 -71 Q 0 -51 -55 -73 "
            "L -77 -64 L -77 -82 L -105 -77 L -100 -95 L -122 -94 Z",
            "url(#shell)",
            cut=True,
        )
    )
    parts.append(path("M -72 -148 Q -23 -170 51 -150", "none", stroke="#ffbd79", width=12))
    for side in (-1, 1):
        angle = side * (sin(cycle + side) * 10 + (37 if celebrating else 0))
        claw = path(
            "M 85 -129 Q 134 -169 137 -196 Q 112 -207 114 -234 Q 119 -257 144 -260 "
            "L 144 -227 L 161 -213 L 181 -237 L 172 -270 Q 205 -258 204 -226 "
            "Q 203 -198 176 -190 Q 151 -134 105 -112 Z",
            CORAL,
            cut=True,
        )
        claw += path("M 132 -198 Q 151 -186 170 -196", "none", width=3)
        parts.append(group(claw, f"scale({side} 1) rotate({angle:.1f} 95 -120)"))
    for x in (-37, 35):
        parts.append(path(f"M {x} -154 L {x + 5} -184", "none", stroke=WHITE, width=18))
        parts.append(path(f"M {x} -154 L {x + 5} -184", "none", width=10))
        parts.append(ellipse(x + 5, -185, 22, 26, WHITE, stroke=INK, width=4))
        parts.append(ellipse(x + 12, -181, 7, 11, INK))
        parts.append(ellipse(x + 14, -185, 2, 3, WHITE))
    parts.append(
        path("M -29 -126 Q 10 -103 54 -133 Q 37 -92 7 -97 Q -14 -100 -29 -126 Z", INK, width=3)
    )
    parts.append(path("M -16 -121 Q 19 -108 45 -125 L 33 -113 L -7 -111 Z", WHITE, width=1))
    parts.append(ellipse(-68, -119, 13, 7, "#db4859"))
    parts.append(ellipse(70, -124, 13, 7, "#db4859"))
    snake = path(
        "M -68 -172 C -148 -172 -130 -230 -81 -225 C -44 -223 -41 -189 -18 -190 "
        "C 14 -189 23 -211 -1 -230 C -41 -260 -36 -294 -8 -315 C 17 -338 56 -323 57 -294 "
        "C 59 -267 30 -259 18 -272 C 6 -286 14 -298 25 -292 C 18 -299 12 -291 15 -286 "
        "C 18 -274 33 -278 34 -292 C 35 -308 14 -312 3 -300 C -15 -282 0 -270 25 -250 "
        "C 78 -206 29 -158 -14 -161 C -60 -161 -59 -200 -82 -200 "
        "C -110 -200 -102 -185 -69 -192 Z",
        BLUE,
        cut=True,
    )
    snake += path(
        "M -78 -178 Q -111 -179 -108 -199 M -17 -181 Q 30 -176 38 -209 "
        "M 26 -238 Q -6 -263 -11 -281",
        "none",
        stroke=YELLOW,
        width=12,
    )
    head_bob = sin(cycle * 0.5) * 4
    head = path(
        "M -12 -311 Q -20 -351 18 -363 Q 54 -376 91 -352 L 109 -332 Q 127 -321 111 -304 "
        "Q 78 -289 37 -296 Q 6 -293 -12 -311 Z",
        YELLOW,
        cut=True,
    )
    head += path(
        "M -9 -334 Q 26 -362 67 -346 L 94 -327 Q 50 -332 20 -310 L -4 -312 Z", BLUE, width=0
    )
    head += ellipse(55, -335, 21, 24, WHITE, stroke=INK, width=3)
    head += ellipse(64, -332, 6, 12, INK)
    head += ellipse(65, -337, 2, 3, WHITE)
    head += path("M 34 -362 L 73 -354", "none", width=6)
    head += path("M 72 -315 Q 91 -309 107 -318", "none", width=4)
    head += ellipse(102, -331, 3, 3, INK)
    if celebrating or (time % 2.2) < 0.22:
        head += path(
            "M 105 -313 L 131 -310 L 141 -318 M 131 -310 L 141 -305",
            "none",
            stroke="#f56384",
            width=4,
        )
    snake += group(head, f"translate(0 {head_bob:.2f})")
    parts.append(snake)
    return group("".join(parts), f"translate(0 {bounce:.2f})")
