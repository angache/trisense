# TriSense — Phase 1 / 2 schematic

Breadboard-friendly protection for piezo → ESP32 ADC (0–3.3 V).

## Single channel (Phase 1 — head)

```
  Piezo (+) ----+---- Rseries (2.2k) ----+---- to ESP32 ADC pin
                |                        |
                Rload (470k)             Cfilter (47nF) to GND
                |                        |
  Piezo (−) ----+---- GND ---------------+
                |
               Dclamp: two Schottky (or 3.3V TVS)
               anode→GND , cathode→ADC node  (blocks negative)
               and  diode/zener from ADC→3V3  (clamps above ~3.3V)
```

### Suggested first values (tune on the bench)

| Part | Value | Role |
|---|---|---|
| Rload | 220k–1M (start **470k**) | Piezo load; lower = quieter/safer, higher = hotter |
| Rseries | **2.2k** | Limits pin current; part of RC |
| Cfilter | **47 nF** | Softens spikes / ADC noise |
| Clamp | BAT54S dual Schottky, or 1N5819 + 3V3 zener | Keep node in ~0–3.3 V |

If peaks never reach threshold: raise Rload toward 1M.  
If ESP32 clips / false triggers: lower Rload toward 100–220k or add series R.

## Pin map (default firmware)

| Signal | ESP32 GPIO | Notes |
|---|---|---|
| HEAD (center) | **GPIO34** | Input-only ADC1 |
| POS0 (0°) | **GPIO35** | Phase 2 |
| POS1 (120°) | **GPIO32** | Phase 2 |
| POS2 (240°) | **GPIO33** | Phase 2 |
| GND | GND | Common with piezo (−) |
| 3V3 | 3V3 | Only for clamp reference |

Use **ADC1** pins when Wi-Fi/BLE is off or quiet; avoid ADC2 if Wi-Fi is on.

## Phase 2 — four identical channels

Duplicate the single-channel network three more times for POS0/1/2. Keep grounds star-tied near the ESP32.

Mechanical layout under the mesh (top view):

```
            POS1 (120°)
                 O
                  \
                   \
        POS2 O------+------O POS0
       (240°)   HEAD     (0°)
                  O
```

Center: TriFlex V30 + felt (or foam).  
Positions: thin foam discs or MiniFlex-class couplers — start with foam.

## ESP32 board choice

| Board | MIDI path |
|---|---|
| ESP32-S2 / S3 | Native **USB-MIDI** (`TRISENSE_USB_MIDI`) |
| Classic ESP32 | **Serial MIDI** at 31250 (Hairless MIDI / ttymidi) or enable BLE later |

## Checklist before first hit

1. Continuity: piezo (−) → GND.
2. No bare piezo on GPIO.
3. Multimeter: idle ADC node near 0 V (or small bias if you add one).
4. Soft tap first; watch Serial peaks before hard hits.
