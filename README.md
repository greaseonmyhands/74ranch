# 74 Ranch

Notes, scans and plans for the house.

## Main floor (combined)

[`floorplans/main-floor.png`](floorplans/main-floor.png) · [SVG](floorplans/main-floor.svg): the
North End Renovation (scan 1), the kitchen/dining room (scan 5) and the front living room (scan 3)
joined into one plan, about **1,524 sq ft** so far. Defined in [`plans/main-floor.json`](plans/main-floor.json).

| Room | Area |
|---|---|
| Kitchen | 262 sq ft |
| Dining (scan 5's "living room", open to the kitchen) | 269 sq ft |
| Living Room (front living room + old Room 1A and its corridor, wall between removed) | 433 sq ft |
| Room 2 | 323 sq ft (11" wider than its own scan; see below) |
| Bedroom 2 (was Room 1B; queen bed drawn for scale) | 183 sq ft |
| Bathroom | 55 sq ft |

How they fit:
- The living room's east wall and Room 2's west wall are one wall: a standard 4" wall, drawn with its
  west face on the living room's scanned surface (11'7" long). The two scans put the surfaces ~15"
  apart; the extra ~11" goes to Room 2.
- The north walls of both scans are exactly in line, and so are the living room's south wall and the
  North End's short step-in wall (moved 4 mm to match).
- The walk-through from the dining room into the North End corridor has its north side on the same
  line as the corridor's top wall. The dashed line there separates Dining from the Living Room.
- The front living room sat beside Room 1A (sharing a 12'10" wall, now removed so they're one Living
  Room). Its north wall (14'10", with the fireplace) is in line with Room 1A's lower 1'6" wall, and it
  projects 2'10" further south than Room 1A: the front of the house jogs there.
- Between the dining room's south wall and the Living Room's north wall is an unscanned strip
  about 2'9" deep, which the dining room's 5'1" opening leads into (an entry or hall?). The two
  fireplaces sit nearly back to back across it, so it likely holds the shared chimney too.

## Floorplans

Generated from iPhone LiDAR room scans (Apple RoomPlan `.glb` exports) taken 2026-11-06.
Furniture is drawn grey; wall-hung items (upper cabinets, shelves) are dashed outlines.
Measurements are surface to surface and are usually accurate to within an inch or two.
Each scan has its own coordinate frame, so the three plans are not aligned with each other yet.

| Scan | Plan | Rooms | Size | Area |
|---|---|---|---|---|
| 1 — North End Renovation | [PNG](floorplans/2026-11-06_scan1.png) · [SVG](floorplans/2026-11-06_scan1.svg) | Room 2 (323 sq ft on the main-floor plan) | 24'4" × 14'9" overall | 313 sq ft |
|   |   | Room 1A (incl. 4' corridor) | 12'6" × 19'3" overall | 193 sq ft |
|   |   | Room 1B | 13'9" × 16'1" overall | 183 sq ft |
|   |   | Bathroom | 8'8" × 6'5" (8'4" × 6'1" inside) | 55 sq ft |
| 2 | [PNG](floorplans/2026-11-06_scan2.png) · [SVG](floorplans/2026-11-06_scan2.svg) | Room (4 doors, 2 windows) | 17'1" × 11'0" | 188 sq ft |
| 3 | [PNG](floorplans/2026-11-06_scan3.png) · [SVG](floorplans/2026-11-06_scan3.svg) | Front Living Room (fireplace, 7'9" window) | 15'0" × 15'9" | 235 sq ft |
| 5 | [PNG](floorplans/2026-11-06_scan5.png) · [SVG](floorplans/2026-11-06_scan5.svg) | Kitchen (open to living room) | 17'3" × 15'2" | 262 sq ft |
|   |   | Living Room (fireplace) | 18'8" × 15'2" overall | 268 sq ft |

Ceilings are about 8'1"–8'2" (7'10" in the kitchen/living room). Full details for every wall, door, window (with sill height) and
detected piece of furniture are in the matching `floorplans/*.json` files.

### Notes from the scans
- **Scan 1 — North End Renovation** *(parked 2026-11-07)*. Re-laid-out to match the hand sketch in [`sketches/2026-11-07_scan1-layout.jpg`](sketches/2026-11-07_scan1-layout.jpg)
  (all changes live in `scans/2026-11-06_scan1.edits.json`; the original scan is untouched):
  - Old hallway removed; a 4' corridor runs from the 2'7" wall to a new bathroom and opens south into Room 1A.
  - Corridor's north wall runs straight from the west exterior wall to the bathroom's east wall, with a
    36" door into Room 2. Bathroom has a 36" door on its west wall near the north end.
  - The 16'1" wall between Room 1A and 1B continues north as the bathroom's east wall and has a 36" door.
  - The angled west wall (with the 2'11" "door" the scanner found) is removed: that side of the corridor
    is an open passage to a hallway, not a doorway.
  - Bathroom east wall moved 2 ft into Room 2 / Room 1B (the 11'5" wall is shorter and the 1A/1B wall
    starts at the bathroom's south wall). Layout: 40" × 60" shower along the south wall, toilet in the
    NE corner facing west (centerline 16" from the north wall and from the shower), 36" vanity in the
    SW corner. Meets IRC minimums (15" toilet side clearance, 21" in front of toilet and vanity); the
    36" door swings clear of the shower by about 4".
  - Furniture is hidden.

  **Open items when we pick this back up:**
  - Confirm the bathroom door position (drawn 6" from the bathroom's inside NW corner) and the
    Room 1A/1B door position (drawn 2'6" south of the bathroom).
  - Give Room 1A, 1B and 2 real names.
  - Connect the hallway beyond the corridor's west opening once it's scanned.

  **Other bathroom options considered** (each in `scans/2026-11-06_scan1.<option>.edits.json`):

  | | Main plan | [36×36](floorplans/2026-11-06_scan1.bath-36x36.png) | [36×48](floorplans/2026-11-06_scan1.bath-36x48.png) |
  |---|---|---|---|
  | East wall moved | 2 ft | — | 1 ft |
  | Bathroom inside | 8'4" × 6'1" | 6'4" × 6'1" | 7'4" × 6'1" |
  | Bathroom area | 55 sq ft | 43 sq ft | 49 sq ft |
  | Shower | 40" × 60" (south wall) | 36" × 36" (NE) | 36" × 48" (north wall) |
  | Vanity | 36" | 24" | 36" |
  | Room 2 / Room 1B | 313 / 183 sq ft | 319 / 189 sq ft | 316 / 186 sq ft |

- **Scan 4** was a duplicate of scan 3 (identical file), so it isn't included.
- **Scan 5:** Open-plan kitchen + living room, one 35'11" × 15'2" space; the dashed line on the plan is
  where RoomPlan put the boundary between them. The plan is turned 90° clockwise
  (`scans/2026-11-06_scan5.edits.json`). Ceiling is 7'10", lower than the other rooms.
  The scanner's top-right "fridge" in the kitchen is really a tall cabinet, and the 25" gap to its
  left is filled with a base cabinet. The 3'4" wall at the living room's SE corner is removed: that
  corner opens to a hallway. Kitchen cabinets are drawn at standard depths from the wall: 25½" for base
  and tall cabinets, dishwasher and range (24" box + countertop overhang), 12" for uppers.
- **Scan 2:** The "storage cabinet" on the left wall starts 5'3" off the floor, so it's most likely
  upper or wall-mounted cabinets.
- **Scan 3 — Front Living Room:** The left wall has a 3'11" opening with no door (an archway or cased
  opening). The scanned table is hidden (`scans/2026-11-06_scan3.edits.json`).

## Regenerating

```bash
pip install trimesh numpy shapely matplotlib
python tools/floorplan.py scans/*.glb plans/*.json --out floorplans
```

Combined plans (`plans/*.json`) place several scans on one drawing, each with its own edits, shifted
by an `offset` in meters; see `process_plan()` in `tools/floorplan.py` for the format.

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

