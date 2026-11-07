# 74 Ranch

Notes, scans and plans for the house.

## Floorplans

Generated from iPhone LiDAR room scans (Apple RoomPlan `.glb` exports) taken 2026-11-06.
Measurements are surface to surface and are usually accurate to within an inch or two.
Each scan has its own coordinate frame, so the three plans are not aligned with each other yet.

| Scan | Plan | Rooms | Size | Area |
|---|---|---|---|---|
| 1 | [PNG](floorplans/2026-11-06_scan1.png) · [SVG](floorplans/2026-11-06_scan1.svg) | Room 1 | 24'3" × 16'1" | 382 sq ft |
|   |   | Room 2 (not rectangular) | 24'4" × 14'9" overall | 337 sq ft |
|   |   | Hallway | 8'1" × 3'2" overall | 23 sq ft |
| 2 | [PNG](floorplans/2026-11-06_scan2.png) · [SVG](floorplans/2026-11-06_scan2.svg) | Room (4 doors, 2 windows) | 17'1" × 11'0" | 188 sq ft |
| 3 | [PNG](floorplans/2026-11-06_scan3.png) · [SVG](floorplans/2026-11-06_scan3.svg) | Room with fireplace, 7'9" window | 15'0" × 15'9" | 235 sq ft |

Ceilings are about 8'1"–8'2". Full details for every wall, door, window (with sill height) and
detected piece of furniture are in the matching `floorplans/*.json` files.

### Notes from the scans
- **Scan 1:** Room 1 and Room 2 are open to each other: the wall between them (11'5") stops about 5 ft
  short of the hallway. One hallway door was picked up at an angle, which may be a door left
  ajar rather than an angled wall.
- **Scan 2:** The "storage cabinet" on the left wall starts 5'3" off the floor, so it's most likely
  upper or wall-mounted cabinets.
- **Scan 3:** The left wall has a 3'11" opening with no door (an archway or cased opening).

## Regenerating

```bash
pip install trimesh numpy shapely matplotlib
python tools/floorplan.py scans/*.glb --out floorplans
```

Drop new RoomPlan `.glb` exports in `scans/` and rerun.
