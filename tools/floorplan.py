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
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
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
    """The polygons in a shapely geometry (lines/points left over from clipping are dropped)."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if hasattr(geom, "geoms"):  # MultiPolygon or GeometryCollection
        return [p for g in geom.geoms for p in polys_of(g)]
    return []


FRIENDLY = [  # RoomPlan category prefix -> short plan label
    ("storage_cabinet", "cabinet"), ("storage_shelf", "shelf"), ("refrigerator", "fridge"),
    ("table_dining", "dining table"), ("table", "table"), ("chair", "chair"), ("sofa", "sofa"),
    ("fireplace", "fireplace"), ("sink", "sink"), ("oven", "range"), ("dishwasher", "DW"),
    ("washer", "washer"), ("dryer", "dryer"), ("toilet", "WC"), ("bathtub", "tub"),
    ("bed", "bed"), ("television", "TV"), ("stairs", "stairs"),
]


SQUARED = {"base cab", "upper cab", "tall cab", "island", "shelf", "fridge", "range", "DW",
           "sink", "washer", "dryer"}


def square_up(poly, walls, snap=0.12, align_deg=4):
    """Draw built-ins as clean rectangles: the smallest enclosing rectangle, made axis-aligned
    when it's within a few degrees of square, with any side that stops just short of a wall
    pushed out to meet it."""
    mrr = poly.minimum_rotated_rectangle
    pts = np.asarray(mrr.exterior.coords)[:4]
    edge = pts[1] - pts[0]
    ang = np.degrees(np.arctan2(edge[1], edge[0])) % 90
    if min(ang, 90 - ang) > align_deg:
        return mrr  # genuinely angled (e.g. a sofa set on the diagonal): keep its angle
    x0, z0, x1, z1 = poly.bounds
    box = lambda a, b, c, d: Polygon([(a, b), (c, b), (c, d), (a, d)])
    for side in range(4):  # 0: left, 1: top, 2: right, 3: bottom
        for step in np.arange(0.005, snap + 1e-9, 0.005):
            probe = [box(x0 - step, z0, x0, z1), box(x0, z0 - step, x1, z0),
                     box(x1, z0, x1 + step, z1), box(x0, z1, x1, z1 + step)][side]
            if probe.intersects(walls):
                if side == 0:
                    x0 -= step
                elif side == 1:
                    z0 -= step
                elif side == 2:
                    x1 += step
                else:
                    z1 += step
                break
    return box(x0, z0, x1, z1)


def _axis_rect(poly):
    """(x0, z0, x1, z1) if poly is an axis-aligned rectangle, else None."""
    if poly.is_empty or abs(poly.area - shapely_box_area(poly)) > 1e-6 * max(poly.area, 1e-9) + 1e-9:
        return None
    return poly.bounds


def shapely_box_area(poly):
    x0, z0, x1, z1 = poly.bounds
    return (x1 - x0) * (z1 - z0)


def _rect(x0, z0, x1, z1):
    return Polygon([(x0, z0), (x1, z0), (x1, z1), (x0, z1)])


def _touching_sides(b, walls, tol=0.02):
    x0, z0, x1, z1 = b
    probes = [_rect(x0 - tol, z0 + tol, x0, z1 - tol), _rect(x0 + tol, z0 - tol, x1 - tol, z0),
              _rect(x1, z0 + tol, x1 + tol, z1 - tol), _rect(x0 + tol, z1, x1 - tol, z1 + tol)]
    return [i for i, p in enumerate(probes) if p.intersects(walls)]


def set_depth(poly, walls, depth):
    """Make a wall-backed cabinet exactly `depth` deep, measured out from the wall behind it.
    In a corner (two walls), the wall behind is the one across the unit's shorter side."""
    b = _axis_rect(poly)
    if b is None:
        return None
    x0, z0, x1, z1 = b
    sides = _touching_sides(b, walls)
    if not sides:
        return None
    # the depth direction is the shorter dimension among the wall-touching sides
    side = min(sides, key=lambda i: (x1 - x0) if i in (0, 2) else (z1 - z0))
    if side == 0:
        x1 = x0 + depth
    elif side == 2:
        x0 = x1 - depth
    elif side == 1:
        z1 = z0 + depth
    else:
        z0 = z1 - depth
    return _rect(x0, z0, x1, z1)


