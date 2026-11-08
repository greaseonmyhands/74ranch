"""Primary Suite designs P1-P3 for the larger suite in 'Keegan's Plans – bathroom moved down'.
Writes plans/primary-suite-p{1,2,3}.json. Coordinates: plan meters (scan 1 frame).
Suite inside faces: west W, east E, north N; south face S (corridor side, west part) and the strip's
south face SS (top of the moved bathroom / Bedroom 2); the entry door is on x = -1.911."""
import json, copy
IN = 0.0254
base = json.load(open('plans/keegans-bath-down.json'))
W, E, N, S, SS = -3.744, 3.658, -4.651, -1.222, -0.119
report = {}
f = lambda m: round(m / IN, 1)
r4 = lambda v: [round(x, 4) for x in v]

def new(title, keep_ext_door):
    pl = copy.deepcopy(base); pl["title"] = title
    pl["rooms"] = [r for r in pl["rooms"] if r["name"] != "Primary Suite"]
    if not keep_ext_door: pl["remove"].append("Door_2~0")
    pl["notes"] = title + ". " + pl["notes"]
    return pl
def wall(pl, label, a, b, show=False): pl["add_walls"].append({"label": label, "from": r4(a), "to": r4(b), "show_length": show})
def door(pl, label, a, b, toward=None):
    d = {"label": label, "from": r4(a), "to": r4(b)}
    if toward: d["swing_toward"] = r4(toward)
    pl.setdefault("add_doors", []).append(d)
def opening(pl, label, a, b): pl.setdefault("add_openings", []).append({"label": label, "from": r4(a), "to": r4(b)})
def fx(pl, name, rect, **k): pl["fixtures"].append(dict(name=name, rect=r4(rect), **k))
def room(pl, name, at, label_at=None, size=8):
    r = {"at": r4(at), "name": name, "compact": True, "label_size": size}
    if label_at: r["label_at"] = r4(label_at)
    pl["rooms"].append(r)

