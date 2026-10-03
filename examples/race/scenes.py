"""A continuous 24-second storyboard, expressed as animated SVG frames."""

from math import cos, pi, sin, tau

from .art import (
    BLUE,
    CORAL,
    INK,
    WHITE,
    YELLOW,
    definitions,
    ellipse,
    group,
    noise,
    path,
    smooth,
    star,
    sticker,
    tag,
    text,
)
from .characters import bunny, team

DURATION = 24
CONTINENTS: tuple[tuple[tuple[float, float], ...], ...] = (
    (
        (-166, 65),
        (-145, 70),
        (-123, 56),
        (-103, 70),
        (-73, 60),
        (-53, 48),
        (-77, 28),
        (-91, 17),
        (-102, 23),
        (-119, 40),
        (-139, 55),
    ),
    (
        (-82, 12),
        (-65, 9),
        (-47, -4),
        (-35, -8),
        (-45, -25),
        (-55, -36),
        (-68, -55),
        (-74, -28),
        (-80, -2),
    ),
    (
        (-18, 34),
        (4, 37),
        (30, 32),
        (39, 13),
        (50, 10),
        (41, -13),
        (31, -32),
        (17, -35),
        (9, -14),
        (2, 5),
        (-15, 12),
    ),
    (
        (-10, 36),
        (-6, 57),
        (15, 71),
        (41, 61),
        (63, 72),
        (116, 69),
        (161, 56),
        (140, 40),
        (123, 24),
        (107, 8),
        (82, 7),
        (68, 24),
        (43, 35),
        (26, 40),
    ),
    ((113, -23), (132, -12), (151, -23), (153, -37), (135, -39), (115, -34)),
    ((-49, 59), (-24, 75), (-42, 84), (-61, 76)),
)


def cloud(x: float, y: float, size: float, time: float = 0) -> str:
    """Draw a lumpy white cloud with a lower paper shadow."""
    shape = path(
        "M -67 11 Q -91 -20 -56 -34 Q -56 -70 -21 -60 Q 7 -90 32 -52 "
        "Q 64 -64 72 -31 Q 103 -27 86 6 Q 88 25 49 25 L -43 29 Q -66 28 -67 11 Z",
        WHITE,
        stroke="#dcebed",
        width=3,
    )
    shape += path("M -45 18 Q 5 3 53 15", "none", stroke="#dbe8e4", width=7)
    return group(shape, f"translate({x:.2f} {y + sin(time) * 3:.2f}) scale({size:.3f})")


def flower(x: float, y: float, size: float, color: str, time: float = 0) -> str:
    """Draw an outlined garden flower with gently swaying paper petals."""
    parts = [path("M 0 0 Q -3 -39 0 -67", "none", stroke="#237f70", width=6)]
    parts.append(path("M 0 -19 Q -37 -48 -33 -18 Q -13 -13 0 -19 Z", "#51b86d", width=2))
    parts.extend(
        group(ellipse(0, -92, 16, 24, color, stroke=WHITE, width=4), f"rotate({i * 72} 0 -68)")
        for i in range(5)
    )
    parts.append(ellipse(0, -68, 13, 13, YELLOW, stroke=INK, width=3))
    return group(
        "".join(parts),
        f"translate({x:.2f} {y:.2f}) rotate({sin(time * 2 + x) * 5:.2f}) scale({size})",
    )


