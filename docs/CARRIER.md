# TriSense Bowl — tapered L-seat carrier

Standard PLA basket form (from S03 concept):

- **L flange** on the shell rim under mesh / hoop (segmented — flex gaps)
- **Conical bowl** — wide top → narrow bottom (not parallel walls)
- Sensors on **raised floor pads** (no 3-arm spider)
- Pad height so TriFlex+felt (~35 mm) reaches the mesh plane

> Manufacturer pad names are descriptive compatibility only — not the product name.

## Print path — S05 hub + petals (current)

Like a flower: **center hub** (TriFlex seat) + **3 petals** around it.

| File | Role | Approx. bbox |
|---|---|---|
| [`trisense-bowl-diy8-s05-hub.stl`](../models/experimental/trisense-bowl-diy8-s05-hub.stl) | center piezo / TriFlex + join rim | ~82×90×14 mm |
| [`trisense-bowl-diy8-s05-petal-a.stl`](../models/experimental/trisense-bowl-diy8-s05-petal-a.stl) | petal + **jack** + 1 pos pad | ~85×170×49 mm |
| [`…-petal-b.stl`](../models/experimental/trisense-bowl-diy8-s05-petal-b.stl) / [`…-c.stl`](../models/experimental/trisense-bowl-diy8-s05-petal-c.stl) | petals | ~147×99×49 mm |

Assembled: [`assets/spider-diy8-s05-assembled.png`](../assets/spider-diy8-s05-assembled.png)  
Assembly steps: [`assets/spider-diy8-s05-assembly.png`](../assets/spider-diy8-s05-assembly.png)  
Preview: [`assets/spider-diy8-s05-preview.png`](../assets/spider-diy8-s05-preview.png)  
Generator: [`cad/generate_spider_s05.py`](../cad/generate_spider_s05.py)  
Concept / monolith: [`assets/spider-diy8-s03-concept.png`](../assets/spider-diy8-s03-concept.png) · [`triflex…s03.stl`](../models/experimental/trisense-spider-diy8-s03.stl)

### Why this split

- Hub is small and flat — easy print, holds the critical center stack.
- Petals carry L wall + one pos pad each; seams through **çentik** gaps (L legs stay whole).
- Joins are on the **floor** (tabs / pegs / M3), not floating bosses outside the OD.

### Assembly

1. Hub flat, pocket up.
2. Hub tabs seat in **open pockets** in each petal floor → **M3** from above (6×).
3. Petals meet **edge-to-edge** (same floor height — no stacking over walls).
4. **Horizontal M3** through facing pads at each seam; optional glue in the gap.
5. Petal **a** aligns with the shell jack hole.

Join note: [`assets/spider-diy8-s05-join-fix.png`](../assets/spider-diy8-s05-join-fix.png)

### L rim

- Bottom **solid ring** (~half wall), then **12 discrete L legs** (tapered wall + horizontal seat).
- **Çentik** = open gap (1.5°) between legs — down to ~half wall height (~22.5 mm).
- Not a shallow notch on top of a continuous cone.

### DIY8 envelope (locked from S03)

| | mm |
|---|---:|
| Shell ID / OD | 185 / ~201 |
| L OD / skirt / bottom | 198 / 183.5 / 150 |
| Overall height (mesh plane) | 49 |
| Center / pos pad top Z | 14 / 16 |

## Other inch sizes (standard form)

Catalog in [`cad/sizes.toml`](../cad/sizes.toml). Ratios from DIY8 S03; **measure your shell ID/OD** before printing non-diy8 sizes (catalog IDs are starting points).

| name | inch | sectors* |
|---|---:|---:|
| diy8 | 8 | 3 |
| tom10 | 10 | auto |
| tom12 | 12 | auto |
| tom13 | 13 | auto |
| tom14 | 14 | auto (often 6) |

\*Sector count increases so the wedge chord stays ≤ `bed_max_mm` (210). Always **3 position pads @ 120°**, regardless of sector count.

```bash
# diy8 hub + petals (S05):
../triflex-cone/.venv/bin/python cad/generate_spider_s05.py

# older parametric sectors (S04) / other sizes:
../triflex-cone/.venv/bin/python cad/generate_spider_bowl.py diy8
../triflex-cone/.venv/bin/python cad/generate_spider_bowl.py tom14
```

## Couplers

- Center: TriFlex V30 + felt ≈ 35 mm above center pad → mesh.
- Position: foam Ø18–20 × ≈ 33 mm above pos pad → mesh.

## Status

| Rev | Notes |
|---|---|
| **S05** | Hub + 3 petals (flower). diy8 kit generated; not yet printed. |
| S04 | Old 120° sectors — superseded by S05 for printing. |
| S03 | Monolith DIY8 form reference — kept. |
| S02 / S01 | Superseded. |
