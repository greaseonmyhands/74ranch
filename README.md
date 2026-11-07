# 74 Ranch

Notes, scans and plans for the house.

## Main floor (combined)

[`floorplans/main-floor.png`](floorplans/main-floor.png) · [SVG](floorplans/main-floor.svg): the
North End Renovation (scan 1), the kitchen/dining room (scan 5), the front living room (scan 3) and
the laundry room (scan 2) and the office (scan 6) joined into one plan, about **1,931 sq ft** so far
(including the 43 sq ft front porch). Defined in [`plans/main-floor.json`](plans/main-floor.json).

| Room | Area |
|---|---|
| Kitchen | 262 sq ft |
| Dining (scan 5's "living room", open to the kitchen) | 268 sq ft |
| Living Room (front living room + old Room 1A and its corridor, wall between removed) | 431 sq ft |
| Room 2 | 314 sq ft |
| Bedroom 2 (was Room 1B; queen bed drawn for scale) | 183 sq ft |
| Laundry Room | 188 sq ft |
| Office | 179 sq ft |
| Front Porch (6' double front door) | 43 sq ft |
| Hall (kitchen to office) | 9 sq ft |
| Bathroom | 55 sq ft |

How they fit:
- The dining room's east wall and Room 2's west wall are one wall: a standard 4" wall, drawn with its
  west face on the dining room's scanned surface (11'7" long). The kitchen/dining scan is placed so
  its south-wall hallway opening ends exactly at the Living Room's extended west wall; with that,
  Room 2 comes out about 1" wider than its own scan.
- The north walls of both scans are exactly in line, and so are the dining room's south wall and the
  North End's short step-in wall (moved 4 mm to match). The dining room's 5'0" opening runs about 5"
  past the North End corridor line, into that step-in wall.
- The walk-through from the dining room into the North End corridor has its north side on the same
  line as the corridor's top wall. The dashed line there separates Dining from the Living Room; it
  meets the south wall at the right edge of the dining room's 5'0" opening.
- The front living room sat beside Room 1A (sharing a 12'10" wall, now removed so they're one Living
  Room). Its north wall (14'10", with the fireplace) is in line with Room 1A's lower 1'6" wall, and it
  projects 2'10" further south than Room 1A: the front of the house jogs there.
- Between the dining room's south wall and the Living Room's north wall is an unscanned strip
  about 2'9" deep, which the dining room's 5'0" opening leads into (an entry or hall?). The two
  fireplaces sit nearly back to back across it, so it likely holds the shared chimney too. The Living
  Room's 6'4" west wall continues 2'9" north to the dining room's south wall, closing the strip's west end.
- The Laundry Room sits west of the kitchen and shares a standard 4" wall with it (11'0"); their south
  walls are in line, and the kitchen runs 4'2" further north. The kitchen's 36" doorway in that wall
  opens into the laundry room.
- The Office (scan 6, turned 180°, furniture removed) sits in the SW block: its SW inside corner is on
  the block's SW inside corner (kitchen west-wall line / Living Room south-wall line), so its west and
  south walls are the outline walls. Its ~4' opening faces east into the rest of the block; the wall
  below the opening is moved 5½" east to line up with the 6'2" wall above it and lengthened to 5'2",
  matching the Living Room's 5'2" wall opposite. An 8'3" wall joins the tops of those two walls,
  enclosing the Front Porch (8'3" × 5'2"); a 6' double front door, centered in that wall, opens north
  into the hallway area.
- A 36"-wide hall runs about 3' from the kitchen's SW opening straight down to the Office, ending in
  a 36" opening in the Office's north wall.
- The SW corner is boxed out: the kitchen's west wall continues 18'6" south and the Living Room's south
  wall continues 20'0" west to meet it. Apart from the Office, that block isn't scanned yet (an
  ~8'-wide area between the Office and the Living Room, plus a strip above the Office); the
  kitchen's south opening, the dining room's hallway opening and the Living Room's 3'11" west opening
  lead into it.

## Floorplans

Generated from iPhone LiDAR room scans (Apple RoomPlan `.glb` exports) taken 2026-11-06.
Furniture is drawn grey; wall-hung items (upper cabinets, shelves) are dashed outlines. Doorless
openings are plain gaps in the wall (no label or end marks); doors and windows are labelled.
Measurements are surface to surface and are usually accurate to within an inch or two.
Each scan has its own coordinate frame, so the three plans are not aligned with each other yet.

| Scan | Plan | Rooms | Size | Area |
|---|---|---|---|---|
| 1 — North End Renovation | [PNG](floorplans/2026-11-06_scan1.png) · [SVG](floorplans/2026-11-06_scan1.svg) | Room 2 (323 sq ft on the main-floor plan) | 24'4" × 14'9" overall | 313 sq ft |
|   |   | Room 1A (incl. 4' corridor) | 12'6" × 19'3" overall | 193 sq ft |
|   |   | Room 1B | 13'9" × 16'1" overall | 183 sq ft |
|   |   | Bathroom | 8'8" × 6'5" (8'4" × 6'1" inside) | 55 sq ft |
| 2 | [PNG](floorplans/2026-11-06_scan2.png) · [SVG](floorplans/2026-11-06_scan2.svg) | Laundry Room (4 doors, 2 windows) | 17'1" × 11'0" | 188 sq ft |
| 3 | [PNG](floorplans/2026-11-06_scan3.png) · [SVG](floorplans/2026-11-06_scan3.svg) | Front Living Room (fireplace, 7'9" window) | 15'0" × 15'9" | 235 sq ft |
| 6 | [PNG](floorplans/2026-11-06_scan6.png) · [SVG](floorplans/2026-11-06_scan6.svg) | Office (turned 180°; 4'10" window, ~4' opening on the right wall) | 11'7" × 15'5" | 179 sq ft |
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
  corner opens to a hallway. The tall cabinet and the table along the south wall are removed. The kitchen's 2'8" door in the south wall is now a doorless 36" opening on
  the same center. Two more doorless 36" openings: one in the south wall (to a hallway), running
  right up to the dining table's left edge; one in the kitchen's west wall, centered
  between the fridge and the SW corner. Kitchen cabinets are drawn at standard depths from the wall: 25½" for base
  and tall cabinets, dishwasher and range (24" box + countertop overhang), 12" for uppers.
- **Scan 2 — Laundry Room:** Turned 180°, table and shelf removed (`scans/2026-11-06_scan2.edits.json`). The "storage cabinet" on the right
  wall (dashed) starts 5'3" off the floor, so it's most likely upper or wall-mounted cabinets.
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