def close_gaps(poly, targets, walls, reach=0.15):
    """Stretch a cabinet's ends (along its run, not out from the wall) to meet a neighbouring
    cabinet or wall when the gap is smaller than `reach`."""
    b = _axis_rect(poly)
    if b is None:
        return poly
    x0, z0, x1, z1 = b
    sides = _touching_sides(b, walls)
    if not sides:
        return poly
    back = min(sides, key=lambda i: (x1 - x0) if i in (0, 2) else (z1 - z0))
    ends = (1, 3) if back in (0, 2) else (0, 2)  # run direction is along the back wall
    for side in ends:
        for step in np.arange(0.005, reach + 1e-9, 0.005):
            probe = [_rect(x0 - step, z0 + 0.01, x0, z1 - 0.01), _rect(x0 + 0.01, z0 - step, x1 - 0.01, z0),
                     _rect(x1, z0 + 0.01, x1 + step, z1 - 0.01), _rect(x0 + 0.01, z1, x1 - 0.01, z1 + step)][side]
            if probe.intersects(targets):
                if side == 0:
                    x0 -= step - 0.005
                elif side == 1:
                    z0 -= step - 0.005
                elif side == 2:
                    x1 += step - 0.005
                else:
                    z1 += step - 0.005
                break
    return _rect(x0, z0, x1, z1)


def friendly_label(name, bottom=0.0, freestanding=False, top=0.0):
    name = name.split("~")[0]  # drop the part tag used on combined plans
    if name.startswith("stove"):  # RoomPlan's "stove" is the cooktop on top of the oven
        return None
    for prefix, label in FRIENDLY:
        if name.startswith(prefix):
            if label == "cabinet":
                if bottom > 1.2:
                    return "upper cab"
                if top > 1.5:
                    return "tall cab"
                return "island" if freestanding else "base cab"
            return label
    return pretty_label(name)


def pretty_label(name):
    base = re.sub(r"_\d+$", "", name.split("~")[0])
    return base.replace("_other", "").replace("_", " ")


def load_edits(path):
    """Optional sidecar next to the scan: <scan>.edits.json, e.g.
    {"rotate_cw": 90,                           # turn the plan clockwise on the page (degrees)
     "remove": ["chair_*", "Wall_10"],          # names or glob patterns of RoomPlan nodes
     "retype": {"refrigerator_1": "storage_cabinet"},   # fix misidentified objects
     "add_objects": [{"type": "storage_cabinet", "rect": [x0, z0, x1, z1], "height": 0.9}],
     "cabinet_depth": {"base": 25.5, "upper": 12, "rooms": ["Kitchen"]},  # inches from wall
     "move": [{"nodes": ["Wall_2", "Door_0"], "by": [dx, dz]}],
     "add_walls": [{"from": [x, z], "to": [x, z], "label": "..."}],
     "add_doors": [{"from": [x, z], "to": [x, z], "label": "..."}],
     "add_openings": [{"from": [x, z], "to": [x, z], "label": "..."}],   # doorless doorways
     "add_floor": [[[x, z], [x, z], ...]],      # extra floor polygons
     "rooms": [{"at": [x, z], "name": "Bathroom"}],   # name the room containing a point
                                                      # ("no_split": true keeps it one room)
     "fixtures": [{"name": "Shower", "rect": [x0, z0, x1, z1]}],  # planned fixtures
     "labels": [{"at": [x, z], "text": "...", "rotation": 0}]}     # free-text notes
    add_doors entries may add "swing_toward": [x, z] to draw the swing (hinged at "from"), and
    "double": true for a pair of doors hinged at both jambs, "bifold": true for bifold doors.
    Coordinates are in the scan's own frame, in meters; walls are given by their centerline."""
    p = Path(path).with_suffix(".edits.json")
    return json.loads(p.read_text()) if p.exists() else {}