def north_bath(pl, xp, wc_w, vanity_in, laundry, linen):
    """Bath north (WC room + linen + shower on the north wall, vanities + doorway on its south wall);
    horseshoe dressing room below it, down to the strip's south wall."""
    iW = xp + 0.05; cx = (iW + E) / 2
    zc = N + 36 * IN + 0.05; zw = N + 93 * IN + 0.05
    bS = zw - 0.05; dN = zw + 0.05; vz = bS - 21 * IN
    wc_e = iW + wc_w * IN + 0.05
    wall(pl, "Primary suite partition", [xp, -4.701], [xp, -0.069])
    wall(pl, "Bath / dressing wall", [xp, zw], [3.708, zw])
    wall(pl, "WC room south wall", [xp, zc], [wc_e, zc]); wall(pl, "WC room east wall", [wc_e, -4.701], [wc_e, zc])
    door(pl, "30in door, bedroom to bath aisle", [xp, -3.60], [xp, -3.60 + 30 * IN], [xp - 1, -3.2])
    door(pl, "24in WC room door", [wc_e - 0.05 - 26 * IN, zc], [wc_e - 0.05 - 2 * IN, zc], [wc_e - 0.5, zc - 1])
    opening(pl, "32in doorway between the vanities into the dressing room", [cx - 16 * IN, zw], [cx + 16 * IN, zw])
    wz = (N + zc - 0.05) / 2
    fx(pl, "WC", [iW, wz - 10 * IN, iW + 28 * IN, wz + 10 * IN], shape="toilet", front="e")
    fx(pl, "Shower\n60\" × 36\"", [E - 60 * IN, N, E, N + 36 * IN], hatch=".")
    if linen: fx(pl, "Linen", [wc_e + 0.1, N, wc_e + 0.1 + 24 * IN, N + 22 * IN])
    fx(pl, f"His vanity {vanity_in}\"", [cx - 17.5 * IN - vanity_in * IN, vz, cx - 17.5 * IN, bS])
    fx(pl, f"Her vanity {vanity_in}\"", [cx + 17.5 * IN, vz, cx + 17.5 * IN + vanity_in * IN, bS])
    arm, back = 22 * IN, 16 * IN
    ox0, ox1 = iW + arm, E - arm
    fx(pl, "Shelves / drawers", [iW, SS - back, E, SS], shape="closet")
    if laundry == "stacked":
        fx(pl, "W/D\nstacked", [iW, dN, iW + 27 * IN, dN + 32 * IN])
        fx(pl, "Hanging", [iW, dN + 33 * IN, ox0, SS - back], shape="closet", text_rotation=90)
        fx(pl, "Hanging", [ox1, dN, E, SS - back], shape="closet", text_rotation=90)
        isl = (30, 18)
    else:
        fx(pl, "Hanging", [iW, dN, ox0, SS - back], shape="closet", text_rotation=90)
        fx(pl, "Washer", [E - 32 * IN, dN, E, dN + 27 * IN], text_rotation=90)
        fx(pl, "Dryer", [E - 32 * IN, dN + 27 * IN, E, dN + 54 * IN], text_rotation=90)
        fx(pl, "Hanging", [ox1, dN + 55 * IN, E, SS - back], shape="closet", text_rotation=90)
        isl = (48, 20)
    icz = (dN + SS - back) / 2
    fx(pl, f"Island {isl[0]}\" × {isl[1]}\"", [cx - isl[0] / 2 * IN, icz - isl[1] / 2 * IN, cx + isl[0] / 2 * IN, icz + isl[1] / 2 * IN])
    room(pl, "Primary Bath", [cx, (zc + bS) / 2], [cx, (zc + vz) / 2 + 0.03], 7.5)
    room(pl, "WC", [(iW + wc_e) / 2, wz], [iW + 44 * IN, wz], 6.5)
    room(pl, "Dressing", [cx, SS - back - 0.2], [cx, icz + isl[1] / 2 * IN + 0.22], 7)
    report[pl["title"]] = {"suite inside": f"{f(E - iW)} wide", "aisle": f(vz - (zc + 0.05)),
        "dressing": f"{f(E - iW)}x{f(SS - dN)}", "island aisles (front/back)": (f(icz - isl[1] / 2 * IN - dN), f(SS - back - (icz + isl[1] / 2 * IN)))}

