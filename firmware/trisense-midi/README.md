# trisense-midi

Arduino sketch for ESP32.

## Build

1. Install [Arduino-ESP32](https://docs.espressif.com/projects/arduino-esp32/).
2. Board: **ESP32-S3** (USB-MIDI later) or classic **ESP32 Dev Module**.
3. Open `trisense-midi.ino`.
4. Optional: set Phase 2 at the top:

```cpp
#define TRISENSE_PHASE 2
```

5. Upload. Serial Monitor 115200.

## MIDI

- **Serial MIDI** on `Serial1` TX pin **GPIO17** at 31250 baud → Hairless MIDI / ttymidi → DAW.
- Native USB-MIDI: on S2/S3, uncomment `#define TRISENSE_USB_MIDI` and wire TinyUSB MIDI in your core (board-dependent). Until that is confirmed on your board, use Serial MIDI.

## Calibration knobs

In the `.ino`:

- `THRESHOLD` — raise if ghost notes; lower if missing soft hits
- `RETRIGGER_MS` — double-trigger window
- `VEL_GAMMA` — velocity curve (<1 expands soft)
- `Rload` on the bench — see `docs/SCHEMATIC.md`