def wall_box(a, b, height, thickness=WALL_T):
    """A wall slab (default WALL_T thick) whose centerline runs from a to b (floor-plane [x, z],
    meters). Like RoomPlan walls, it extends WALL_T/2 past each end so corners close."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    v = b - a
    L = np.linalg.norm(v)
    box = trimesh.creation.box(extents=[L + WALL_T, height, thickness])
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


def scan_edits(path, variant=None):
    if variant:
        return json.loads(Path(path).with_suffix(f".{variant}.edits.json").read_text())
    return load_edits(path)


def process(path, outdir, variant=None):
    """Render one scan. With `variant`, use <scan>.<variant>.edits.json instead of the
    base edits and write <scan>.<variant>.png/svg/json (for comparing design options)."""
    edits = scan_edits(path, variant)
    nodes, swings, added = prepare(path, edits)
    stem = Path(path).stem + (f".{variant}" if variant else "")
    return render(nodes, swings, added, edits, stem, outdir, source=str(path))


def prepare(path, edits):
    """Load a scan and apply its edits; returns (nodes, door swings, names of added walls)."""
    nodes = load_nodes(path)
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
    # Retype scanned objects RoomPlan misidentified, e.g. {"refrigerator_1": "storage_cabinet"}
    for old_name, new_type in edits.get("retype", {}).items():
        if old_name not in nodes:
            print(f"  warning: retype target {old_name!r} not found")
            continue
        k = 0
        while f"{new_type}_retyped_{k}" in nodes:
            k += 1
        nodes[f"{new_type}_retyped_{k}"] = nodes.pop(old_name)
    # New furniture/cabinets: box footprints [x0, z0, x1, z1] with a RoomPlan-style type
    for i, ob in enumerate(edits.get("add_objects", [])):
        x0, z0, x1, z1 = ob["rect"]
        bottom, height = ob.get("bottom", 0.0), ob.get("height", 0.9)
        box = trimesh.creation.box(extents=[abs(x1 - x0), height, abs(z1 - z0)])
        box.apply_translation([(x0 + x1) / 2, bottom + height / 2, (z0 + z1) / 2])
        nodes[f"{ob['type']}_added_{i}"] = box
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
    added, swings = add_walls_and_doors(nodes, edits)
    return nodes, swings, added


def add_walls_and_doors(nodes, edits, tag="added"):
    added = set()
    for i, w in enumerate(edits.get("add_walls", [])):
        # "show_length": false hides the length label (connector pieces of a longer wall)
        name = f"Wall_{tag}_{i}" if w.get("show_length", True) else f"Wall_{tag}_nolabel_{i}"
        added.add(name)
        nodes[name] = wall_box(w["from"], w["to"], w.get("height", 2.5),
                               w.get("thickness_in", WALL_T / 0.0254) * 0.0254)
    swings = {}
    for i, d in enumerate(edits.get("add_doors", [])):
        nodes[f"Door_{tag}_{i}"] = opening_quad(d["from"], d["to"], d.get("height", 2.03))
        if "swing_toward" in d:  # hinge at "from" (both jambs if "double"), opening toward the point
            swings[f"Door_{tag}_{i}"] = {"hinge": d["from"], "other": d["to"],
                                         "toward": d["swing_toward"], "double": d.get("double", False),
                                         "bifold": d.get("bifold", False)}
    for i, o in enumerate(edits.get("add_openings", [])):  # doorless doorways / cased openings
        nodes[f"Opening_{tag}_{i}"] = opening_quad(o["from"], o["to"], o.get("height", 2.03))
    return added, swings


def translate_edits(edits, dx, dz):
    """Shift the drawing-level parts of a scan's edits (used when combining scans)."""
    sh = lambda p: [p[0] + dx, p[1] + dz]
    out = {}
    out["rooms"] = [dict(r, at=sh(r["at"]), **({"label_at": sh(r["label_at"])} if "label_at" in r else {}))
                    for r in edits.get("rooms", [])]
    out["add_floor"] = [[sh(p) for p in poly] for poly in edits.get("add_floor", [])]
    out["fixtures"] = [dict(f, rect=[f["rect"][0] + dx, f["rect"][1] + dz, f["rect"][2] + dx, f["rect"][3] + dz])
                       for f in edits.get("fixtures", [])]
    out["labels"] = [dict(l, at=sh(l["at"])) for l in edits.get("labels", [])]
    out["room_dividers"] = [dict(d, **{"from": sh(d["from"]), "to": sh(d["to"])})
                            for d in edits.get("room_dividers", [])]
    return out


