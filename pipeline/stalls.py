"""
stalls.py - estimated stall positions inside a lot polygon (metres).

Port of the ParkShark Duke surface model (parkshark/scripts/estimate_spaces.py):
1.2 m perimeter setback, 2.6 x 5.4 m bays, 6.2 m aisle, two orientations x eight
grid offsets, keep the densest layout. Then reconciled with the OFFICIAL space
count: if the grid finds at least that many bays we keep the ones nearest the
entrance; if it finds fewer we fall back to a schematic lattice with exactly the
official count and say so. Positions are estimates; counts are official.
"""
import math

from shapely import affinity
from shapely.geometry import Point, box
from shapely.prepared import prep

BAY_W, BAY_L, AISLE, SETBACK = 2.6, 5.4, 6.2, 1.2


def _fit(poly, angle, y_off, x_off, need_module=True):
    c = poly.centroid
    r = affinity.rotate(poly, -angle, origin=c)
    pr = prep(r)
    minx, miny, maxx, maxy = r.bounds
    module = 2 * BAY_L + AISLE
    out = []
    y = miny - module + y_off
    while y < maxy:
        rows = [y, y + BAY_L + AISLE] if need_module else [y, y + BAY_L + AISLE / 2]
        for ry in rows:
            x = minx - BAY_W + x_off
            while x < maxx:
                if pr.contains(box(x, ry, x + BAY_W, ry + BAY_L)):
                    out.append((x + BAY_W / 2, ry + BAY_L / 2))
                x += BAY_W
        y += module if need_module else 2 * BAY_L + AISLE
    if not out:
        return []
    return [affinity.rotate(Point(q), angle, origin=c).coords[0] for q in out]


def grid_bays(poly):
    best = []
    for setback in (SETBACK, 0.4):
        inner = poly.buffer(-setback)
        if inner.is_empty:
            continue
        mrr = inner.minimum_rotated_rectangle
        xs, ys = mrr.exterior.coords.xy
        e = max(((xs[i + 1] - xs[i], ys[i + 1] - ys[i]) for i in range(4)), key=lambda d: math.hypot(*d))
        base = math.degrees(math.atan2(e[1], e[0]))
        for ang in (base, base + 90):
            for k in range(8):
                for xo in (0.0, BAY_W / 2):
                    got = _fit(inner, ang, k * (2 * BAY_L + AISLE) / 8, xo)
                    if len(got) > len(best):
                        best = got
    return best


def lattice(poly, n):
    """Exactly n points on a regular lattice inside the polygon (schematic)."""
    inner = poly.buffer(-1.0)
    if inner.is_empty:
        inner = poly
    mrr = inner.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    e = max(((xs[i + 1] - xs[i], ys[i + 1] - ys[i]) for i in range(4)), key=lambda d: math.hypot(*d))
    ang = math.degrees(math.atan2(e[1], e[0]))
    c = inner.centroid
    r = affinity.rotate(inner, -ang, origin=c)
    pr = prep(r)
    minx, miny, maxx, maxy = r.bounds
    s = math.sqrt(r.area / max(n, 1))
    pts = []
    for _ in range(60):
        pts = []
        y = miny + s / 2
        while y < maxy:
            x = minx + s / 2
            while x < maxx:
                if pr.contains(Point(x, y)):
                    pts.append((x, y))
                x += s
            y += s
        if len(pts) >= n:
            break
        s *= 0.97
    pts.sort(key=lambda q: (round(q[1] / s), q[0]))
    if len(pts) > n:                      # drop evenly so the lattice stays regular-looking
        step = len(pts) / n
        pts = [pts[int(i * step)] for i in range(n)]
    return [affinity.rotate(Point(q), ang, origin=c).coords[0] for q in pts]


def layout(poly, n, entrance):
    bays = grid_bays(poly)
    if len(bays) >= n:
        ep = Point(entrance)
        bays.sort(key=lambda q: Point(q).distance(ep))
        return bays[:n], f"estimated 2.6x5.4 m bay grid ({len(bays)} fit, trimmed to the official {n})"
    return lattice(poly, n), (f"schematic lattice (bay grid fit only {len(bays)} of the official {n}; "
                              "stall positions not mapped)")