def south_bath(pl, xp, vanity_in):
    """Dressing room north (a clean rectangle); bath south, entered from the entry strip."""
    iW = xp + 0.05; cx = (iW + E) / 2
    zw = SS - 93 * IN - 0.05; bN = zw + 0.05; dS = zw - 0.05; vz = bN + 21 * IN
    zc = SS - 36 * IN - 0.05; wc_e = iW + 60 * IN + 0.05
    wall(pl, "Primary suite partition", [xp, -4.701], [xp, -0.069])
    wall(pl, "Dressing / bath wall", [xp, zw], [3.708, zw])
    wall(pl, "WC room north wall", [xp, zc], [wc_e, zc]); wall(pl, "WC room east wall", [wc_e, zc], [wc_e, -0.069])
    door(pl, "30in door, entry to bath aisle", [xp, vz + 0.05], [xp, vz + 0.05 + 30 * IN], [xp - 1, vz + 0.4])
    door(pl, "24in WC room door", [wc_e - 0.05 - 26 * IN, zc], [wc_e - 0.05 - 2 * IN, zc], [wc_e - 0.5, zc + 1])
    opening(pl, "32in doorway between the vanities into the dressing room", [cx - 16 * IN, zw], [cx + 16 * IN, zw])
    wz = (zc + 0.05 + SS) / 2
    fx(pl, "WC", [iW, wz - 10 * IN, iW + 28 * IN, wz + 10 * IN], shape="toilet", front="e")
    fx(pl, "Shower\n60\" × 36\"", [E - 60 * IN, SS - 36 * IN, E, SS], hatch=".")
    fx(pl, "Linen", [wc_e + 0.1, SS - 24 * IN, wc_e + 0.1 + 24 * IN, SS])
    fx(pl, f"His vanity {vanity_in}\"", [cx - 17.5 * IN - vanity_in * IN, bN, cx - 17.5 * IN, vz])
    fx(pl, f"Her vanity {vanity_in}\"", [cx + 17.5 * IN, bN, cx + 17.5 * IN + vanity_in * IN, vz])
    arm, back = 22 * IN, 16 * IN
    # washer + dryer on the west wall at the bottom (by the doorway); hanging above them and down the east wall
    fx(pl, "Washer", [iW, dS - 54 * IN, iW + 32 * IN, dS - 27 * IN], text_rotation=90)
    fx(pl, "Dryer", [iW, dS - 27 * IN, iW + 32 * IN, dS], text_rotation=90)
    fx(pl, "Hanging", [iW, N, iW + arm, dS - 55 * IN], shape="closet", text_rotation=90)
    fx(pl, "Shelves / drawers", [iW + arm, N, E - arm, N + back], shape="closet")
    fx(pl, "Hanging", [E - arm, N, E, dS], shape="closet", text_rotation=90)
    icz = (N + back + dS) / 2
    fx(pl, "Island 48\" × 20\"", [cx - 24 * IN, icz - 10 * IN, cx + 24 * IN, icz + 10 * IN])
    room(pl, "Primary Bath", [cx, (vz + zc) / 2], [cx + 0.25, (vz + zc - 0.05) / 2], 7.5)
    room(pl, "WC", [(iW + wc_e) / 2, wz], [iW + 44 * IN, wz], 6.5)
    room(pl, "Dressing", [cx, dS - 0.3], [cx, icz + 10 * IN + 0.22], 7)
    report[pl["title"]] = {"suite inside": f"{f(E - iW)} wide", "aisle": f(zc - 0.05 - vz),
        "dressing": f"{f(E - iW)}x{f(dS - N)}", "island aisles (front/back)": (f(dS - (icz + 10 * IN)), f(icz - 10 * IN - (N + back))),
        "W/D front to island": f((cx - 24 * IN) - (iW + 32 * IN)), "island to east hanging": f((E - arm) - (cx + 24 * IN))}

def bed_north(pl, xp, door_w=-0.591):
    bcx = (W + door_w) / 2
    fx(pl, "King bed\n76\" × 80\"", [bcx - 38 * IN, N, bcx + 38 * IN, N + 80 * IN], shape="bed", head="n")
    room(pl, "Primary Bedroom", [bcx, -1.8], [bcx, -1.75], 9)
def bed_west(pl, xp):
    cz = (N + S) / 2
    fx(pl, "King bed\n76\" × 80\"", [W, cz - 38 * IN, W + 80 * IN, cz + 38 * IN], shape="bed", head="w")
    room(pl, "Primary Bedroom", [(W + 80 * IN + xp) / 2, cz], [W + 46 * IN, -1.58], 8.5)   # below the bed

xp1 = 0.5                                  # keeps the north exterior door clear (bedroom 13'9")
xp2 = W - 0.05 + 120 * IN + 0.05           # exterior door removed (bedroom 10'0")
pl = new("Primary Suite – P1", True);  north_bath(pl, xp1, 54, 40, "stacked", False); bed_north(pl, xp1)
json.dump(pl, open('plans/primary-suite-p1.json', 'w'), indent=2)
pl = new("Primary Suite – P2", False); north_bath(pl, xp2, 60, 48, "side", True); bed_west(pl, xp2)
json.dump(pl, open('plans/primary-suite-p2.json', 'w'), indent=2)
pl = new("Primary Suite – P3", False); south_bath(pl, xp2, 48); bed_west(pl, xp2)
json.dump(pl, open('plans/primary-suite-p3.json', 'w'), indent=2)
for k, v in report.items(): print(k, v)