def process_plan(plan_path, outdir):
    """Render several scans together on one plan. plans/<name>.json:
    {"title": "...",
     "parts": [{"scan": "scans/a.glb"},                               # its own edits apply
               {"scan": "scans/c.glb", "edits": "plans/v1/c.edits.json"},  # or a frozen copy
               {"scan": "scans/b.glb", "variant": "opt", "offset": [dx, dz]}],
     "add_walls": [{"from": [x, z], "to": [x, z], "thickness_in": 4, "show_length": false}],
     "room_dividers": [{"from": [x, z], "to": [x, z]}],   # open boundary between rooms (dashed;
                                                          # "hidden": true to separate without a line)
     "remove": ["Wall_3~1"],                              # node names get ~<part index>
     "scan_labels": false,                                # drop the scans' own text notes
     "rooms"/"labels"/...: as in a scan's edits, in plan coordinates}
    Offsets are applied after each scan's own edits (including its rotate_cw)."""
    plan = json.loads(Path(plan_path).read_text())
    nodes, swings, added = {}, {}, set()
    draw = {"title": plan.get("title", Path(plan_path).stem), "rooms": [], "add_floor": [],
            "fixtures": [], "labels": [], "room_dividers": []}
    cab = None
    for i, part in enumerate(plan["parts"]):
        # A part can point at its own frozen copy of the scan's edits ("edits": path), so a saved
        # version of a plan doesn't change when the scan's working edits do.
        e = (json.loads(Path(part["edits"]).read_text()) if part.get("edits")
             else scan_edits(part["scan"], part.get("variant")))
        pn, ps, pa = prepare(part["scan"], e)
        dx, dz = part.get("offset", [0, 0])
        T = trimesh.transformations.translation_matrix([dx, 0, dz])
        tag = f"~{i}"
        for n, m in pn.items():
            m.apply_transform(T)
            nodes[n + tag] = m
        sh = lambda p: [p[0] + dx, p[1] + dz]
        for n, sw in ps.items():
            swings[n + tag] = {k: (sh(v) if isinstance(v, list) else v) for k, v in sw.items()}
        added |= {n + tag for n in pa}
        for k, v in translate_edits(e, dx, dz).items():
            if k == "labels" and not plan.get("scan_labels", True):
                continue  # notes like "open to hallway" may no longer apply once joined
            draw[k] += v
        if e.get("cabinet_depth"):
            cab = dict(e["cabinet_depth"]) if cab is None else \
                dict(cab, rooms=cab.get("rooms", []) + e["cabinet_depth"].get("rooms", []))
    if cab:
        draw["cabinet_depth"] = cab
    for pat in plan.get("remove", []):
        for n in [n for n in nodes if fnmatch.fnmatchcase(n, pat)]:
            del nodes[n]
    pa, ps = add_walls_and_doors(nodes, plan, tag="plan")
    added |= pa
    swings.update(ps)
    for k in ("rooms", "add_floor", "fixtures", "labels", "room_dividers"):
        draw[k] += plan.get(k, [])
    return render(nodes, swings, added, draw, Path(plan_path).stem, outdir, source=str(plan_path))


