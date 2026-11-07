# 74 Ranch

Notes, scans and plans for the house.

## Floorplans

Generated from iPhone LiDAR room scans (Apple RoomPlan `.glb` exports) taken 2026-11-06.
Measurements are surface to surface and are usually accurate to within an inch or two.
Each scan has its own coordinate frame, so the three plans are not aligned with each other yet.

| Scan | Plan | Rooms | Size | Area |
|---|---|---|---|---|
| 1 | [PNG](floorplans/2026-11-06_scan1.png) · [SVG](floorplans/2026-11-06_scan1.svg) | Room 1A (west of new wall) | 12'4" × 16'1" overall | 192 sq ft |
|   |   | Room 1B (east of new wall) | 11'7" × 16'1" | 186 sq ft |
|   |   | Room 2 (not rectangular) | 24'4" × 14'9" overall | 333 sq ft |
|   |   | Hallway | 8'1" × 3'2" overall | 23 sq ft |
| 2 | [PNG](floorplans/2026-11-06_scan2.png) · [SVG](floorplans/2026-11-06_scan2.svg) | Room (4 doors, 2 windows) | 17'1" × 11'0" | 188 sq ft |
| 3 | [PNG](floorplans/2026-11-06_scan3.png) · [SVG](floorplans/2026-11-06_scan3.svg) | Room with fireplace, 7'9" window | 15'0" × 15'9" | 235 sq ft |

Ceilings are about 8'1"–8'2". Full details for every wall, door, window (with sill height) and
detected piece of furniture are in the matching `floorplans/*.json` files.

### Notes from the scans
- **Scan 1:** Room 1 and Room 2 are open to each other: the wall between them (11'5") stops about 5 ft
  short of the hallway. One hallway door was picked up at an angle, which may be a door left
  ajar rather than an angled wall. Furniture and the short 3'2" wall on the hallway's east end
  are hidden via `scans/2026-11-06_scan1.edits.json`. That file also adds a new 16'1" wall running
  south from the west end of the 11'5" wall to the exterior wall, splitting Room 1 into 1A and 1B.
  (1B has no door yet.) The hallway (both its walls, doors and floor) is shifted north about 5" so
  its south wall lines up with the 11'5" wall, and the 2'7" wall below it is stretched to 3'2" to meet it.
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
  "add_walls": [{ "from": [0.12, -0.20], "to": [0.12, 4.69], "label": "new partition" }]
}
```
