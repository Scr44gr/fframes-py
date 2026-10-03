def box(data: bytes, kind: bytes) -> bytes:
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset : offset + 4], "big")
        assert size >= 8
        if data[offset + 4 : offset + 8] == kind:
            return data[offset + 8 : offset + size]
        offset += size
    raise AssertionError(f"Missing MP4 box: {kind!r}")
