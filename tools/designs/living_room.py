"""Living Room game-day layouts on top of Primary Suite P3, spread across the room's full width.
Writes plans/living-room-l3.json (wide arc) and plans/living-room-l4.json (long sectional + angled wing).

TV (85") on the Living Room side of the Utility Closet's back wall, right of the fireplace.
Living Room geometry (wall faces, metres; x east, z south):
  north (TV / fireplace) wall z 0.824, fireplace box x -6.987..-5.383 projecting to z 1.031
  hall from the Dining room / Primary Suite / bath opens on the north wall at x -3.18..-1.96
  west wall x -8.26 with the Entry opening at z 2.79..3.93
  south wall z 5.516 west of x -3.73 (front-of-house jog), z 4.644 east of it
  east part (old Room 1A) below the bath (z 1.83): x -1.96..0.073; Bedroom 2 door on its east wall z ~1.9..2.8
"Angle" turns a piece clockwise on the plan about its centre (+ faces it north-east, - north-west).
"""
import json, copy, math
from shapely.geometry import Polygon, box
from shapely import affinity
IN = 0.0254
FT = 0.3048
base = json.load(open('plans/primary-suite-p3.json'))
r4 = lambda v: [round(x, 4) for x in v]
f = lambda m: round(m / IN, 1)
WALL_N = 0.824
TVW = 74.4 * IN
TVX = -4.33                                       # clears the fireplace box, ends before the hall opening
TV = (TVX, WALL_N + 0.05)
D = 38 * IN                                       # sofa depth
# floor the furniture must stay inside (Living Room, wall faces), and areas to keep clear
ROOM = Polygon([(-8.26, 1.031), (-3.28, 1.031), (-3.28, 0.824), (-1.96, 0.824), (-1.96, 1.83),
                (0.073, 1.83), (0.073, 4.644), (-3.73, 4.644), (-3.73, 5.516), (-8.26, 5.516)])
KEEP_CLEAR = {"entry landing": box(-8.26, 2.79, -7.36, 3.93),        # 3 ft in from the entry opening
              "Bedroom 2 door": box(-0.69, 1.83, 0.073, 2.85),      # 30" in front of the door
              "hall mouth": box(-3.18, 0.824, -1.96, 1.74)}


def new(title):
    pl = copy.deepcopy(base); pl["title"] = title
    pl["notes"] = title + ". " + pl["notes"]
    for r in pl["rooms"]:
        if r["name"] == "Living Room":
            r["label_at"] = [-5.9, 1.75]; r["compact"] = True
    pl["fixtures"].append(dict(name="TV 85\"", rect=r4([TVX - TVW / 2, WALL_N, TVX + TVW / 2, WALL_N + 3 * IN]), shape="tv"))
    pl["_pieces"] = []
    return pl


def piece(pl, name, cx, cz, w, d, angle=0, seats=0, **k):
    """A seat centred at (cx, cz), w wide x d deep, facing north before turning by angle."""
    rect = [cx - w / 2, cz - d / 2, cx + w / 2, cz + d / 2]
    fx = dict(name=name, rect=r4(rect), **k)
    if angle: fx["angle"] = angle
    if seats: fx["seats"] = seats
    pl["fixtures"].append(fx)
    poly = affinity.rotate(box(*rect), angle, origin=(cx, cz))
    pl["_pieces"].append((name or "piece", poly, seats, cx, cz, angle))
    return poly


