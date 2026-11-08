"""Living Room game-day layouts L1, L2 on top of Primary Suite P3 (seat 10 facing the TV).
Writes plans/living-room-l{1,2}.json.

TV on the Living Room side of the Utility Closet's back wall (right of the fireplace).
Living Room geometry (wall faces, metres; x east, z south):
  north (TV / fireplace) wall z 0.824, fireplace box x -6.987..-5.383 projecting to z 1.031
  hall from the Dining room / Primary Suite / bath opens on the north wall at x -3.18..-1.96
  west wall x -8.26 with the Entry opening at z 2.79..3.93
  south wall z 5.516 west of x -3.73 (front-of-house jog), z 4.644 east of it
  east part (old Room 1A) below the bath: x -1.96..0.073, z 1.83..4.644, Bedroom 2 door on its east wall
"""
import json, copy
IN = 0.0254
FT = 0.3048
base = json.load(open('plans/primary-suite-p3.json'))
r4 = lambda v: [round(x, 4) for x in v]
f = lambda m: round(m / IN, 1)
WALL_N = 0.824
FP_FRONT, FP_E = 1.031, -5.383
WALL_N_END = -3.28                 # north wall face ends at the hall opening
S_WEST, S_EAST, JOG_X = 5.516, 4.644, -3.73
TVW = 74.4 * IN                    # 85" TV
TVX = -4.33                        # centred on the wall between the fireplace box and the hall opening
SEAT_D = 39 * IN                   # sectional depth


def new(title):
    pl = copy.deepcopy(base); pl["title"] = title
    pl["notes"] = title + ". " + pl["notes"]
    for r in pl["rooms"]:
        if r["name"] == "Living Room":
            r["label_at"] = [-7.3, 4.85]; r["compact"] = True
    tv = [TVX - TVW / 2, WALL_N, TVX + TVW / 2, WALL_N + 3 * IN]
    assert tv[0] > FP_E and tv[2] < WALL_N_END
    pl["fixtures"].append(dict(name="TV 85\"", rect=r4(tv), shape="tv"))
    return pl


def fx(pl, name, rect, **k): pl["fixtures"].append(dict(name=name, rect=r4(rect), **k))
def ft(m): return round(m / FT, 1)


def l1():
    """U-shaped sectional (9) + swivel chair in the old 1A pocket (10)."""
    pl = new("Living Room – L1 (game day: U sectional, seats 10)")
    back = 4.55
    w = 168 * IN                                   # 39" corner + 3 × 30" + 39" corner
    x0, x1 = TVX - w / 2, TVX + w / 2
    front = back - SEAT_D
    ret_n = 2.0                                    # returns stop ~38" short of the fireplace front
    fx(pl, "U sectional", [x0, front, x1, back], shape="sofa", back="s", arms=False, seats=5)
    fx(pl, "", [x0, ret_n, x0 + SEAT_D, front], shape="sofa", back="w", arms=False, seats=2)
    fx(pl, "", [x1 - SEAT_D, ret_n, x1, front], shape="sofa", back="e", arms=False, seats=2)
    ott = [TVX - 30 * IN, (ret_n + front) / 2 - 18 * IN, TVX + 30 * IN, (ret_n + front) / 2 + 18 * IN]
    fx(pl, "Ottoman 60×36", ott)
    sw = [-1.45, 2.95, -1.45 + 34 * IN, 2.95 + 34 * IN]
    fx(pl, "Swivel", sw, shape="chair", back="e")
    json.dump(pl, open('plans/living-room-l1.json', 'w'), indent=2)
    print(f"L1  back row to TV {ft(front - WALL_N)}-{ft(back - WALL_N)} ft  returns to fireplace front {f(ret_n - FP_FRONT)} in"
          f"  west return to west wall {f(x0 - (-8.26))} in  east return to hall opening x {round(x1, 2)} (hall -3.18..-1.96)"
          f"  ottoman to seats {f(ott[0] - (x0 + SEAT_D))} / {f(front - ott[3])} in"
          f"  swivel to TV {ft(((sw[0] - TVX) ** 2 + (sw[1] - WALL_N) ** 2) ** .5)} ft")


def l2():
    """L sectional (6) + bar ledge with 4 stools behind it (10) + optional swivel (11)."""
    pl = new("Living Room – L2 (game day: sectional + bar ledge, seats 10–11)")
    front = 3.30
    back = front + SEAT_D
    x0, x1 = -6.05, -2.70                           # 132" run, corner on the east end
    ret_n = 1.90
    fx(pl, "Sectional", [x0, front, x1, back], shape="sofa", back="s", arms=False, seats=4)
    fx(pl, "", [x1 - SEAT_D, ret_n, x1, front], shape="sofa", back="e", arms=False, seats=2)
    tbl = [(x0 + x1 - SEAT_D) / 2 - 24 * IN, front - 18 * IN - 30 * IN,
           (x0 + x1 - SEAT_D) / 2 + 24 * IN, front - 18 * IN]
    fx(pl, "Coffee table", tbl)
    lx0, lx1 = -6.35, JOG_X - 0.10                  # ledge stays west of the jog wall
    ledge = [lx0, back, lx1, back + 12 * IN]
    fx(pl, "Bar ledge 42\" high", ledge)
    n = 4; sp = (lx1 - lx0) / n; d = 16 * IN
    for k in range(n):
        cx = lx0 + sp * (k + .5); cz = ledge[3] + 4 * IN + d / 2
        fx(pl, "", [cx - d / 2, cz - d / 2, cx + d / 2, cz + d / 2], shape="stool")
    sw = [-1.45, 2.95, -1.45 + 34 * IN, 2.95 + 34 * IN]
    fx(pl, "Swivel", sw, shape="chair", back="e")
    json.dump(pl, open('plans/living-room-l2.json', 'w'), indent=2)
    print(f"L2  sofa to TV {ft(front - WALL_N)}-{ft(back - WALL_N)} ft  stools to TV ~{ft(ledge[3] + 12 * IN - WALL_N)} ft"
          f"  stool spacing {f(sp)} in  stool back edge to south wall {f(S_WEST - (ledge[3] + 4 * IN + d))} in"
          f"  return to hall/TV wall {f(ret_n - WALL_N)} in  sofa west end to west wall {f(x0 + 8.26)} in"
          f"  table to sofa {f(front - tbl[3])} in")


l1(); l2()