def planet(time: float) -> str:
    """Project rotating continents and a separate drifting cloud layer onto a sphere."""
    spin = -0.5 + time * 0.30
    parts = [ellipse(0, 0, 261, 261, "url(#atmosphere)")]
    parts.append(ellipse(0, 0, 218, 218, "url(#sea)", stroke=WHITE, width=5))
    land: list[str] = []
    for continent in CONTINENTS:
        visible: list[tuple[float, float]] = []
        for longitude, latitude in continent:
            lon = longitude * pi / 180 + spin
            lat = latitude * pi / 180
            if cos(lon) * cos(lat) > -0.07:
                visible.append((sin(lon) * cos(lat) * 215, -sin(lat) * 215))
        if len(visible) >= 3:
            data = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in visible) + " Z"
            land.append(path(data, "#bade73", stroke="#f1e9a6", width=3))
    land.extend(
        ellipse(
            0,
            latitude * 215,
            (1 - latitude**2) ** 0.5 * 215,
            16,
            "none",
            stroke="#d8fffa",
            width=0.7,
        )
        for latitude in (-0.6, 0.0, 0.6)
    )
    for index in range(11):
        longitude = index * 2.37 + time * 0.43
        latitude = sin(index * 14.3) * 0.83
        depth = cos(longitude)
        if depth > 0:
            x = sin(longitude) * (1 - latitude**2) ** 0.5 * 213
            land.append(group(cloud(x, latitude * 205, 0.22 + depth * 0.20), opacity=0.8))
    land.append(ellipse(0, 0, 216, 216, "url(#shade)"))
    parts.append('<g clip-path="url(#globe)">' + "".join(land) + "</g>")
    parts.append(path("M -183 -83 A 201 201 0 0 1 -87 -183", "none", stroke="#bdffff", width=7))
    return "".join(parts)


def space(time: float) -> str:
    """Begin close to a paper planet and accelerate toward its surface."""
    stars = []
    for i in range(74):
        x, y = noise(i + 13) * 1280, noise(i + 901) * 720
        radius = 1.5 + noise(i * 4) * 3.3
        alpha = 0.4 + 0.4 * sin(time * 1.4 + i) ** 2
        stars.append(group(star(x, y, radius * 2, WHITE, 15), opacity=alpha))
    base = '<rect width="1280" height="720" fill="#282346"/>'
    base += path(
        "M -100 575 Q 130 80 830 55 Q 1560 200 960 800", "none", stroke="#37305a", width=140
    )
    zoom = smooth((time - 3.5) / 2.7)
    scale = 1 + zoom**2 * 11
    center_x, center_y = 640 - zoom * 150, 360 + zoom * 190
    globe = group(planet(time), f"translate({center_x} {center_y}) scale({scale}) rotate(-12)")
    blur = max(0.0, sin(min(1.0, max(0.0, (time - 3.6) / 2.9)) * pi)) * 7
    base += "".join(stars)
    base += (
        '<defs><filter id="zoomblur" filterUnits="userSpaceOnUse" '
        'x="0" y="0" width="1280" height="720">'
        f'<feGaussianBlur stdDeviation="{blur:.2f}"/></filter></defs>'
    )
    base += f'<g filter="url(#zoomblur)">{globe}</g>' if blur > 0.1 else globe
    if time > 4.1:
        amount = smooth((time - 4.1) / 1.5)
        streaks = []
        for i in range(27):
            angle = i * tau / 27
            radius = 310 + noise(i) * 100
            x, y = 640 + cos(angle) * radius, 360 + sin(angle) * radius
            streaks.append(
                path(
                    f"M {x:.1f} {y:.1f} l {cos(angle) * 200:.1f} {sin(angle) * 200:.1f}",
                    "none",
                    stroke=WHITE,
                    width=2 + noise(i) * 4,
                )
            )
        base += group("".join(streaks), opacity=amount * 0.75)
    return base