def report(pl, tag):
    polys = [p for _, p, *_ in pl["_pieces"]]
    total = 0
    for i, (name, p, seats, cx, cz, a) in enumerate(pl["_pieces"]):
        if not ROOM.buffer(1e-6).contains(p): print(f"  !! {tag}: {name} leaves the room", [round(v, 2) for v in p.bounds])
        for kname, kc in KEEP_CLEAR.items():
            if p.intersects(kc): print(f"  !! {tag}: {name} blocks the {kname}", [round(v, 2) for v in p.bounds])
        for q in polys[i + 1:]:
            if p.intersection(q).area > 1e-4: print(f"  !! {tag}: {name} overlaps another piece")
        if seats:
            total += seats
            dx, dz = TV[0] - cx, cz - TV[1]
            print(f"  {tag} {name:14s} seats {seats}  to TV {math.hypot(dx, dz) / FT:4.1f} ft  "
                  f"off the screen's axis {abs(math.degrees(math.atan2(dx, dz))):3.0f}°")
    print(f"  {tag} total seats {total}")
    del pl["_pieces"]


def fits(pl, poly, gap=4 * IN):
    if not ROOM.buffer(1e-6).contains(poly): return False
    if any(poly.intersects(k) for k in KEEP_CLEAR.values()): return False
    return all(poly.distance(q) >= gap for _, q, *_ in pl["_pieces"])


def place(pl, name, w, d, xs, zs, score, turn=1.0, **k):
    """Best spot in the search window for a seat turned toward the TV (turn = share of the full turn)."""
    best = None
    for cx in xs:
      for cz in zs:
        for t in (1.0, 0.85, 0.7, 0.55):
            a = round(math.degrees(math.atan2(TV[0] - cx, cz - TV[1])) * t * turn)
            poly = affinity.rotate(box(cx - w / 2, cz - d / 2, cx + w / 2, cz + d / 2), a, origin=(cx, cz))
            if fits(pl, poly):
                sc = score(cx, cz, poly) + 0.4 * (1 - t)
                if best is None or sc < best[0]: best = (sc, cx, cz, a)
    if not best:
        print(f"  !! no spot for {name}"); return None
    _, cx, cz, a = best
    return piece(pl, name, cx, cz, w, d, angle=a, **k)


rng = lambda a, b, st=0.025: [round(a + st * i, 4) for i in range(int(round((b - a) / st)) + 1)]
off_axis = lambda cx, cz: abs(math.atan2(TV[0] - cx, cz - TV[1]))


def wing(pl, name, T, side, w, a, **k):
    """A sofa turned a degrees whose inner front corner sits at point T (the end of the piece it continues).
    side "e": continues east and turns to face north-west (a < 0); side "w": mirror image."""
    vx, vz = (-w / 2 if side == "e" else w / 2), -D / 2
    r = math.radians(a)
    rx, rz = vx * math.cos(r) - vz * math.sin(r), vx * math.sin(r) + vz * math.cos(r)
    return piece(pl, name, T[0] - rx, T[1] - rz, w, D, angle=a, **k)


def l3():
    """Wall to wall: two long sofas with their backs to the front windows, stepping with the front-of-house jog."""
    pl = new("Living Room – L3 (wall to wall: two long sofas, seats 10–11)")
    S_W, S_E, JOG = 5.516, 4.644, -3.73
    w0, w1 = -8.20, JOG - 0.10                    # west: 171" sectional, 6 seats
    piece(pl, "Sofa 171\"", (w0 + w1) / 2, S_W - D / 2, w1 - w0, D, seats=6, shape="sofa", back="s")
    e0, e1 = JOG + 0.05, -0.30                    # east: 132" sofa, 4-5 seats
    piece(pl, "Sofa 132\"", (e0 + e1) / 2, S_E - D / 2, e1 - e0, D, seats=4, shape="sofa", back="s")
    piece(pl, "Coffee table", -5.95, S_W - D - 18 * IN - 13 * IN, 54 * IN, 26 * IN)
    piece(pl, "Coffee table", -2.45, S_E - D - 18 * IN - 12 * IN, 42 * IN, 24 * IN)
    report(pl, "L3")
    json.dump(pl, open('plans/living-room-l3.json', 'w'), indent=2)