def render(nodes, swings, added, edits, stem, outdir, source=""):
    kind = lambda n: n.split("_")[0]

    floors = {n: m for n, m in nodes.items() if kind(n) == "Floor"}
    walls = {n: m for n, m in nodes.items() if kind(n) in ("Wall", "Joint")}
    doors = {n: m for n, m in nodes.items() if kind(n) == "Door"}
    openings = {n: m for n, m in nodes.items() if kind(n) == "Opening"}  # doorless doorways
    windows = {n: m for n, m in nodes.items() if kind(n) == "Window"}
    ceilings = {n: m for n, m in nodes.items() if kind(n) == "Ceiling"}
    objects = {n: m for n, m in nodes.items() if n[0].islower()}

    ceiling_hs = sorted(m.bounds.mean(0)[1] for m in ceilings.values())
    ceiling_h = ceiling_hs[-1] if ceiling_hs else None

    # Each wall is a straight slab; using its oriented rectangle squares off the mitered
    # ends RoomPlan leaves where a wall met one that has since been removed.
    wall_geom = unary_union([footprint(m).minimum_rotated_rectangle
                             for m in walls.values() if footprint(m) is not None])

    furn = [footprint(m) for n, m in objects.items() if m.bounds[0][1] <= 1.2]
    furn += [_rect(*fx["rect"]) for fx in edits.get("fixtures", [])]  # planned fixtures too
    furn_union = unary_union([f.convex_hull for f in furn if f is not None]) if furn else None

    floor_polys = {n: footprint(m) for n, m in floors.items()}
    extra_floor = [Polygon(f) for f in edits.get("add_floor", [])]
    floor_all = unary_union(list(floor_polys.values()) + extra_floor).buffer(1e-4).buffer(-1e-4)

    # Page size grows with the drawing so text stays readable on whole-floor plans
    fb = floor_all.bounds
    fig_in = float(np.clip(0.9 * max(fb[2] - fb[0], fb[3] - fb[1]), 10, 22))
    fig, ax = plt.subplots(figsize=(fig_in, fig_in))
    ax.set_aspect("equal")
    ax.axis("off")

    summary = {"source": source, "ceiling_height": None, "rooms": [], "walls": [],
               "doors": [], "windows": [], "objects": []}
    if ceiling_h:
        summary["ceiling_height"] = {"m": round(ceiling_h, 2), "ft_in": ft_in(ceiling_h)}

    # Rooms: the floor split up by the walls. Each region is grown back out to the wall
    # centerlines (how RoomPlan measures rooms) and named after the scanned floor it
    # mostly sits on, unless the edits name it.
    divider_lines = [LineString([d["from"], d["to"]]) for d in edits.get("room_dividers", [])]
    cut = unary_union([wall_geom] + [l.buffer(0.01, cap_style=2) for l in divider_lines])
    regions = [r for r in polys_of(floor_all.difference(cut)) if r.area > 0.3]
    rooms = []
    dividers = []
    nice = lambda n: n.split("~")[0].replace("Floor_", "").replace("_", " ")
    for r in regions:
        full = r.buffer(WALL_T / 2, join_style=2).intersection(floor_all)
        full = max(polys_of(full), key=lambda q: q.area)
        # Open plan: RoomPlan scanned two or more whole rooms that no wall separates
        # (e.g. kitchen + living room). Split the space along their floor boundary.
        whole = [n for n, f in floor_polys.items()
                 if f.area > 0.5 and f.intersection(full).area >= 0.9 * f.area]
        keep_whole = any(spec.get("no_split") and r.contains(Point(spec["at"]))
                         for spec in edits.get("rooms", []))  # a named room that's one space
        if len(whole) >= 2 and not keep_whole:
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

    room_label_boxes = []
    room_colors = ["#f3ede2", "#e6eef2", "#eef2e6", "#f2e6ee", "#eae6f2", "#f2efe6"]
    total_area = 0
    # Colour rooms so that neighbours (rooms within a wall's thickness of each other) differ:
    # greedy colouring, biggest rooms first.
    ordered = sorted(rooms, key=lambda rm: rm[0])
    color_of = {}
    for rm in sorted(ordered, key=lambda rm: -rm[1].area):
        near = {color_of[o[0]] for o in ordered
                if o[0] in color_of and o is not rm and o[1].distance(rm[1]) < 0.3}
        color_of[rm[0]] = next((c for c in range(len(room_colors)) if c not in near),
                               len(color_of) % len(room_colors))
    for i, (label, fp, inner) in enumerate(ordered):
        ax.add_patch(poly_patch(fp, fc=room_colors[color_of[label]], ec="none", zorder=1))
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
        fs = opt.get("label_size", 10 if area >= 5 else 8)
        ax.text(c.x, c.y, text, ha="center", va="center", fontsize=fs,
                zorder=6, fontweight="bold", color="#333")
        lines = text.split("\n")  # remember the label's footprint so wall labels can avoid it
        mpp = (max(fb[2] - fb[0], fb[3] - fb[1]) + 1.0) / (fig_in * 72)
        hw = max(len(t) for t in lines) * 0.62 * fs * mpp / 2
        hh = len(lines) * 1.3 * fs * mpp / 2
        room_label_boxes.append(_rect(c.x - hw, c.y - hh, c.x + hw, c.y + hh))
        summary["rooms"].append({"name": label, "width_m": round(w, 3), "depth_m": round(d, 3),
                                 "width_ft_in": ft_in(w), "depth_ft_in": ft_in(d),
                                 "area_m2": round(area, 2), "area_sqft": round(sqft(area), 1),
                                 "rectangular": bool(rect)})
    for d, l in zip(edits.get("room_dividers", []), divider_lines):  # open boundaries between rooms
        if d.get("hidden"):
            continue  # separates the rooms without drawing anything (e.g. across a plain opening)
        (ax_, az), (bx, bz) = l.coords
        ax.plot([ax_, bx], [az, bz], color="#888", lw=1, ls=(0, (6, 4)), zorder=1.5)
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
    m_per_pt = (max(fb[2] - fb[0], fb[3] - fb[1]) + 1.0) / (fig_in * 72)
    def fits(text, size, poly):
        mrr = poly.minimum_rotated_rectangle
        minx, minz, maxx, maxz = mrr.bounds
        tw = (len(text) * 0.62 + 1) * size * m_per_pt  # same estimate as the overlap check
        th = 1.3 * size * m_per_pt
        if tw <= (maxx - minx) * 0.95 and th <= (maxz - minz) * 0.95:
            return 0
        if tw <= (maxz - minz) * 0.95 and th <= (maxx - minx) * 0.95:
            return 90
        return None
    # Rooms marked "no_furniture" (e.g. a chimney box) don't show scanned furniture spilling in
    no_furn = unary_union([rm[1] for rm in rooms
                           if label_opts.get(rm[0], {}).get("no_furniture")]) if rooms else None
    # Pass 1: footprints and labels for every object
    items = []
    for name, m in objects.items():
        fp = footprint(m)
        if fp is None:
            continue
        hull = fp.convex_hull.intersection(floor_all)
        if no_furn is not None and not no_furn.is_empty:
            hull = hull.difference(no_furn)
        if hull.is_empty:
            continue
        bottom = float(m.bounds[0][1])
        kind_ = friendly_label(name, bottom, hull.distance(wall_geom) > 0.15,
                               top=float(m.bounds[1][1]))
        if kind_ is None:  # e.g. cooktop sitting on the oven
            continue
        if kind_ in SQUARED:
            hull = square_up(hull, wall_geom).intersection(floor_all)
        items.append({"name": name, "m": m, "kind": kind_, "hull": hull, "bottom": bottom})

    # Pass 2 (optional): standard cabinet depths measured from the wall behind each unit,
    # e.g. "cabinet_depth": {"base": 25.5, "upper": 12, "rooms": ["Kitchen"]} (inches).
    cd = edits.get("cabinet_depth")
    if cd:
        IN_ = 0.0254
        depth_for = {"base cab": cd.get("base"), "tall cab": cd.get("tall", cd.get("base")),
                     "DW": cd.get("base"), "range": cd.get("base"), "upper cab": cd.get("upper")}
        zones = [rm[1] for rm in rooms if not cd.get("rooms") or rm[0] in cd["rooms"]]
        zone = unary_union(zones) if zones else None
        adjusted = []
        for it in items:
            d = depth_for.get(it["kind"])
            if d and zone is not None and zone.contains(it["hull"].centroid):
                new_rect = set_depth(it["hull"], wall_geom, d * IN_)
                if new_rect is not None:
                    it["hull"] = new_rect
                    adjusted.append(it)
        # close small gaps along each run (to neighbouring cabinets or a wall), base and upper
        # cabinets separately
        for upper in (False, True):
            group = [it for it in adjusted if (it["bottom"] > 1.2) == upper]
            for it in group:
                others = unary_union([wall_geom] + [o["hull"] for o in group if o is not it])
                it["hull"] = close_gaps(it["hull"], others, wall_geom)

    uppers = []
    placed = []  # label boxes already drawn, to avoid overlapping text
    for it in sorted(items, key=lambda it: it["hull"].area):  # label small items first
        name, m, kind_, hull, bottom = it["name"], it["m"], it["kind"], it["hull"], it["bottom"]
        if bottom > 1.2:  # wall-hung (upper cabinets, shelves): draw after base units, dashed
            uppers.append((hull, kind_))
        else:
            for hp in polys_of(hull):
                ax.add_patch(poly_patch(hp, fc="#d9d9d9", ec="#999", lw=0.8, zorder=2, alpha=0.8))
            size = 6.5
            rot = fits(kind_, size, hull)
            if rot is None:  # try a smaller font before giving up on the label
                size = 5.5
                rot = fits(kind_, size, hull)
            if rot is not None:
                c = hull.centroid
                tw = (len(kind_) * 0.62 + 1) * size * m_per_pt / 2  # a little padding
                th = 1.3 * size * m_per_pt / 2
                hw, hh = (tw, th) if rot == 0 else (th, tw)
                box = Polygon([(c.x - hw, c.y - hh), (c.x + hw, c.y - hh),
                               (c.x + hw, c.y + hh), (c.x - hw, c.y + hh)])
                if not any(box.intersects(b) for b in placed):
                    placed.append(box)
                    ax.text(c.x, c.y, kind_, ha="center", va="center", fontsize=size,
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
        if fx.get("shape") == "bed":  # two pillows at the head end ("head": n/s/e/w)
            head = fx.get("head", "n")
            xa, xb, za, zb = min(x0, x1), max(x0, x1), min(z0, z1), max(z0, z1)
            pd, gap = 0.30, 0.06  # pillow depth, margins
            if head in ("n", "s"):
                zp = za + gap if head == "n" else zb - gap - pd
                half = (xb - xa) / 2
                for k in range(2):
                    px = xa + gap + k * half
                    ax.add_patch(poly_patch(_rect(px, zp, px + half - 2 * gap, zp + pd),
                                            fc="white", ec="#777", lw=0.7, zorder=3.5))
                zl = zp + pd + gap if head == "n" else zp - gap  # top of the folded-back sheet
                ax.plot([xa, xb], [zl + (0.25 if head == "n" else -0.25)] * 2, color="#999",
                        lw=0.7, zorder=3.5)
            else:
                xp = xa + gap if head == "w" else xb - gap - pd
                half = (zb - za) / 2
                for k in range(2):
                    pz = za + gap + k * half
                    ax.add_patch(poly_patch(_rect(xp, pz, xp + pd, pz + half - 2 * gap),
                                            fc="white", ec="#777", lw=0.7, zorder=3.5))
        if fx.get("shape") == "stairs":  # treads across the run, arrow pointing up ("up": n/s/e/w)
            up = fx.get("up", "e")
            xa, xb, za, zb = min(x0, x1), max(x0, x1), min(z0, z1), max(z0, z1)
            tread = fx.get("tread_in", 10) * 0.0254
            if up in ("e", "w"):
                for xt in np.arange(xa + tread, xb - 1e-6, tread):
                    ax.plot([xt, xt], [za, zb], color="#999", lw=0.7, zorder=3.5)
                zc = (za + zb) / 2
                (sx, ex) = (xa + 0.15, xb - 0.15) if up == "e" else (xb - 0.15, xa + 0.15)
                ax.annotate("", xy=(ex, zc), xytext=(sx, zc), zorder=3.6,
                            arrowprops=dict(arrowstyle="-|>", color="#555", lw=1.1))
            else:
                for zt in np.arange(za + tread, zb - 1e-6, tread):
                    ax.plot([xa, xb], [zt, zt], color="#999", lw=0.7, zorder=3.5)
                xc = (xa + xb) / 2
                (sz, ez) = (zb - 0.15, za + 0.15) if up == "n" else (za + 0.15, zb - 0.15)
                ax.annotate("", xy=(xc, ez), xytext=(xc, sz), zorder=3.6,
                            arrowprops=dict(arrowstyle="-|>", color="#555", lw=1.1))
        if fx.get("shape") == "closet":  # reach-in/hanging closet: dashed rod down the middle
            xa, xb, za, zb = min(x0, x1), max(x0, x1), min(z0, z1), max(z0, z1)
            if (xb - xa) >= (zb - za):
                ax.plot([xa + 0.05, xb - 0.05], [(za + zb) / 2] * 2, color="#888", lw=0.8,
                        ls=(0, (4, 3)), zorder=3.5)
            else:
                ax.plot([(xa + xb) / 2] * 2, [za + 0.05, zb - 0.05], color="#888", lw=0.8,
                        ls=(0, (4, 3)), zorder=3.5)
        if fx.get("shape") == "toilet" and fx.get("front", "w") in ("n", "s"):
            from matplotlib.patches import Ellipse
            w, d = abs(x1 - x0), abs(z1 - z0)
            tank = 7 * IN
            za, zb = min(z0, z1), max(z0, z1)
            front = fx["front"]
            bz = (za + (0 if front == "n" else tank) + zb - (tank if front == "n" else 0)) / 2
            ax.add_patch(Ellipse(((x0 + x1) / 2, bz), w - 0.04, d - tank - 0.02, fc="white",
                                 ec="#555", lw=0.8, zorder=3.5))
            tz = zb - tank if front == "n" else za + tank
            ax.plot([x0, x1], [tz, tz], color="#555", lw=0.8, zorder=3.5)
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
                color="#333", zorder=4.5, rotation=fx.get("text_rotation", 0),
                bbox=dict(fc="white", ec="none", pad=1.0) if fx.get("shape") == "stairs" else None)
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
    wall_label_boxes = []
    by_length = lambda kv: -max((kv[1].bounds[1] - kv[1].bounds[0])[[0, 2]])
    for name, m in sorted(walls.items(), key=by_length):  # longest walls get labels first
        if not name.startswith("Wall"):
            continue
        ext = m.bounds[1] - m.bounds[0]
        ctr = m.bounds.mean(0)
        length = max(ext[0], ext[2]) - WALL_T
        summary["walls"].append({"name": name, "added": name in added, "length_m": round(float(length), 3),
                                 "length_ft_in": ft_in(length),
                                 "height_m": round(float(ext[1]), 2)})
        if length < 0.3 or "_nolabel_" in name:
            continue
        fpw = footprint(m)
        others = unary_union([footprint(o) for n2, o in walls.items() if n2 != name and n2.startswith("Wall")])
        if fpw is not None and not others.is_empty and fpw.difference(others).area < 0.2 * fpw.area:
            continue  # buried inside a thicker wall (e.g. a shared wall on a combined plan)
        horiz = ext[0] >= ext[2]
        off = 0.22
        txt = ft_in(length)
        half_w = (len(txt) * 0.62 + 1) * 7.5 * m_per_pt / 2
        half_h = 1.3 * 7.5 * m_per_pt / 2
        # Default side is away from the plan's center; flip to the other side of the wall if
        # that collides with another label (wall or furniture), skip if both sides do.
        sign = 1 if (ctr[2] > cz if horiz else ctr[0] > cx) else -1
        box = None
        for sgn in (sign, -sign):
            if horiz:
                lx, lz = ctr[0], ctr[2] + sgn * off
                cand = _rect(lx - half_w, lz - half_h, lx + half_w, lz + half_h)
            else:
                lx, lz = ctr[0] + sgn * off, ctr[2]
                cand = _rect(lx - half_h, lz - half_w, lx + half_h, lz + half_w)
            if not any(cand.intersects(b) for b in wall_label_boxes + placed + room_label_boxes):
                box = cand
                break
        if box is None:
            continue
        wall_label_boxes.append(box)
        ax.text(lx, lz, txt, ha="center", va="center", fontsize=7.5, color="#0b5394",
                rotation=0 if horiz else 90, zorder=7)

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
            if style == "door":
                ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw_gap, ls=(0, (2, 1.5)), zorder=5)
            for p in ((a, b) if style == "door" else ()):  # jamb ticks; doorless openings are a plain gap
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
        kind_txt = "bifold" if swings.get(name, {}).get("bifold") else "door"
        ax.text(mid[0], mid[1], f"{kind_txt} {ft_in(L)}", fontsize=6, color="#b45f06", ha="center",
                va="bottom", zorder=8, rotation=rot, rotation_mode="anchor")
        if name in swings:  # draw each leaf open at 90 degrees and its swing arc
            sw = swings[name]
            A, B = np.array(sw["hinge"], float), np.array(sw["other"], float)
            toward = np.array(sw["toward"], float)
            if sw.get("bifold"):  # pairs of folding panels: a shallow zig-zag toward the room
                v = B - A
                n = np.array([-v[1], v[0]]) / np.linalg.norm(v)
                if np.dot(n, toward - A) < 0:
                    n = -n
                depth = np.linalg.norm(v) / 8
                for a, b in ((A, (A + B) / 2), (B, (A + B) / 2)):  # each half folds from its jamb
                    mid = (a + b) / 2 + n * depth
                    ax.plot([a[0], mid[0], b[0]], [a[1], mid[1], b[1]], color="#b45f06", lw=1.0, zorder=5)
                continue
            leaves = [(A, B)] if not sw.get("double") else [(A, (A + B) / 2), (B, (A + B) / 2)]
            for hinge, other in leaves:
                v = other - hinge
                r = np.linalg.norm(v)
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
                ax.plot(hinge[0] + r * np.cos(t), hinge[1] + r * np.sin(t), color="#b45f06",
                        lw=0.6, ls=(0, (3, 2)), zorder=5)
    for name, m in sorted(openings.items()):
        L, mid, bottom, h, rot = opening(m, "#b45f06", 1.0, "opening")
        summary.setdefault("openings", []).append({"name": name, "width_m": round(float(L), 3),
                                                   "width_ft_in": ft_in(L)})
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

    title = edits.get("title", stem) + f"  —  {summary['total_area_sqft']:.0f} sq ft"
    if ceiling_h:
        if ceiling_hs[-1] - ceiling_hs[0] > 0.02:  # combined plans: rooms differ
            title += f"  ·  ceilings {ft_in(ceiling_hs[0])}–{ft_in(ceiling_hs[-1])}"
        else:
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
    ap.add_argument("glb", nargs="+", help="scan .glb files and/or combined plans/*.json")
    ap.add_argument("--out", default="floorplans")
    args = ap.parse_args()
    for p in args.glb:
        if p.endswith(".json"):  # a combined plan (plans/*.json)
            s = process_plan(p, Path(args.out))
            print(f"{p}: {s['total_area_sqft']} sq ft, "
                  f"rooms={[(r['name'], r['area_sqft']) for r in s['rooms']]}")
            continue
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
