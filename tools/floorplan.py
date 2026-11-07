#!/usr/bin/env python3
"""Turn an Apple RoomPlan .glb export into a 2D floorplan (PNG + SVG) and a
JSON summary of rooms, walls, doors and windows.

RoomPlan exports one named node per element (Wall_*, Door_*, Window_*,
Floor_*, Ceiling_*, Joint_*, plus furniture like chair_*, storage_*), in
meters, Y-up. We project everything onto the floor plane (X/Z) and draw it
top-down.

Per-scan tweaks (e.g. dropping furniture or a stray wall) go in an optional
<scan>.edits.json next to the .glb; see load_edits().

Usage:
    pip install trimesh numpy shapely matplotlib
    python tools/floorplan.py scans/*.glb --out floorplans
"""
import argparse
import fnmatch
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.patches import PathPatch, Polygon as MplPolygon
from matplotlib.path import Path as MplPath
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

WALL_T = 0.10  # RoomPlan models every wall as a 10 cm box centered on the scanned surface
M_TO_FT = 3.280839895


def ft_in(m):
    total_in = m * M_TO_FT * 12
    ft = int(total_in // 12)
    inch = round(total_in - ft * 12)
    if inch == 12:
        ft, inch = ft + 1, 0
    return f"{ft}'{inch}\""


def sqft(m2):
    return m2 * M_TO_FT**2


def load_nodes(path):
    scene = trimesh.load(path, force="scene")
    nodes = {}
    for name in scene.graph.nodes_geometry:
        T, g = scene.graph[name]
        m = scene.geometry[g].copy()
        m.apply_transform(T)
        nodes[name] = m
    return nodes


def footprint(mesh):
    """Union of all triangles projected onto the floor plane (x, z)."""
    tris = mesh.vertices[mesh.faces][:, :, [0, 2]]
    polys = [Polygon(t) for t in tris]
    polys = [p for p in polys if p.is_valid and p.area > 1e-6]
    if not polys:
        return None
    return unary_union(polys).buffer(0)


def segment(mesh):
    """Doors/windows are flat quads: return the two farthest-apart projected points."""
    pts = np.unique(np.round(mesh.vertices[:, [0, 2]], 4), axis=0)
    d = np.linalg.norm(pts[:, None] - pts[None], axis=-1)
    i, j = np.unravel_index(d.argmax(), d.shape)
    return pts[i], pts[j]


def poly_patch(poly, **kw):
    """Matplotlib patch for a shapely polygon, keeping its holes transparent."""
    rings = [np.asarray(poly.exterior.coords)] + [np.asarray(r.coords) for r in poly.interiors]
    verts, codes = [], []
    for r in rings:
        verts.extend(r)
        codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(r) - 2) + [MplPath.CLOSEPOLY])
    return PathPatch(MplPath(verts, codes), **kw)


def polys_of(geom):
    if geom is None:
        return []
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [geom]


def pretty_label(name):
    base = re.sub(r"_\d+$", "", name)
    return base.replace("_other", "").replace("_", " ")


def load_edits(path):
    """Optional sidecar next to the scan: <scan>.edits.json, e.g.
    {"remove": ["chair_*", "Wall_10"],          # names or glob patterns of RoomPlan nodes
     "move": [{"nodes": ["Wall_2", "Door_0"], "by": [dx, dz]}],
     "add_walls": [{"from": [x, z], "to": [x, z], "label": "..."}]}
    add_walls coordinates are the wall centerline in the scan's own frame, in meters."""
    p = Path(path).with_suffix(".edits.json")
    return json.loads(p.read_text()) if p.exists() else {}