def garden(time: float, scroll: float = 0) -> str:
    """Draw independent scenery layers for a side-scrolling paper garden."""
    parts = ['<rect width="1280" height="720" fill="url(#sky)"/>']
    parts.append(ellipse(1090, 123, 60, 60, "#ffdf79", stroke=WHITE, width=6))
    for i in range(7):
        x = (i * 270 - scroll * 0.08) % 1760 - 210
        parts.append(cloud(x, 125 + (i % 3) * 38, 0.65 + (i % 2) * 0.25, time * 0.3))
    for i in range(6):
        x = (i * 400 - scroll * 0.12) % 2000 - 350
        parts.append(ellipse(x, 392, 355, 158 + (i % 2) * 32, "#70c6a1", stroke="#c1eab4", width=5))
    for i in range(10):
        x = (i * 207 - scroll * 0.26) % 1910 - 250
        tree = path("M -12 375 L -9 248 L 9 248 L 14 375 Z", "#ae8368", stroke="#766756", width=3)
        tree += path(
            "M -80 258 Q -111 220 -76 195 Q -74 146 -31 154 Q 0 100 41 148 "
            "Q 94 143 90 194 Q 128 236 82 262 Q 30 285 -3 269 Q -45 287 -80 258 Z",
            "#258e7b",
            stroke=WHITE,
            width=4,
        )
        tree += path(
            "M -43 199 Q -22 160 19 171 M 39 212 Q 76 205 71 235", "none", stroke="#64b990", width=8
        )
        parts.append(group(tree, f"translate({x:.1f} 0)"))
    parts.append(
        path(
            "M -10 378 Q 200 350 421 382 Q 750 339 1290 376 L 1290 730 L -10 730 Z",
            "#86c777",
            stroke="#dbefa8",
            width=7,
        )
    )
    for i in range(23):
        x = (i * 81 - scroll * 0.7) % 1580 - 150
        parts.append(
            flower(
                x,
                397 + (i % 3) * 9,
                0.38 + noise(i) * 0.18,
                ("#f2a6c8", "#ffeaae", "#a398e1")[i % 3],
                time,
            )
        )
    parts.append(
        path(
            "M -10 427 Q 631 395 1290 434 L 1290 722 L -10 722 Z",
            "#deb583",
            stroke="#fce3b3",
            width=7,
        )
    )
    parts.append(path("M 0 525 Q 670 498 1280 537", "none", stroke="#f1d1a0", width=5))
    parts.append(path("M 0 676 Q 670 650 1280 681", "none", stroke="#f1d1a0", width=5))
    for i in range(38):
        x = (i * 109 - scroll) % 1540 - 130
        y = 438 + noise(i + 51) * 234
        parts.append(ellipse(x, y, 3 + noise(i) * 5, 2, "#cda472"))
    return "".join(parts)


def foreground(time: float, scroll: float) -> str:
    """Pass oversized leaves and flowers close to the camera."""
    parts = []
    for i in range(7):
        x = (i * 360 - scroll * 1.7) % 2200 - 410
        parts.append(
            flower(x, 805, 1.25 + noise(i) * 0.5, ("#ef91b6", "#ab97e0", "#ffc85f")[i % 3], time)
        )
        parts.append(
            group(
                path(
                    "M -90 35 Q -184 -89 -141 -122 Q -51 -77 -35 22 "
                    "Q -21 -97 22 -137 Q 72 -58 30 36 Z",
                    "#2c8b73",
                    stroke="#b8dfa0",
                    width=4,
                ),
                f"translate({x + 65:.1f} 720) scale(.7)",
            )
        )
    return "".join(parts)


def dust(x: float, y: float, time: float, strength: float = 1) -> str:
    """Trail small paper puffs behind the racers."""
    puffs = []
    for i in range(6):
        phase = (time * 2.5 + i / 6) % 1
        puffs.append(
            group(
                ellipse(
                    x - phase * 160 * strength,
                    y - 10 - phase * 26,
                    8 + phase * 23,
                    6 + phase * 13,
                    "#fff0c5",
                ),
                opacity=(1 - phase) * 0.7,
            )
        )
    return "".join(puffs)


