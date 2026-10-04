"""Resolve overlapping captions once, retaining upstream's inclusive millisecond endpoints."""

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import pairwise

from fframes import Font, Subtitles, TextLayout


@dataclass(frozen=True)
class Caption:
    """One visible interval with premeasured lines and horizontal offsets."""

    start: int
    end: int
    lines: tuple[tuple[str, int], ...]


def captions(
    track: Subtitles, layout: TextLayout, font: Font, width: int, frames: int, fps: int
) -> tuple[Caption, ...]:
    """Prefer the last active source cue and return nonoverlapping frame intervals."""
    events: dict[int, list[int]] = {0: [], frames: []}
    ends: list[int] = []
    lines: list[tuple[tuple[str, int], ...]] = []
    for index, cue in enumerate(track.cues):
        start = (round(cue.start * 1000) * fps + 999) // 1000
        end = ((round(cue.end * 1000) + 1) * fps + 999) // 1000
        ends.append(end)
        wrapped = layout.wrap(cue.text, font, width)
        lines.append(
            tuple(
                (line, max(0, width - length) // 2)
                for line, length in zip(wrapped, layout.widths(wrapped, font), strict=True)
            )
        )
        if start < frames:
            events.setdefault(start, []).append(index)
            events.setdefault(min(end, frames), [])
    boundaries = sorted(events)
    active: list[int] = []
    result: list[Caption] = []
    for start, end in pairwise(boundaries):
        for index in events[start]:
            heappush(active, -index)
        while active and ends[-active[0]] <= start:
            heappop(active)
        if active:
            content = lines[-active[0]]
            if result and result[-1].end == start and result[-1].lines == content:
                result[-1] = Caption(result[-1].start, end, content)
            else:
                result.append(Caption(start, end, content))
    return tuple(result)
