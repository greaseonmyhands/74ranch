"""Room 2 master-suite options H, I, J (center-aisle master bath). Writes plans/room2-option-{h,i,j}.json.
Built on Keegan's Plans with Room 2's exterior door removed. Coordinates are plan meters (scan 1 frame)."""
import json, copy
IN = 0.0254
base = json.load(open('plans/keegans-plans.json'))
W, E, N, S, Salc, Xalc = -3.744, 3.658, -4.651, -1.222, -0.252, 0.783   # Room 2 inside faces; alcove
report = {}
f = lambda m: round(m / IN, 1)

def new(title):
    pl = copy.deepcopy(base); pl["title"] = title
    pl["remove"].append("Door_2~0")
    pl["notes"] = title + ": center-aisle master bath. " + pl["notes"]
    return pl
def wall(pl, label, a, b, show=False):
    pl["add_walls"].append({"label": label, "from": [round(v, 4) for v in a], "to": [round(v, 4) for v in b], "show_length": show})
def door(pl, label, a, b, toward=None):
    d = {"label": label, "from": [round(v, 4) for v in a], "to": [round(v, 4) for v in b]}
    if toward: d["swing_toward"] = toward
    pl.setdefault("add_doors", []).append(d)
def opening(pl, label, a, b):
    pl.setdefault("add_openings", []).append({"label": label, "from": [round(v, 4) for v in a], "to": [round(v, 4) for v in b]})
def fx(pl, name, rect, **k): pl["fixtures"].append(dict(name=name, rect=[round(v, 4) for v in rect], **k))
def room(pl, name, at, label_at=None, size=8):
    r = {"at": [round(v, 4) for v in at], "name": name, "compact": True, "label_size": size}
    if label_at: r["label_at"] = [round(v, 4) for v in label_at]
    pl["rooms"].append(r)

def north_bath(pl, xp, vanity_in, laundry):
    """Bath on the north (center aisle: WC room, linen, shower on the north wall; vanities + doorway
    on the south wall); horseshoe dressing room south, using the alcove."""
    iW = xp + 0.05; cx = (iW + E) / 2
    zc = N + 36 * IN + 0.05; zw = N + 93 * IN + 0.05
    bS = zw - 0.05; dN = zw + 0.05; vz = bS - 21 * IN
    wc_e = iW + 60 * IN + 0.05
    wall(pl, "Master suite partition", [xp, -4.701], [xp, -1.172])
    wall(pl, "Bath / dressing wall", [xp, zw], [3.708, zw])
    wall(pl, "WC room south wall", [xp, zc], [wc_e, zc]); wall(pl, "WC room east wall", [wc_e, -4.701], [wc_e, zc])
    door(pl, "30in door, bedroom to bath aisle", [xp, -3.60], [xp, -3.60 + 30 * IN], [xp - 1, -3.2])
    door(pl, "24in WC room door", [wc_e - 0.05 - 26 * IN, zc], [wc_e - 0.05 - 2 * IN, zc], [wc_e - 0.5, zc - 1])
    opening(pl, "32in doorway between the vanities into the dressing room", [cx - 16 * IN, zw], [cx + 16 * IN, zw])
    wz = (N + zc - 0.05) / 2
    fx(pl, "WC", [iW, wz - 10 * IN, iW + 28 * IN, wz + 10 * IN], shape="toilet", front="e")
    fx(pl, "Shower\n60\" × 36\"", [E - 60 * IN, N, E, N + 36 * IN], hatch=".")
    fx(pl, "Linen", [wc_e + 0.05, N, E - 60 * IN, N + 22 * IN])
    fx(pl, f"His vanity {vanity_in}\"", [cx - 17.5 * IN - vanity_in * IN, vz, cx - 17.5 * IN, bS])
    fx(pl, f"Her vanity {vanity_in}\"", [cx + 17.5 * IN, vz, cx + 17.5 * IN + vanity_in * IN, bS])
    if laundry == "stacked":
        fx(pl, "W/D\nstacked", [iW, dN, iW + 27 * IN, dN + 32 * IN])
    else:
        fx(pl, "Washer", [iW, dN, iW + 27 * IN, dN + 32 * IN]); fx(pl, "Dryer", [iW + 27 * IN, dN, iW + 54 * IN, dN + 32 * IN])
    arm, back = 22 * IN, 16 * IN
    fx(pl, "Shelves / drawers", [Xalc, Salc - back, E, Salc], shape="closet")
    fx(pl, "Hanging", [Xalc, -1.70, Xalc + arm, Salc - back], shape="closet", text_rotation=90)
    fx(pl, "Hanging", [E - arm, -1.65, E, Salc - back], shape="closet", text_rotation=90)
    ox0, ox1 = Xalc + arm, E - arm; icx = (ox0 + ox1) / 2; icz = (dN + Salc - back) / 2
    fx(pl, "Island", [icx - 12 * IN, icz - 8 * IN, icx + 12 * IN, icz + 8 * IN])
    room(pl, "Master Bath", [cx, (zc + bS) / 2], [cx, (zc + vz) / 2 + 0.02], 7.5)
    room(pl, "Dressing", [icx, -1.0], [icx, icz + 8 * IN + 0.22], 6.5)
    room(pl, "WC", [(iW + wc_e) / 2, wz], [iW + 44 * IN, wz], 6.5)
    report[pl["title"]] = {"aisle": f(vz - (zc + 0.05)), "WC room": f"{f(wc_e - 0.05 - iW)}x{f(zc - 0.05 - N)}",
        "landing beside his vanity": f(cx - 17.5 * IN - vanity_in * IN - iW),
        "island aisles side/front/back": (f(icx - 12 * IN - ox0), f(icz - 8 * IN - dN), f(Salc - back - (icz + 8 * IN)))}