def finish_line(time: float) -> str:
    """Draw the garden finish gate and tear its ribbon after Rust arrives."""
    parts = [path("M 1090 303 L 1090 713 M 1223 284 L 1223 536", "none", stroke=INK, width=11)]
    parts.append(path("M 1090 303 L 1223 284 L 1223 337 L 1090 354 Z", WHITE, width=4, cut=True))
    for i in range(5):
        x = 1093 + i * 26
        y = 305 - i * 3.8
        parts.append(path(f"M {x} {y} l 25 -3 l 0 21 l -25 3 Z", INK, width=0))
    parts.append(text("FINISH", 1160, 333, 18, INK))
    parts.append(path("M 1093 712 L 1226 526", "none", stroke=WHITE, width=19))
    if time < 18.45:
        parts.append(path("M 1090 545 Q 1157 566 1223 435", "none", stroke="#ef6c8c", width=15))
    else:
        fly = smooth((time - 18.45) / 0.55)
        parts.append(
            path(
                f"M 1090 545 Q {1080 - fly * 95:.1f} {492 - fly * 80:.1f} "
                f"{1152 - fly * 164:.1f} {488 - fly * 106:.1f}",
                "none",
                stroke="#ef6c8c",
                width=15,
            )
        )
        parts.append(
            path(
                f"M 1223 435 Q {1175 + fly * 52:.1f} {527 - fly * 78:.1f} "
                f"{1164 + fly * 147:.1f} {493 - fly * 118:.1f}",
                "none",
                stroke="#ef6c8c",
                width=15,
            )
        )
    return "".join(parts)


def confetti(time: float) -> str:
    """Scatter deterministic colored paper strips and stars."""
    parts = []
    colors = (CORAL, BLUE, YELLOW, "#ab8bdd", WHITE)
    for i in range(90):
        age = (time * (0.4 + noise(i) * 0.3) + noise(i + 75)) % 1
        x = noise(i + 38) * 1450 - 85 + sin(time * 3 + i) * 20
        y = age * 900 - 130
        rotation = time * 170 + i * 31
        if i % 7 == 0:
            parts.append(star(x, y, 12, colors[i % 5], rotation))
        else:
            parts.append(
                group(
                    f'<rect x="-5" y="-10" width="10" height="20" fill="{colors[i % 5]}"/>',
                    f"translate({x:.1f} {y:.1f}) rotate({rotation:.1f})",
                )
            )
    return "".join(parts)


def race(time: float) -> str:
    """Stage the start, the rabbit's lead, the comeback and the victory."""
    active = 9 <= time < 20
    scroll = max(0, min(time - 9, 10.5)) * 260
    if time >= 20:
        return victory(time)
    parts = [garden(time, scroll)]
    intro = time < 9
    rabbit_x = 340 + 395 * smooth((time - 9) / 3.2)
    rust_x = 490 - 30 * smooth((time - 9) / 3)
    if time >= 13:
        rust_x += 405 * smooth((time - 13) / 4)
        rabbit_x -= 80 * smooth((time - 13) / 4)
    if time >= 17:
        rust_x += 230 * smooth((time - 17) / 2.6)
        rabbit_x += 353 * smooth((time - 17) / 3)
    if active:
        parts.append(dust(rabbit_x - 30, 471, time))
        parts.append(dust(rust_x - 80, 655, time, 1.5 if time > 13 else 0.8))
    parts.append(ellipse(rabbit_x, 478, 78, 13, "#b58f69"))
    parts.append(
        sticker(
            bunny(time, running=active, surprised=15.7 < time < 20),
            f"translate({rabbit_x:.2f} 466) scale(.67)",
        )
    )
    if time > 13.3 and time < 17.8:
        boost = smooth((time - 13.3) / 0.4) * (1 - smooth((time - 17.3) / 0.5))
        flames = path(
            "M -104 -117 L -261 -161 L -201 -112 L -326 -88 L -215 -66 L -273 -20 L -105 -61 Z",
            YELLOW,
            stroke=WHITE,
            width=7,
        )
        flames += path("M -101 -102 L -193 -118 L -158 -85 L -236 -75 L -102 -71 Z", CORAL, width=0)
        parts.append(group(flames, f"translate({rust_x:.2f} 629) scale(.73)", boost))
        for i in range(11):
            x = (noise(i) * 1280 - time * 590) % 1280
            y = 280 + noise(i + 12) * 330
            parts.append(
                group(
                    path(
                        f"M {x:.1f} {y:.1f} h {-70 - noise(i) * 80:.1f}",
                        "none",
                        stroke=WHITE,
                        width=3,
                    ),
                    opacity=boost * 0.6,
                )
            )
    parts.append(ellipse(rust_x, 651, 143, 19, "#b58f69"))
    parts.append(sticker(team(time, running=active), f"translate({rust_x:.2f} 633) scale(.77)"))
    if intro:
        parts.append(tag("MEDIABUNNY", 341, 154, "#d6c4ff", 21))
        parts.append(tag("PYTHON + RUST", 710, 297, YELLOW, 22))
        parts.append(path("M 701 319 Q 680 365 611 379", "none", stroke=WHITE, width=5))
        count = "3" if time < 7.4 else "2" if time < 8.1 else "1"
        parts.append(
            group(
                ellipse(998, 220, 72, 72, INK) + text(count, 998, 246, 77, YELLOW),
                opacity=smooth((time - 6.5) / 0.4),
            )
        )
    elif time < 9.7:
        parts.append(text("GO!", 640, 170, 64, YELLOW, outline=True))
    if time >= 17:
        parts.append(
            group(finish_line(time), f"translate({(1 - smooth((time - 17) / 0.8)) * 300:.2f} 0)")
        )
    parts.append(foreground(time, scroll))
    if 18.45 <= time < 20:
        parts.append(confetti(time - 18.45))
    return "".join(parts)


