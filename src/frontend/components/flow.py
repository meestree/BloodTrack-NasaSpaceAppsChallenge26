"""Shared perfusion-unit (PU) ranges for maps, tables, and statistics."""

# Low danger boundary, normal lower/upper boundaries, high danger boundary.
FLOW_RANGES = {
    'Neck': (7, 15, 40, 60),
    'Arms': (5, 10, 30, 50),
    'Legs': (2, 5, 20, 35),
}


def flow_ranges(part: str) -> tuple[int, int, int, int]:
    group = {'Left arm': 'Arms', 'Right arm': 'Arms',
             'Left leg': 'Legs', 'Right leg': 'Legs'}.get(part, part)
    return FLOW_RANGES[group]