def south_bath(pl, xp, vanity_in):
    """Dressing room north (a clean rectangle); center-aisle bath south, WC room + shower in the alcove."""
    iW = xp + 0.05; cx = (iW + E) / 2
    zw = Salc - 93 * IN - 0.05; bN = zw + 0.05; dS = zw - 0.05; vz = bN + 21 * IN
    zc = Salc - 36 * IN - 0.05
    wc_e = Xalc + 54 * IN + 0.05
    wall(pl, "Master suite partition", [xp, -4.701], [xp, -1.172])
    wall(pl, "Dressing / bath wall", [xp, zw], [3.708, zw])
    wall(pl, "WC room north wall", [0.7328, zc], [wc_e, zc]); wall(pl, "WC room east wall", [wc_e, zc], [wc_e, -0.202])
    door(pl, "30in door, bedroom to bath aisle", [xp, -1.30 - 30 * IN], [xp, -1.30], [xp - 1, -1.7])
    door(pl, "24in WC room door", [wc_e - 0.05 - 26 * IN, zc], [wc_e - 0.05 - 2 * IN, zc], [wc_e - 0.5, zc + 1])
    opening(pl, "32in doorway between the vanities into the dressing room", [cx - 16 * IN, zw], [cx + 16 * IN, zw])
    wz = (zc + 0.05 + Salc) / 2
    fx(pl, "WC", [Xalc, wz - 10 * IN, Xalc + 28 * IN, wz + 10 * IN], shape="toilet", front="e")
    fx(pl, f"Shower\n{round((E - wc_e - 0.05) / IN)}\" × 36\"", [wc_e + 0.05, Salc - 36 * IN, E, Salc], hatch=".")
    fx(pl, f"His vanity {vanity_in}\"", [cx - 17.5 * IN - vanity_in * IN, bN, cx - 17.5 * IN, vz])
    fx(pl, f"Her vanity {vanity_in}\"", [cx + 17.5 * IN, bN, cx + 17.5 * IN + vanity_in * IN, vz])
    arm, back = 22 * IN, 16 * IN
    fx(pl, "Hanging", [iW, N, iW + arm, dS], shape="closet", text_rotation=90)
    fx(pl, "Shelves / drawers", [iW + arm, N, E - 32 * IN, N + back], shape="closet")
    fx(pl, "Washer", [E - 32 * IN, N, E, N + 27 * IN], text_rotation=90)
    fx(pl, "Dryer", [E - 32 * IN, N + 27 * IN, E, N + 54 * IN], text_rotation=90)
    fx(pl, "Hanging", [E - arm, N + 55 * IN, E, dS], shape="closet", text_rotation=90)
    icz = (N + back + dS) / 2
    fx(pl, "Island 48\" × 16\"", [cx - 24 * IN, icz - 8 * IN, cx + 24 * IN, icz + 8 * IN])
    room(pl, "Master Bath", [cx, (vz + zc) / 2], [cx - 0.2, (vz + zc - 0.05) / 2], 7.5)
    room(pl, "WC", [(Xalc + wc_e) / 2, wz], [Xalc + 42 * IN, wz], 6.5)
    room(pl, "Dressing", [cx, dS - 0.3], [cx, icz + 8 * IN + 0.2], 7)
    report[pl["title"]] = {"aisle": f(zc - 0.05 - vz), "WC room": f"{f(wc_e - 0.05 - Xalc)}x{f(Salc - (zc + 0.05))}",
        "bedroom door strip below his vanity": f(-1.222 - vz),
        "island aisles W/E/front/back": (f(cx - 24 * IN - (iW + arm)), f(E - 32 * IN - (cx + 24 * IN)), f(dS - (icz + 8 * IN)), f(icz - 8 * IN - (N + back)))}

def bed_north(pl, xp):
    bcx = (W + xp - 0.05) / 2
    fx(pl, "King bed\n76\" × 80\"", [bcx - 38 * IN, N, bcx + 38 * IN, N + 80 * IN], shape="bed", head="n")
    room(pl, "Master Bedroom", [bcx, -1.75], [bcx, -1.72], 9)
def bed_west(pl, xp):
    cz = (N + S) / 2
    fx(pl, "King bed\n76\" × 80\"", [W, cz - 38 * IN, W + 80 * IN, cz + 38 * IN], shape="bed", head="w")
    room(pl, "Master Bedroom", [(W + xp) / 2, -1.55], [(W + xp) / 2 - 0.1, -1.58], 8)   # below the bed

xp_h = 0.5 - 24 * IN                     # bedroom 11'9" (bed on the north wall)
xp_ij = W - 0.05 + 120 * IN + 0.05       # bedroom 10'0" (bed on the west wall)
pl = new("Room 2 Master Suite – Option H"); north_bath(pl, xp_h, 42, "stacked"); bed_north(pl, xp_h)
json.dump(pl, open('plans/room2-option-h.json', 'w'), indent=2)
pl = new("Room 2 Master Suite – Option I"); north_bath(pl, xp_ij, 48, "side"); bed_west(pl, xp_ij)
json.dump(pl, open('plans/room2-option-i.json', 'w'), indent=2)
pl = new("Room 2 Master Suite – Option J"); south_bath(pl, xp_ij, 48); bed_west(pl, xp_ij)
json.dump(pl, open('plans/room2-option-j.json', 'w'), indent=2)
for k, v in report.items(): print(k, v)