def wall_box(a, b, height):
    """A WALL_T-thick wall slab whose centerline runs from a to b (floor-plane [x, z], meters).
    Like RoomPlan walls, it extends WALL_T/2 past each end so corners close."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    v = b - a
    L = np.linalg.norm(v)
    box = trimesh.creation.box(extents=[L + WALL_T, height, WALL_T])
    ang = np.arctan2(v[1], v[0])
    T = trimesh.transformations.rotation_matrix(-ang, [0, 1, 0])
    mid = (a + b) / 2
    T[:3, 3] = [mid[0], height / 2, mid[1]]
    box.apply_transform(T)
    return box


def process(path, outdir):
    nodes = load_nodes(path)
    edits = load_edits(path)
    for pat in edits.get("remove", []):
        hits = [n for n in nodes if fnmatch.fnmatchcase(n, pat)]
        if not hits:
            print(f"  warning: edit pattern {pat!r} matched nothing")
        for n in hits:
            del nodes[n]
    # Moves: translate whole RoomPlan elements in the floor plane
    moved_floor_orig = {}
    for mv in edits.get("move", []):
        dx, dz = mv["by"]
        T = trimesh.transformations.translation_matrix([dx, 0, dz])
        for pat in mv["nodes"]:
            hits = [n for n in nodes if fnmatch.fnmatchcase(n, pat)]
            if not hits:
                print(f"  warning: move pattern {pat!r} matched nothing")
            for n in hits:
                if n.startswith("Floor") and n not in moved_floor_orig:
                    moved_floor_orig[n] = footprint(nodes[n])
                nodes[n].apply_transform(T)
    added = {}
    for i, w in enumerate(edits.get("add_walls", [])):
        name = f"Wall_added_{i}"
        added[name] = w.get("label", name)
        nodes[name] = wall_box(w["from"], w["to"], w.get("height", 2.5))
    kind = lambda n: n.split("_")[0]
    added_fp = unary_union([footprint(nodes[n]) for n in added]) if added else None

    floor_polys = {n: footprint(m) for n, m in nodes.items() if kind(n) == "Floor"}
    # A moved floor takes priority where it now overlaps another room; the area it
    # vacated goes to the neighbouring room it shares the most boundary with.
    for n, orig in moved_floor_orig.items():
        new = floor_polys[n]
        others = [o for o in floor_polys if o not in moved_floor_orig]
        for o in others:
            floor_polys[o] = floor_polys[o].difference(new)
        for piece in polys_of(orig.difference(new)):
            if piece.area < 0.01 or not others:
                continue
            best = max(others, key=lambda o: floor_polys[o].buffer(0.02).intersection(piece).area)
            floor_polys[best] = unary_union([floor_polys[best], piece])
        for o in others:  # drop slivers left behind by the subtraction
            parts = [q for q in polys_of(floor_polys[o].buffer(0)) if q.area >= 0.05]
            floor_polys[o] = unary_union(parts).buffer(1e-4).buffer(-1e-4)

    floors = {n: m for n, m in nodes.items() if kind(n) == "Floor"}
    walls = {n: m for n, m in nodes.items() if kind(n) in ("Wall", "Joint")}
    doors = {n: m for n, m in nodes.items() if kind(n) == "Door"}
    windows = {n: m for n, m in nodes.items() if kind(n) == "Window"}
    ceilings = {n: m for n, m in nodes.items() if kind(n) == "Ceiling"}
    objects = {n: m for n, m in nodes.items() if n[0].islower()}

    ceiling_h = max((m.bounds.mean(0)[1] for m in ceilings.values()), default=None)

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")
    ax.axis("off")

    summary = {"source": str(path), "ceiling_height": None, "rooms": [], "walls": [],
               "doors": [], "windows": [], "objects": []}
    if ceiling_h:
        summary["ceiling_height"] = {"m": round(ceiling_h, 2), "ft_in": ft_in(ceiling_h)}

    # Floors / rooms
    room_colors = ["#f3ede2", "#e6eef2", "#eef2e6", "#f2e6ee"]
    total_area = 0
    pieces = []
    for name in sorted(floors):
        label = name.replace("Floor_", "").replace("_", " ")
        fp = floor_polys[name]
        if added_fp is not None:
            parts = [p for p in polys_of(fp.difference(added_fp)) if p.area > 0.3]
            if len(parts) > 1:  # an added wall divides this room: label each side
                parts.sort(key=lambda p: (round(p.centroid.x, 1), p.centroid.y))
                pieces += [(f"{label}{chr(65 + k)}", p) for k, p in enumerate(parts)]
                continue
        pieces.append((label, fp))
    for i, (label, fp) in enumerate(pieces):
        for p in polys_of(fp):
            ax.add_patch(MplPolygon(np.array(p.exterior.coords), closed=True,
                                    fc=room_colors[i % len(room_colors)], ec="none", zorder=1))
        minx, minz, maxx, maxz = fp.bounds
        w, d = maxx - minx, maxz - minz
        area = fp.area
        total_area += area
        rect = abs(area - w * d) < 0.02 * w * d
        c = fp.representative_point() if not rect else fp.centroid
        text = f"{label}\n{ft_in(w)} × {ft_in(d)}\n{sqft(area):.0f} sq ft" if rect else \
               f"{label}\n{sqft(area):.0f} sq ft\n(overall {ft_in(w)} × {ft_in(d)})"
        if area < 5:  # small spaces (halls, closets): keep the label compact
            text = f"{label}\n{sqft(area):.0f} sq ft"
        ax.text(c.x, c.y, text, ha="center", va="center", fontsize=10 if area >= 5 else 7.5, zorder=6,
                fontweight="bold", color="#333")
        summary["rooms"].append({"name": label, "width_m": round(w, 3), "depth_m": round(d, 3),
                                 "width_ft_in": ft_in(w), "depth_ft_in": ft_in(d),
                                 "area_m2": round(area, 2), "area_sqft": round(sqft(area), 1),
                                 "rectangular": bool(rect)})
    summary["total_area_sqft"] = round(sqft(total_area), 1)
    summary["total_area_m2"] = round(total_area, 2)

    # Furniture (light, under walls). RoomPlan boxes can poke through walls, so clip to the floor.
    floor_all = unary_union(list(floor_polys.values()))
    for name, m in objects.items():
        fp = footprint(m)
        if fp is None:
            continue
        hull = fp.convex_hull.intersection(floor_all)
        if hull.is_empty:
            continue
        for hp in polys_of(hull):
            ax.add_patch(poly_patch(hp, fc="#d9d9d9", ec="#999", lw=0.8, zorder=2, alpha=0.8))
        c = hull.centroid
        ax.text(c.x, c.y, pretty_label(name), ha="center", va="center", fontsize=6.5,
                color="#555", zorder=3)
        ext = m.bounds[1] - m.bounds[0]
        summary["objects"].append({"name": name, "type": pretty_label(name),
                                   "size_m": [round(float(ext[0]), 2), round(float(ext[2]), 2),
                                              round(float(ext[1]), 2)],
                                   "bottom_height_m": round(float(m.bounds[0][1]), 2)})

    # Walls
    # Each wall is a straight slab; using its oriented rectangle squares off the mitered
    # ends RoomPlan leaves where a wall met one that has since been removed.
    wall_geom = unary_union([footprint(m).minimum_rotated_rectangle
                             for m in walls.values() if footprint(m) is not None])
    for p in polys_of(wall_geom):
        ax.add_patch(poly_patch(p, fc="#222", ec="#222", lw=0.5, zorder=4))

    # Wall length labels, placed just outside the drawing
    allb = np.array([m.bounds for m in nodes.values()])
    cx = (allb[:, 0, 0].min() + allb[:, 1, 0].max()) / 2
    cz = (allb[:, 0, 2].min() + allb[:, 1, 2].max()) / 2
    for name, m in sorted(walls.items()):
        if not name.startswith("Wall"):
            continue
        ext = m.bounds[1] - m.bounds[0]
        ctr = m.bounds.mean(0)
        length = max(ext[0], ext[2]) - WALL_T
        summary["walls"].append({"name": name, "added": name in added, "length_m": round(float(length), 3),
                                 "length_ft_in": ft_in(length),
                                 "height_m": round(float(ext[1]), 2)})
        if length < 0.3:
            continue
        horiz = ext[0] >= ext[2]
        off = 0.22
        if horiz:
            tz = ctr[2] + (off if ctr[2] > cz else -off)
            ax.text(ctr[0], tz, ft_in(length), ha="center", va="center", fontsize=7.5,
                    color="#0b5394", zorder=7)
        else:
            tx = ctr[0] + (off if ctr[0] > cx else -off)
            ax.text(tx, ctr[2], ft_in(length), ha="center", va="center", fontsize=7.5,
                    color="#0b5394", rotation=90, zorder=7)

    # Doors and windows: cut a gap in the wall, then draw a symbol
    def opening(m, color, lw_gap, style):
        a, b = segment(m)
        v = b - a
        L = np.linalg.norm(v)
        u = v / L
        n = np.array([-u[1], u[0]])
        t = WALL_T / 2 + 0.02
        quad = np.array([a + n * t, b + n * t, b - n * t, a - n * t])
        ax.add_patch(MplPolygon(quad, closed=True, fc="white", ec="none", zorder=5))
        if style == "window":
            for s in (-0.025, 0.025):
                ax.plot([a[0] + n[0] * s, b[0] + n[0] * s], [a[1] + n[1] * s, b[1] + n[1] * s],
                        color=color, lw=lw_gap, zorder=5)
        else:
            ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw_gap, ls=(0, (2, 1.5)), zorder=5)
            for p in (a, b):  # jamb ticks
                ax.plot([p[0] + n[0] * t, p[0] - n[0] * t], [p[1] + n[1] * t, p[1] - n[1] * t],
                        color="#222", lw=1.2, zorder=5)
        mid = (a + b) / 2
        return L, mid, m.bounds[0][1], m.bounds[1][1] - m.bounds[0][1]

    for name, m in sorted(doors.items()):
        L, mid, bottom, h = opening(m, "#b45f06", 1.2, "door")
        summary["doors"].append({"name": name, "width_m": round(float(L), 3), "width_ft_in": ft_in(L),
                                 "height_m": round(float(h), 2), "height_ft_in": ft_in(h)})
        ax.text(mid[0], mid[1], f"door {ft_in(L)}", fontsize=6, color="#b45f06", ha="center",
                va="bottom", zorder=8, rotation=0)
    for name, m in sorted(windows.items()):
        L, mid, bottom, h = opening(m, "#3d85c6", 1.0, "window")
        summary["windows"].append({"name": name, "width_m": round(float(L), 3), "width_ft_in": ft_in(L),
                                   "height_m": round(float(h), 2), "height_ft_in": ft_in(h),
                                   "sill_height_m": round(float(bottom), 2),
                                   "sill_height_ft_in": ft_in(bottom)})
        ax.text(mid[0], mid[1], f"win {ft_in(L)}", fontsize=6, color="#3d85c6", ha="center",
                va="top", zorder=8)

    # glTF is Y-up with +Z toward the viewer; looking down, screen-up = -Z
    ax.autoscale_view()
    xmin, xmax = ax.get_xlim()
    ax.set_xlim(xmin - 0.5, xmax + 0.5)
    zmin, zmax = ax.get_ylim()
    ax.set_ylim(zmax + 0.5, zmin - 0.5)

    # 1 m / 5 ft scale bar
    sx, sz = xmin - 0.3, zmax + 0.35
    ax.plot([sx, sx + 5 / M_TO_FT], [sz, sz], color="#222", lw=2)
    ax.text(sx + 2.5 / M_TO_FT, sz + 0.05, "5 ft", ha="center", va="top", fontsize=7)

    stem = Path(path).stem
    title = f"{stem}  —  {summary['total_area_sqft']:.0f} sq ft"
    if ceiling_h:
        title += f"  ·  ceiling {ft_in(ceiling_h)}"
    ax.set_title(title, fontsize=12)

    outdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(outdir / f"{stem}.png", dpi=200, bbox_inches="tight", facecolor="white")
    fig.savefig(outdir / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    (outdir / f"{stem}.json").write_text(json.dumps(summary, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb", nargs="+")
    ap.add_argument("--out", default="floorplans")
    args = ap.parse_args()
    for p in args.glb:
        s = process(p, Path(args.out))
        print(f"{p}: {s['total_area_sqft']} sq ft, rooms={[r['name'] for r in s['rooms']]}")


if __name__ == "__main__":
    main()
