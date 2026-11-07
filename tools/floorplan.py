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
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import polylabel, unary_union

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


FRIENDLY = [  # RoomPlan category prefix -> short plan label
    ("storage_cabinet", "cabinet"), ("storage_shelf", "shelf"), ("refrigerator", "fridge"),
    ("table_dining", "dining table"), ("table", "table"), ("chair", "chair"), ("sofa", "sofa"),
    ("fireplace", "fireplace"), ("sink", "sink"), ("oven", "range"), ("dishwasher", "DW"),
    ("washer", "washer"), ("dryer", "dryer"), ("toilet", "WC"), ("bathtub", "tub"),
    ("bed", "bed"), ("television", "TV"), ("stairs", "stairs"),
]


def friendly_label(name, bottom=0.0, freestanding=False):
    if name.startswith("stove"):  # RoomPlan's "stove" is the cooktop on top of the oven
        return None
    for prefix, label in FRIENDLY:
        if name.startswith(prefix):
            if label == "cabinet":
                if bottom > 1.2:
                    return "upper cab"
                return "island" if freestanding else "base cab"
            return label
    return pretty_label(name)


def pretty_label(name):
    base = re.sub(r"_\d+$", "", name)
    return base.replace("_other", "").replace("_", " ")


def load_edits(path):
    """Optional sidecar next to the scan: <scan>.edits.json, e.g.
    {"rotate_cw": 90,                           # turn the plan clockwise on the page (degrees)
     "remove": ["chair_*", "Wall_10"],          # names or glob patterns of RoomPlan nodes
     "move": [{"nodes": ["Wall_2", "Door_0"], "by": [dx, dz]}],
     "add_walls": [{"from": [x, z], "to": [x, z], "label": "..."}],
     "add_doors": [{"from": [x, z], "to": [x, z], "label": "..."}],
     "add_floor": [[[x, z], [x, z], ...]],      # extra floor polygons
     "rooms": [{"at": [x, z], "name": "Bathroom"}],   # name the room containing a point
     "fixtures": [{"name": "Shower", "rect": [x0, z0, x1, z1]}],  # planned fixtures
     "labels": [{"at": [x, z], "text": "...", "rotation": 0}]}     # free-text notes
    add_doors entries may add "swing_toward": [x, z] to draw the swing (hinged at "from").
    Coordinates are in the scan's own frame, in meters; walls are given by their centerline."""
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


def opening_quad(a, b, height):
    """A flat vertical quad (like RoomPlan's doors/windows) from a to b on the floor plane."""
    (ax_, az), (bx, bz) = a, b
    v = np.array([[ax_, 0, az], [bx, 0, bz], [bx, height, bz], [ax_, height, az]], float)
    return trimesh.Trimesh(vertices=v, faces=[[0, 1, 2], [0, 2, 3]], process=False)