def victory(time: float) -> str:
    """Give Python and Rust an unmistakable winner shot while the rabbit applauds."""
    parts = [garden(time, 2800)]
    rays = []
    for i in range(18):
        angle = i * tau / 18 + 0.05 * time
        a, b = angle - 0.04, angle + 0.04
        rays.append(
            path(
                f"M 640 370 L {640 + cos(a) * 1000:.1f} {370 + sin(a) * 1000:.1f} "
                f"L {640 + cos(b) * 1000:.1f} {370 + sin(b) * 1000:.1f} Z",
                WHITE,
                width=0,
            )
        )
    parts.append(group("".join(rays), opacity=0.28))
    parts.append(ellipse(582, 648, 220, 27, "#b58f69"))
    parts.append(
        sticker(team(time, running=False, celebrating=True), "translate(560 620) scale(1.08)")
    )
    parts.append(ellipse(982, 642, 76, 13, "#b58f69"))
    parts.append(sticker(bunny(time, running=False), "translate(968 626) scale(.62)"))
    parts.append(text("PYTHON + RUST WIN!", 640, 115, 61, YELLOW, outline=True))
    parts.append(star(302, 364, 44, YELLOW, sin(time * 3) * 12))
    parts.append(star(805, 335, 32, YELLOW, -sin(time * 3) * 12))
    parts.append(foreground(time, 2800))
    parts.append(confetti(time))
    return "".join(parts)


def frame(time: float, texture: str, width: int = 1920, height: int = 1080) -> str:
    """Compose one HD frame, including the cloud-covered zoom transition."""
    content = space(time) if time < 6.5 else race(time)
    if 5.2 < time < 7.1:
        opacity = smooth((time - 5.2) / 0.9) * (1 - smooth((time - 6.5) / 0.6))
        clouds = '<rect width="1280" height="720" fill="#e8f5ec"/>'
        for i in range(12):
            clouds += cloud((i % 4) * 380 - 50 + time * 9, (i // 4) * 300, 2.8 + sin(i) * 0.7)
        content += group(clouds, opacity=opacity)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        'viewBox="0 0 1280 720">' + definitions() + content + texture + "</svg>"
    )