def l4():
    """Long sectional across the room + a wing turned toward the TV in the old 1A corner."""
    pl = new("Living Room – L4 (wide sectional + angled wing, seats 10)")
    x0, x1 = -7.18, -2.80                        # 172" run, 6 seats
    front = 4.60 - D
    piece(pl, "Sectional", (x0 + x1) / 2, front + D / 2, x1 - x0, D, seats=7, shape="sofa", back="s", arms=False)
    piece(pl, "", x0 - 3 * IN, front + D / 2, 6 * IN, D, shape="sofa", back="s", arms=False)   # west arm
    wing(pl, "Wing", (x1, front), "e", 78 * IN, -40, seats=3, shape="sofa", back="s", arms=False)
    piece(pl, "Coffee table", -6.0, front - 18 * IN - 13 * IN, 48 * IN, 26 * IN)
    piece(pl, "Coffee table", -4.1, front - 18 * IN - 13 * IN, 48 * IN, 26 * IN)
    report(pl, "L4")
    json.dump(pl, open('plans/living-room-l4.json', 'w'), indent=2)



def l5():
    """Theater: 4 recliners in front, 4 wall-hugger recliners on a 7" riser along the front window, 2 swivels in 1A."""
    pl = new("Living Room – L5 (theater: two rows of recliners, seats 10)")
    RW, RD = 36 * IN, 40 * IN
    z0 = 2.85
    for k in range(4):
        cx = TVX + (k - 1.5) * RW
        piece(pl, "", cx, z0 + RD / 2, RW, RD, seats=1, shape="chair", back="s")
    pl["fixtures"].insert(-4, dict(name="", rect=r4([TVX - 2 * RW - 0.02, z0 - 20 * IN, TVX + 2 * RW + 0.02, z0]),
                                   shape="rug"))                     # footrests out
    RW2 = 40 * IN
    rx0, rx1 = -8.22, -3.77
    riser = [rx0, 4.32, rx1, 5.516]
    pl["fixtures"].append(dict(name="", rect=r4(riser), shape="rug"))
    n = 4; gap = ((rx1 - rx0) - n * RW2) / (n + 1)
    for k in range(n):
        cx = rx0 + gap + RW2 / 2 + k * (RW2 + gap)
        piece(pl, "", cx, 5.516 - 0.03 - RD / 2, RW2, RD, seats=1, shape="chair", back="s")
    pl["labels"] = pl.get("labels", []) + [{"at": [-7.55, 4.18], "text": "7\" riser"},
                                           {"at": [TVX, 2.6], "text": "footrests out"}]
    for cx, cz in [(-1.55, 3.0), (-0.75, 3.85)]:
        piece(pl, "Swivel", cx, cz, 32 * IN, 32 * IN, angle=-45, seats=1, shape="chair", back="s")
    report(pl, "L5")
    json.dump(pl, open('plans/living-room-l5.json', 'w'), indent=2)


def l6():
    """Conversation: two 108" sofas facing each other off the TV wall, two swivel chairs closing the far end."""
    pl = new("Living Room – L6 (facing sofas + swivels, seats 10)")
    for r in pl["rooms"]:
        if r["name"] == "Living Room": r["label_at"] = [-7.4, 4.85]
    L = 108 * IN; zc = 1.85 + L / 2
    gapx = 100 * IN                                   # front to front
    piece(pl, "Sofa 108\"", TVX - gapx / 2 - D / 2, zc, D, L, seats=4, shape="sofa", back="w")
    piece(pl, "Sofa 108\"", TVX + gapx / 2 + D / 2, zc, D, L, seats=4, shape="sofa", back="e")
    for dx in (-0.47, 0.47):
        piece(pl, "Swivel", TVX + dx, 4.15, 32 * IN, 32 * IN, seats=1, shape="chair", back="s")
    piece(pl, "Coffee table", TVX, 2.95, 30 * IN, 60 * IN)
    report(pl, "L6")
    json.dump(pl, open('plans/living-room-l6.json', 'w'), indent=2)


l3(); l4(); l5(); l6()