def process(path, outdir, variant=None):
    """Render one scan. With `variant`, use <scan>.<variant>.edits.json instead of the
    base edits and write <scan>.<variant>.png/svg/json (for comparing design options)."""
    nodes = load_nodes(path)
    if variant:
        edits = json.loads(Path(path).with_suffix(f".{variant}.edits.json").read_text())
    else:
        edits = load_edits(path)
    # Turn the whole plan clockwise on the page (in 90 degree steps or any angle).
    # Later edit coordinates refer to the rotated plan.
    if edits.get("rotate_cw"):
        # On the page x points right and z points down, so clockwise by t maps
        # (x, z) -> (x cos t - z sin t, x sin t + z cos t): a rotation about +Y by -t.
        R = trimesh.transformations.rotation_matrix(-np.radians(edits["rotate_cw"]), [0, 1, 0])
        for m in nodes.values():
            m.apply_transform(R)
    for pat in edits.get("remove", []):
        hits = [n for n in nodes if fnmatch.fnmatchcase(n, pat)]
        if not hits:
            print(f"  warning: edit pattern {pat!r} matched nothing")
        for n in hits:
            del nodes[n]
    # Moves: translate whole RoomPlan elements in the floor plane
    for mv in edits.get("move", []):
        dx, dz = mv["by"]
        T = trimesh.transformations.translation_matrix([dx, 0, dz])
        for pat in mv["nodes"]:
            hits = [n for n in nodes if fnmatch.fnmatchcase(n, pat)]
            if not hits:
                print(f"  warning: move pattern {pat!r} matched nothing")
            for n in hits:
                nodes[n].apply_transform(T)
    added = set()
    for i, w in enumerate(edits.get("add_walls", [])):
        name = f"Wall_added_{i}"
        added.add(name)
        nodes[name] = wall_box(w["from"], w["to"], w.get("height", 2.5))
    swings = {}
    for i, d in enumerate(edits.get("add_doors", [])):
        nodes[f"Door_added_{i}"] = opening_quad(d["from"], d["to"], d.get("height", 2.03))
        if "swing_toward" in d:  # hinge at "from", opening toward the given point
            swings[f"Door_added_{i}"] = {"hinge": d["from"], "other": d["to"],
                                         "toward": d["swing_toward"]}
    kind = lambda n: n.split("_")[0]

    floors = {n: m for n, m in nodes.items() if kind(n) == "Floor"}
    walls = {n: m for n, m in nodes.items() if kind(n) in ("Wall", "Joint")}
    doors = {n: m for n, m in nodes.items() if kind(n) == "Door"}
    windows = {n: m for n, m in nodes.items() if kind(n) == "Window"}
    ceilings = {n: m for n, m in nodes.items() if kind(n) == "Ceiling"}
    objects = {n: m for n, m in nodes.items() if n[0].islower()}

    ceiling_h = max((m.bounds.mean(0)[1] for m in ceilings.values()), default=None)

    # Each wall is a straight slab; using its oriented rectangle squares off the mitered
    # ends RoomPlan leaves where a wall met one that has since been removed.
    wall_geom = unary_union([footprint(m).minimum_rotated_rectangle
                             for m in walls.values() if footprint(m) is not None])

    furn = [footprint(m) for n, m in objects.items() if m.bounds[0][1] <= 1.2]
    furn_union = unary_union([f.convex_hull for f in furn if f is not None]) if furn else None

    floor_polys = {n: footprint(m) for n, m in floors.items()}
    extra_floor = [Polygon(f) for f in edits.get("add_floor", [])]
    floor_all = unary_union(list(floor_polys.values()) + extra_floor).buffer(1e-4).buffer(-1e-4)

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")
    ax.axis("off")

    summary = {"source": str(path), "ceiling_height": None, "rooms": [], "walls": [],
               "doors": [], "windows": [], "objects": []}
    if ceiling_h:
        summary["ceiling_height"] = {"m": round(ceiling_h, 2), "ft_in": ft_in(ceiling_h)}

    # Rooms: the floor split up by the walls. Each region is grown back out to the wall
    # centerlines (how RoomPlan measures rooms) and named after the scanned floor it
    # mostly sits on, unless the edits name it.
    regions = [r for r in polys_of(floor_all.difference(wall_geom)) if r.area > 0.3]
    rooms = []
    dividers = []
    nice = lambda n: n.replace("Floor_", "").replace("_", " ")
    for r in regions:
        full = r.buffer(WALL_T / 2, join_style=2).intersection(floor_all)
        full = max(polys_of(full), key=lambda q: q.area)
        # Open plan: RoomPlan scanned two or more whole rooms that no wall separates
        # (e.g. kitchen + living room). Split the space along their floor boundary.
        whole = [n for n, f in floor_polys.items()
                 if f.area > 0.5 and f.intersection(full).area >= 0.9 * f.area]
        if len(whole) >= 2:
            parts = {n: full.intersection(floor_polys[n]) for n in whole}
            rest = full.difference(unary_union(list(parts.values())))
            for piece in polys_of(rest):  # leftovers join the part they touch most
                if piece.area < 1e-4:
                    continue
                best = max(parts, key=lambda n: parts[n].buffer(0.02).intersection(piece).area)
                parts[best] = unary_union([parts[best], piece])
            for n, part in parts.items():
                part = max(polys_of(part.buffer(0)), key=lambda q: q.area)
                rooms.append([nice(n), part, part.intersection(r)])
            names_ = list(parts)
            for i in range(len(names_)):
                for j in range(i + 1, len(names_)):
                    shared = parts[names_[i]].buffer(0.01).intersection(
                        parts[names_[j]].buffer(0.01)).difference(wall_geom)
                    if not shared.is_empty:
                        dividers.append(shared)
            continue
        base = max(floor_polys, key=lambda n: floor_polys[n].intersection(r).area) \
            if floor_polys else "Floor_Room"
        rooms.append([nice(base), full, r])
    label_opts = {}
    for spec in edits.get("rooms", []):
        pt = Point(spec["at"])
        for rm in rooms:
            if rm[2].contains(pt):
                rm[0] = spec["name"]
                label_opts[spec["name"]] = spec
    rooms.sort(key=lambda rm: (round(rm[1].centroid.x, 1), rm[1].centroid.y))
    names = [rm[0] for rm in rooms]
    seen = {}
    for rm in rooms:  # rooms sharing a scanned floor's name become 1A, 1B, ...
        if names.count(rm[0]) > 1:
            k = seen.get(rm[0], 0)
            seen[rm[0]] = k + 1
            rm[0] = f"{rm[0]}{chr(65 + k)}"

    room_colors = ["#f3ede2", "#e6eef2", "#eef2e6", "#f2e6ee", "#eae6f2", "#f2efe6"]
    total_area = 0
    for i, (label, fp, inner) in enumerate(sorted(rooms, key=lambda rm: rm[0])):
        ax.add_patch(poly_patch(fp, fc=room_colors[i % len(room_colors)], ec="none", zorder=1))
        minx, minz, maxx, maxz = fp.bounds
        w, d = maxx - minx, maxz - minz
        area = fp.area
        total_area += area
        rect = abs(area - w * d) < 0.02 * w * d
        c = fp.centroid if rect else polylabel(inner, tolerance=0.01)
        if furn_union is not None and furn_union.intersects(c.buffer(0.6)):
            # keep the room label off the furniture: use the middle of the open floor
            free = [q for q in polys_of(inner.difference(furn_union.buffer(0.1))) if q.area > 0.5]
            if free:
                c = polylabel(max(free, key=lambda q: q.area), tolerance=0.01)
        opt = label_opts.get(label, {})
        if "label_at" in opt:
            c = Point(opt["label_at"])
        text = f"{label}\n{ft_in(w)} × {ft_in(d)}\n{sqft(area):.0f} sq ft" if rect else \
               f"{label}\n{sqft(area):.0f} sq ft\n(overall {ft_in(w)} × {ft_in(d)})"
        if area < 5 or opt.get("compact"):  # small spaces (baths, halls, closets): compact label
            text = f"{label}\n{sqft(area):.0f} sq ft"
        ax.text(c.x, c.y, text, ha="center", va="center",
                fontsize=opt.get("label_size", 10 if area >= 5 else 8),
                zorder=6, fontweight="bold", color="#333")
        summary["rooms"].append({"name": label, "width_m": round(w, 3), "depth_m": round(d, 3),
                                 "width_ft_in": ft_in(w), "depth_ft_in": ft_in(d),
                                 "area_m2": round(area, 2), "area_sqft": round(sqft(area), 1),
                                 "rectangular": bool(rect)})
    for dv in dividers:  # open-plan boundary between rooms
        for q in polys_of(dv):
            mrr = q.minimum_rotated_rectangle
            pts = np.asarray(mrr.exterior.coords)[:4]
            e = [(np.linalg.norm(pts[i] - pts[(i + 1) % 4]), i) for i in range(4)]
            _, i = max(e)
            a = (pts[i] + pts[(i + 3) % 4]) / 2
            b = (pts[(i + 1) % 4] + pts[(i + 2) % 4]) / 2
            ax.plot([a[0], b[0]], [a[1], b[1]], color="#888", lw=1, ls=(0, (6, 4)), zorder=1.5)
    summary["total_area_sqft"] = round(sqft(total_area), 1)
    summary["total_area_m2"] = round(total_area, 2)

    # Furniture (light, under walls). RoomPlan boxes can poke through walls, so clip to the floor.
    # Scale for fitting labels: the figure is ~10in across the larger drawing dimension.
    fb = floor_all.bounds
    m_per_pt = (max(fb[2] - fb[0], fb[3] - fb[1]) + 1.0) / (10 * 72)
    def fits(text, size, poly):
        mrr = poly.minimum_rotated_rectangle
        minx, minz, maxx, maxz = mrr.bounds
        tw = len(text) * 0.55 * size * m_per_pt
        th = 1.3 * size * m_per_pt
        if tw <= (maxx - minx) * 0.95 and th <= (maxz - minz) * 0.95:
            return 0
        if tw <= (maxz - minz) * 0.95 and th <= (maxx - minx) * 0.95:
            return 90
        return None
    uppers = []
    placed = []  # label boxes already drawn, to avoid overlapping text
    order = sorted(objects.items(), key=lambda kv: footprint(kv[1]).area
                   if footprint(kv[1]) is not None else 0)
    for name, m in order:
        fp = footprint(m)
        if fp is None:
            continue
        hull = fp.convex_hull.intersection(floor_all)
        if hull.is_empty:
            continue
        bottom = float(m.bounds[0][1])
        kind_ = friendly_label(name, bottom, hull.distance(wall_geom) > 0.15)
        if kind_ is None:  # e.g. cooktop sitting on the oven
            continue
        if bottom > 1.2:  # wall-hung (upper cabinets, shelves): draw after base units, dashed
            uppers.append((hull, kind_))
        else:
            for hp in polys_of(hull):
                ax.add_patch(poly_patch(hp, fc="#d9d9d9", ec="#999", lw=0.8, zorder=2, alpha=0.8))
            rot = fits(kind_, 6.5, hull)
            if rot is not None:
                c = hull.centroid
                tw = len(kind_) * 0.55 * 6.5 * m_per_pt / 2
                th = 1.3 * 6.5 * m_per_pt / 2
                hw, hh = (tw, th) if rot == 0 else (th, tw)
                box = Polygon([(c.x - hw, c.y - hh), (c.x + hw, c.y - hh),
                               (c.x + hw, c.y + hh), (c.x - hw, c.y + hh)])
                if not any(box.intersects(b) for b in placed):
                    placed.append(box)
                    ax.text(c.x, c.y, kind_, ha="center", va="center", fontsize=6.5,
                            color="#555", zorder=3, rotation=rot)
        ext = m.bounds[1] - m.bounds[0]
        summary["objects"].append({"name": name, "type": kind_,
                                   "size_m": [round(float(ext[0]), 2), round(float(ext[2]), 2),
                                              round(float(ext[1]), 2)],
                                   "bottom_height_m": round(bottom, 2)})
    for hull, kind_ in uppers:
        for hp in polys_of(hull):
            ax.add_patch(poly_patch(hp, fc="none", ec="#777", lw=0.7, ls=(0, (3, 2)), zorder=2.5))

    # Planned fixtures (shower, toilet, vanity, ...): labelled rectangles from the edits
    IN = 0.0254
    for fx in edits.get("fixtures", []):
        x0, z0, x1, z1 = fx["rect"]
        poly = Polygon([(x0, z0), (x1, z0), (x1, z1), (x0, z1)])
        ax.add_patch(poly_patch(poly, fc="white", ec="#555", lw=0.9, zorder=3))
        if fx.get("hatch"):  # light pattern (e.g. shower floor) under the outline
            ax.add_patch(poly_patch(poly, fc="none", ec="#bbb", lw=0, zorder=3.1,
                                    hatch=fx["hatch"]))
        if fx.get("shape") == "toilet":  # bowl drawn as an ellipse toward the front
            from matplotlib.patches import Ellipse
            w, d = abs(x1 - x0), abs(z1 - z0)
            horiz = w >= d  # long side = depth of the toilet
            front = fx.get("front", "w")
            tank = 7 * IN
            if front in ("w", "e"):
                bx = (min(x0, x1) + (0 if front == "w" else tank) + max(x0, x1) - (tank if front == "w" else 0)) / 2
                ax.add_patch(Ellipse((bx, (z0 + z1) / 2), w - tank - 0.02, d - 0.04, fc="white",
                                     ec="#555", lw=0.8, zorder=3.5))
                tx = max(x0, x1) - tank if front == "w" else min(x0, x1) + tank
                ax.plot([tx, tx], [z0, z1], color="#555", lw=0.8, zorder=3.5)
        ax.text((x0 + x1) / 2, (z0 + z1) / 2, fx["name"], ha="center", va="center", fontsize=6.5,
                color="#333", zorder=4.5, rotation=fx.get("text_rotation", 0))
        summary.setdefault("fixtures", []).append(
            {"name": fx["name"], "width_ft_in": ft_in(abs(x1 - x0)), "depth_ft_in": ft_in(abs(z1 - z0))})

    # Free-text notes on the plan
    for lb in edits.get("labels", []):
        ax.text(lb["at"][0], lb["at"][1], lb["text"], ha="center", va="center", fontsize=7,
                style="italic", color="#666", rotation=lb.get("rotation", 0), zorder=8)

    # Walls
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
        # screen y is flipped (z points down), so negate z for the on-screen angle
        rot = np.degrees(np.arctan2(-u[1], u[0]))
        rot = (rot + 90) % 180 - 90  # keep text upright
        return L, mid, m.bounds[0][1], m.bounds[1][1] - m.bounds[0][1], rot

    for name, m in sorted(doors.items()):
        L, mid, bottom, h, rot = opening(m, "#b45f06", 1.2, "door")
        summary["doors"].append({"name": name, "width_m": round(float(L), 3), "width_ft_in": ft_in(L),
                                 "height_m": round(float(h), 2), "height_ft_in": ft_in(h)})
        ax.text(mid[0], mid[1], f"door {ft_in(L)}", fontsize=6, color="#b45f06", ha="center",
                va="bottom", zorder=8, rotation=rot, rotation_mode="anchor")
        if name in swings:  # draw the leaf open at 90 degrees and its swing arc
            hinge, other = np.array(swings[name]["hinge"]), np.array(swings[name]["other"])
            toward = np.array(swings[name]["toward"])
            v = other - hinge
            n = np.array([-v[1], v[0]])
            if np.dot(n, toward - hinge) < 0:
                n = -n
            tip = hinge + n
            ax.plot([hinge[0], tip[0]], [hinge[1], tip[1]], color="#b45f06", lw=1.0, zorder=5)
            a0 = np.arctan2(v[1], v[0])
            a1 = np.arctan2(n[1], n[0])
            if a1 - a0 > np.pi:
                a1 -= 2 * np.pi
            elif a0 - a1 > np.pi:
                a1 += 2 * np.pi
            t = np.linspace(a0, a1, 30)
            ax.plot(hinge[0] + L * np.cos(t), hinge[1] + L * np.sin(t), color="#b45f06",
                    lw=0.6, ls=(0, (3, 2)), zorder=5)
    for name, m in sorted(windows.items()):
        L, mid, bottom, h, rot = opening(m, "#3d85c6", 1.0, "window")
        summary["windows"].append({"name": name, "width_m": round(float(L), 3), "width_ft_in": ft_in(L),
                                   "height_m": round(float(h), 2), "height_ft_in": ft_in(h),
                                   "sill_height_m": round(float(bottom), 2),
                                   "sill_height_ft_in": ft_in(bottom)})
        ax.text(mid[0], mid[1], f"win {ft_in(L)}", fontsize=6, color="#3d85c6", ha="center",
                va="top", zorder=8, rotation=rot, rotation_mode="anchor")

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

    stem = Path(path).stem + (f".{variant}" if variant else "")
    title = edits.get("title", stem) + f"  —  {summary['total_area_sqft']:.0f} sq ft"
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
        # Design options: <scan>.<variant>.edits.json
        stem = Path(p).stem
        for vf in sorted(Path(p).parent.glob(f"{stem}.*.edits.json")):
            variant = vf.name[len(stem) + 1:-len(".edits.json")]
            s = process(p, Path(args.out), variant)
            print(f"  option {variant}: {s['total_area_sqft']} sq ft, "
                  f"rooms={[(r['name'], r['area_sqft']) for r in s['rooms']]}")


if __name__ == "__main__":
    main()
