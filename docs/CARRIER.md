# TriSense Spider S01 — DIY 8″ PLA basket

Rigid PLA spider that sits inside a DIY 8″ shell and holds:

- 1× center piezo + TriFlex V30 (+ felt)
- 3× position piezos @ 120°
- stereo pan jack on the spider

## Shell fit (measured)

| | mm |
|---|---:|
| Shell OD (approx.) | 200–201 |
| Shell ID | **185** |
| Assumed stack height H_stack | **35** (default; adjust foam if your floor→mesh differs) |

## S01 geometry

| Param | mm |
|---|---:|
| R_pos (position piezo centers) | 60 |
| R_foot (support feet) | 88 |
| R_max (clip envelope) | 90 |
| Plate thickness | 3.5 |
| Hub OD | 44 |
| TriFlex pocket OD × depth | 39 × 1.2 |
| Center piezo recess OD × depth | 29 × 0.6 |
| Center hole OD | 12 |
| Position pad OD | 28 |
| Position piezo recess OD × depth | 22 × 0.6 |
| Arm width | 28 |
| Foot OD × height | 14 × 4 |
| Jack hole OD / flange | 10 / 16 at R=38 on +X |
| Cable grooves | 3.5 × 1.5 underside |

STL: [`models/experimental/trisense-spider-diy8-s01.stl`](../models/experimental/trisense-spider-diy8-s01.stl)  
Generator: [`cad/generate_spider_s01.py`](../cad/generate_spider_s01.py)  
Preview: [`assets/spider-diy8-s01-preview.png`](../assets/spider-diy8-s01-preview.png)

## Couplers (same top plane)

- Center: TriFlex V30 body 32 mm + felt ~3 mm ≈ **35 mm** above plate top (plus piezo thickness under TriFlex).
- Position: foam Ø18–20 × **H ≈ 32–34 mm** so tops match TriFlex+felt.

## Print (PLA)

- Orient: large flat face on bed (feet up or down — feet-down preferred)
- Layer 0.20 mm · 3 walls · 35–40% infill
- Brim optional
- Supports usually not required

## Rebuild

```bash
# from trisense/, using triflex-cone venv that has trimesh/manifold3d:
../triflex-cone/.venv/bin/python cad/generate_spider_s01.py \
  models/experimental/trisense-spider-diy8-s01.stl
```

## Status

Generated experimental — not yet printed or fitted. Watertight mesh; bbox ≈ 141 × 162 × 7.5 mm (fits inside Ø185).
