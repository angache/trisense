/*
 * TriSense — piezo peak detect → MIDI
 *
 * Phase 1: head ADC → note + velocity
 * Phase 2: head + 3 position ADCs → note + velocity + radial/angle CC
 *
 * MIDI: Serial1 TX @ 31250 (default GPIO17) for Hairless MIDI / ttymidi.
 * ESP32-S2/S3 native USB-MIDI can be added later per board TinyUSB setup.
 */

#include <Arduino.h>
#include <math.h>

#ifndef TRISENSE_PHASE
#define TRISENSE_PHASE 1  // 1 = head only, 2 = head + 3 position
#endif

static const int PIN_HEAD = 34;
static const int PIN_POS0 = 35;
static const int PIN_POS1 = 32;
static const int PIN_POS2 = 33;

static const uint8_t MIDI_CHANNEL = 0;
static const uint8_t MIDI_NOTE = 38;
static const uint8_t CC_RADIAL = 16;
static const uint8_t CC_ANGLE = 17;

static const int THRESHOLD = 180;
static const int RETRIGGER_MS = 40;
static const int NOTE_OFF_MS = 35;
static const float VEL_GAMMA = 0.55f;

#ifndef MIDI_TX_PIN
#define MIDI_TX_PIN 17
#endif

#if TRISENSE_PHASE >= 2
static const int NUM_CH = 4;
#else
static const int NUM_CH = 1;
#endif

static const int PINS[4] = {PIN_HEAD, PIN_POS0, PIN_POS1, PIN_POS2};

static int baseline[4];
static int envPeak[4];
static bool inHit[4];

static bool noteActive = false;
static uint32_t noteOffAt = 0;
static uint32_t lastTriggerMs = 0;

static int readAdc(int pin) {
  uint32_t sum = 0;
  for (int i = 0; i < 4; i++) {
    sum += analogRead(pin);
  }
  return (int)(sum / 4);
}

static void midiWrite(uint8_t status, uint8_t d1, uint8_t d2) {
  Serial1.write(status);
  Serial1.write(d1);
  Serial1.write(d2);
}

static void noteOn(uint8_t note, uint8_t vel) {
  midiWrite(0x90 | MIDI_CHANNEL, note, vel);
}

static void noteOff(uint8_t note) {
  midiWrite(0x80 | MIDI_CHANNEL, note, 0);
}

static void controlChange(uint8_t cc, uint8_t value) {
  midiWrite(0xB0 | MIDI_CHANNEL, cc, value);
}

static uint8_t velocityFromPeak(int peak) {
  float n = (float)peak / 3500.0f;
  if (n < 0.0f) {
    n = 0.0f;
  }
  if (n > 1.0f) {
    n = 1.0f;
  }
  int v = (int)(powf(n, VEL_GAMMA) * 126.0f) + 1;
  return (uint8_t)constrain(v, 1, 127);
}

#if TRISENSE_PHASE >= 2
static void emitPositionCCs(const int peaks[4]) {
  float p0 = (float)max(peaks[1], 0);
  float p1 = (float)max(peaks[2], 0);
  float p2 = (float)max(peaks[3], 0);
  float head = (float)max(peaks[0], 1);
  float peri = p0 + p1 + p2;
  float radial = peri / (head + peri + 1e-3f);
  float x = p0 - 0.5f * p1 - 0.5f * p2;
  float y = 0.8660254f * p1 - 0.8660254f * p2;
  float ang = atan2f(y, x);
  if (ang < 0) {
    ang += 6.2831853f;
  }
  uint8_t ccR = (uint8_t)constrain((int)(radial * 127.0f), 0, 127);
  uint8_t ccA = (uint8_t)constrain((int)(ang / 6.2831853f * 127.0f), 0, 127);
  controlChange(CC_RADIAL, ccR);
  controlChange(CC_ANGLE, ccA);
  Serial.printf(" pos r=%u a=%u p=[%d,%d,%d]\n", ccR, ccA, peaks[1], peaks[2], peaks[3]);
}
#endif

static void fire(const int peaks[4]) {
  uint8_t vel = velocityFromPeak(peaks[0]);
  noteOn(MIDI_NOTE, vel);
  noteActive = true;
  noteOffAt = millis() + NOTE_OFF_MS;
  lastTriggerMs = millis();
  Serial.printf("HIT peak=%d vel=%u", peaks[0], vel);
#if TRISENSE_PHASE >= 2
  emitPositionCCs(peaks);
#else
  Serial.println();
#endif
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.printf("\nTriSense MIDI  phase=%d\n", TRISENSE_PHASE);

  analogReadResolution(12);
#if defined(ARDUINO_ARCH_ESP32)
  analogSetAttenuation(ADC_11db);
#endif

  Serial1.begin(31250, SERIAL_8N1, -1, MIDI_TX_PIN);

  for (int i = 0; i < NUM_CH; i++) {
    pinMode(PINS[i], INPUT);
    baseline[i] = readAdc(PINS[i]);
    envPeak[i] = 0;
    inHit[i] = false;
  }

  Serial.println("Ready. Tap HEAD piezo (GPIO34). MIDI TX GPIO17 @ 31250.");
}

void loop() {
  int above[4] = {0, 0, 0, 0};

  for (int i = 0; i < NUM_CH; i++) {
    int x = readAdc(PINS[i]);
    int a = x - baseline[i];
    if (a < 0) {
      a = -a;
    }
    above[i] = a;

    if (!inHit[i]) {
      // quiet: track baseline slowly
      baseline[i] += (x - baseline[i]) / 64;
      if (a > THRESHOLD) {
        inHit[i] = true;
        envPeak[i] = a;
      }
    } else {
      if (a > envPeak[i]) {
        envPeak[i] = a;
      }
      // end of hit when signal falls near baseline
      if (a < THRESHOLD / 2) {
        inHit[i] = false;
        if (i == 0) {
          uint32_t now = millis();
          if (now - lastTriggerMs >= (uint32_t)RETRIGGER_MS && envPeak[0] > THRESHOLD) {
            int peaks[4] = {envPeak[0], envPeak[1], envPeak[2], envPeak[3]};
            // latch current above for channels still rising
            for (int j = 0; j < NUM_CH; j++) {
              if (above[j] > peaks[j]) {
                peaks[j] = above[j];
              }
            }
            fire(peaks);
          }
          for (int j = 0; j < NUM_CH; j++) {
            envPeak[j] = 0;
          }
        }
      }
    }
  }

  if (noteActive && (int32_t)(millis() - noteOffAt) >= 0) {
    noteOff(MIDI_NOTE);
    noteActive = false;
  }

  yield();
}
