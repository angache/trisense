# TriSense

**DIY digital multi-sensor trigger for mesh drum pads**

TriSense is an experimental piezo → ADC → ESP32 → MIDI sensing layer. It is inspired by multi-element snare sensing (center head + peripheral position sensors), but it is an **independent** project: it does **not** implement any manufacturer digital-trigger bus or protocol.

Mechanical springs (TriFlex / MiniFlex) stay in [triflex-cone](https://github.com/angache/triflex-cone). TriSense is the electronics + firmware sibling.

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 | 1 piezo → ESP32 ADC → MIDI note + velocity | Firmware ready; physical test pending |
| 2 | +3 position piezos @ 120° → position CCs | Firmware ready; physical test pending |
| 3 | Rim / cross-stick | Out of scope until parts exist |

## Architecture

```
Mesh head
  ├─ Head piezo (center) ──┐
  ├─ Pos piezo 0° ─────────┤
  ├─ Pos piezo 120° ───────┼─→ divider / clamp / RC → ADC → ESP32 → MIDI
  └─ Pos piezo 240° ───────┘
```

- **Velocity** from the center (head) peak.
- **Position** (Phase 2) from the three peripheral peaks → radial + angle CCs.

## Quick start (Phase 1)

1. Build the protection circuit in [docs/SCHEMATIC.md](docs/SCHEMATIC.md).
2. Open [`firmware/trisense-midi/`](firmware/trisense-midi/) (Arduino-ESP32). Prefer **ESP32-S2/S3** for native USB-MIDI; classic ESP32 can use Serial MIDI bridge.
3. Flash, open Serial at 115200, tap the piezo, confirm peak lines.
4. Connect MIDI to a DAW / MIDI monitor (note 38 default).
5. Log results in [docs/TESTING.md](docs/TESTING.md).

## Safety

Piezo discs can produce tens of volts into a high impedance. Always use the load resistor + clamp before any ESP32 pin. Never wire a bare piezo to a GPIO.

## License

Same spirit as TriFlex: documentation and original firmware here are intended for non-commercial sharing with attribution pending formal LICENSE commit. Commercial use requires written permission from Ali Tuna.

## Trademark note

TriSense is independent. Third-party product names in design notes are descriptive only.
