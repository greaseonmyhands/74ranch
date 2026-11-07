# 74 Ranch

Notes, scans and plans for the house.

## Floorplans

Generated from iPhone LiDAR room scans (Apple RoomPlan `.glb` exports) taken 2026-11-06.
Measurements are surface to surface and are usually accurate to within an inch or two.
Each scan has its own coordinate frame, so the three plans are not aligned with each other yet.

| Scan | Plan | Rooms | Size | Area |
|---|---|---|---|---|
| 1 | [PNG](floorplans/2026-11-06_scan1.png) · [SVG](floorplans/2026-11-06_scan1.svg) | Room 2 | 24'4" × 14'9" overall | 319 sq ft |
|   |   | Room 1A (incl. 4' corridor) | 12'6" × 19'3" overall | 193 sq ft |
|   |   | Room 1B | 11'9" × 16'1" | 189 sq ft |
|   |   | Bathroom | 6'8" × 6'5" (≈6'4" × 6'1" inside) | 43 sq ft |
| 2 | [PNG](floorplans/2026-11-06_scan2.png) · [SVG](floorplans/2026-11-06_scan2.svg) | Room (4 doors, 2 windows) | 17'1" × 11'0" | 188 sq ft |
| 3 | [PNG](floorplans/2026-11-06_scan3.png) · [SVG](floorplans/2026-11-06_scan3.svg) | Room with fireplace, 7'9" window | 15'0" × 15'9" | 235 sq ft |

Ceilings are about 8'1"–8'2". Full details for every wall, door, window (with sill height) and
detected piece of furniture are in the matching `floorplans/*.json` files.

### Notes from the scans
- **Scan 1:** Re-laid-out to match the hand sketch in [`sketches/2026-11-07_scan1-layout.jpg`](sketches/2026-11-07_scan1-layout.jpg)
  (all changes live in `scans/2026-11-06_scan1.edits.json`; the original scan is untouched):
  - Old hallway removed; a 4' corridor runs from the 2'7" wall to a new bathroom and opens south into Room 1A.
  - Corridor's north wall runs straight from the west exterior wall to the bathroom's east wall, with a
    36" door into Room 2. Bathroom has a 36" door on its west wall near the north end.
  - The 16'1" wall between Room 1A and 1B continues north as the bathroom's east wall and has a 36" door.
  - The angled west wall is straightened onto the exterior line, keeping the scanned 2'11" exterior door.
  - Bathroom fixture layout drawn in: 36" × 36" shower (NE corner), toilet on the east wall facing
    west (centerline 18" off the south wall, ~19" from the shower), 24" vanity on the west wall below
    the door. Meets IRC minimums (15" toilet side clearance, 21" in front of toilet and vanity) and
    the 36" door swings clear of every fixture.
  - Furniture is hidden.

  **Bigger-bathroom options** (side by side: [`floorplans/2026-11-06_scan1.bath-options.png`](floorplans/2026-11-06_scan1.bath-options.png)).
  Each moves the bathroom's east wall into Room 2 and Room 1B; the 11'5" wall gets shorter and the
  1A/1B wall now starts at the bathroom's south wall.

  | | Current | Option A | Option B |
  |---|---|---|---|
  | Plan | [PNG](floorplans/2026-11-06_scan1.png) | [PNG](floorplans/2026-11-06_scan1.bath-36x48.png) | [PNG](floorplans/2026-11-06_scan1.bath-40x60.png) |
  | East wall moved | — | 1 ft | 2 ft |
  | Bathroom inside | 6'4" × 6'1" | 7'4" × 6'1" | 8'4" × 6'1" |
  | Bathroom area | 43 sq ft | 49 sq ft | 55 sq ft |
  | Shower | 36" × 36" | 36" × 48" | 40" × 60" |
  | Vanity | 24" (west wall) | 36" (south wall) | 36" (south wall) |
  | Toilet centerline to shower / wall | 19" / 18" | 19" / 18" | 16" / 16" |
  | Room 2 | 319 sq ft | 316 sq ft | 313 sq ft |
  | Room 1B | 189 sq ft | 186 sq ft | 183 sq ft |

  All three meet IRC minimums (15" toilet side clearance, 21" in front of toilet and vanity), and the
  36" door swings clear of the shower by about 4" in each. Options live in
  `scans/2026-11-06_scan1.<option>.edits.json`.
- **Scan 2:** The "storage cabinet" on the left wall starts 5'3" off the floor, so it's most likely
  upper or wall-mounted cabinets.
- **Scan 3:** The left wall has a 3'11" opening with no door (an archway or cased opening).

## Regenerating

```bash
pip install trimesh numpy shapely matplotlib
python tools/floorplan.py scans/*.glb --out floorplans
```

Drop new RoomPlan `.glb` exports in `scans/` and rerun. To hide objects or walls from a scan without
touching the original, list their names (or glob patterns) in a `<scan>.edits.json` next to it.
New walls are given by their centerline endpoints `[x, z]` in the scan's own coordinates (meters):

```json
{
  "remove": ["chair_*", "Wall_10"],
  "move": [{ "nodes": ["Wall_2"], "by": [0, -0.13] }],
  "add_walls": [{ "from": [0.12, -0.20], "to": [0.12, 4.69], "label": "new partition" }],
  "add_doors": [{ "from": [0.12, 1.57], "to": [0.12, 2.49], "label": "36in door" }],
  "add_floor": [[[-3.68, -1.17], [-1.91, -1.17], [-1.91, -0.07], [-3.68, -0.07]]],
  "rooms": [{ "at": [-0.9, -0.2], "name": "Bathroom" }]
}
```

To compare design options, copy a scan's edits to `<scan>.<option>.edits.json`, change it, and rerun;
each option renders as `floorplans/<scan>.<option>.png`.

Rooms are found from the walls themselves (doors don't count as gaps), so adding or removing a wall
re-divides the rooms automatically. `rooms` renames whichever room contains the given point.

