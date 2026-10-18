# TriSense test log

Separate physical observations from hypotheses.

## Phase 1 — single piezo → MIDI (procedure)

Hardware:
- One piezo + protection network per [SCHEMATIC.md](SCHEMATIC.md)
- ESP32 (S2/S3 preferred)
- Firmware: `firmware/trisense-midi/` with `TRISENSE_PHASE = 1`

Steps:
1. Flash firmware; Serial 115200.
2. Soft finger tap → Serial shows `peak=… vel=…` without saturating at 4095 every time.
3. Stick hits light / medium / hard → velocities should spread (not all 127).
4. Connect USB-MIDI (or Serial MIDI bridge) to a DAW / MIDI monitor.
5. Confirm note-on (default 38) with matching velocities; note-off follows.

### Phase 1 result — pending physical run

| Field | Value |
|---|---|
| Date | _pending_ |
| Board | |
| Rload / Rseries / C | |
| Threshold (raw) | |
| Observed | _not yet recorded_ |
| Status | Firmware ready; awaiting bench test |

Hypothesis (untested): ESP32 ADC + peak detector is enough for usable snare velocity on a mesh pad when the piezo is loaded ~470k and clamped.

## Phase 2 — position CCs (procedure)

Enable `TRISENSE_PHASE 2` (4 ADC channels). Hit center vs edge vs near each POS piezo.

Expected (hypothesis):
- Center hits → low radial CC (~0–40)
- Edge near a POS → high radial CC; angle CC leans toward that sensor

### Phase 2 result — pending

| Field | Value |
|---|---|
| Date | _pending_ |
| Observed | _not yet recorded_ |
| Status | Firmware ready; awaiting Phase 1 success first |
