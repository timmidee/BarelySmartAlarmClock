# Raspberry Pi Alarm Clock - Wiring Guide

## GPIO Pin Reference (BCM Numbering)

```
                    3.3V (1) (2)  5V
          I2C SDA - GPIO2 (3) (4)  5V
          I2C SCL - GPIO3 (5) (6)  GND
                   GPIO4 (7) (8)  GPIO14
                     GND (9) (10) GPIO15
                  GPIO17 (11)(12) GPIO18
                  GPIO27 (13)(14) GND
                  GPIO22 (15)(16) GPIO23
                    3.3V (17)(18) GPIO24
                  GPIO10 (19)(20) GND
                   GPIO9 (21)(22) GPIO25
                  GPIO11 (23)(24) GPIO8
                     GND (25)(26) GPIO7
                   GPIO0 (27)(28) GPIO1
                   GPIO5 (29)(30) GND
                   GPIO6 (31)(32) GPIO12
                  GPIO13 (33)(34) GND
                  GPIO19 (35)(36) GPIO16
                  GPIO26 (37)(38) GPIO20
                     GND (39)(40) GPIO21
```

## Components

### 1. Adafruit 1.2" 4-Digit 7-Segment Display (HT16K33)

The display uses I2C communication and needs 5 connections:

| Display Pin | Pi Pin | Description |
|-------------|--------|-------------|
| VIN / + | Pin 2 (5V) | LED power |
| IO | Pin 1 (3.3V) | I2C logic level |
| GND / - | Pin 6 (GND) | Ground |
| SDA / D | Pin 3 (GPIO2) | I2C Data |
| SCL / C | Pin 5 (GPIO3) | I2C Clock |

**Note:** VIN needs 5V to drive the LEDs. IO sets the I2C logic level and must match the Pi's 3.3V.

**I2C Address:** 0x70 (default)

### 2. DS3231 RTC Module

The RTC also uses I2C and shares the same bus as the display:

| RTC Pin | Pi Pin | Description |
|---------|--------|-------------|
| VCC | Pin 1 (3.3V) | Power |
| GND | Pin 6 (GND) | Ground |
| SDA | Pin 3 (GPIO2) | I2C Data (shared with display) |
| SCL | Pin 5 (GPIO3) | I2C Clock (shared with display) |

**I2C Address:** 0x68 (default)

**Note:** Install a CR2032 battery in the RTC module to maintain time during power loss.

### 3. Tactile Push Buttons

Using internal pull-up resistors, buttons connect to GPIO and ground:

| Button | GPIO Pin | Pi Pin | Ground |
|--------|----------|--------|--------|
| Snooze | GPIO17 | Pin 11 | Pin 9 (GND) |
| Dismiss | GPIO27 | Pin 13 | Pin 14 (GND) |

**Wiring:** Connect one leg of each button to the GPIO pin and the other leg to GND.

## Wiring Diagram

```
                        Raspberry Pi Zero 2 W
                    ┌───────────────────────────┐
                    │  (1) 3.3V ────────────────┼───── IO (Display) + VCC (RTC)
                    │  (2) 5V ──────────────────┼───── VIN (Display)
                    │  (3) GPIO2 ───────────────┼───── SDA (Display & RTC)
                    │  (4) 5V                   │
                    │  (5) GPIO3 ───────────────┼───── SCL (Display & RTC)
                    │  (6) GND ─────────────────┼───── GND (Display & RTC)
                    │  (7) GPIO4                │
                    │  (8) GPIO14               │
                    │  (9) GND ─────────────────┼───── Snooze Button
                    │ (10) GPIO15               │           │
                    │ (11) GPIO17 ──────────────┼───────────┘
                    │ (12) GPIO18               │
                    │ (13) GPIO27 ──────────────┼───────────┐
                    │ (14) GND ─────────────────┼───── Dismiss Button
                    │      ...                  │
                    └───────────────────────────┘
```

The display and RTC share the I2C bus (SDA, SCL, GND). The display needs an additional 5V connection for the LEDs.

## I2C Bus Setup

Both the display and RTC share the I2C bus:

```
I2C Bus (GPIO2 SDA, GPIO3 SCL)
    │
    ├── 7-Segment Display (0x70)
    │
    └── DS3231 RTC (0x68)
```

## Setup

### 1. Enable I2C on the Pi

```bash
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable
```

### 2. Install Dependencies

```bash
sudo apt update
sudo apt install i2c-tools python3-rpi.gpio alsa-utils mpg123
pip install adafruit-circuitpython-ht16k33 adafruit-circuitpython-ds3231
```

### 3. Connect USB Speakers

1. Connect USB speakers to the micro USB OTG hub
2. Connect the hub to the Pi's micro USB port

## Test Scripts

This folder contains test scripts to verify each component is wired correctly.

### Test I2C Devices (Display & RTC)

```bash
./test_i2c.sh
```

Expected: Shows devices at `0x68` (RTC) and `0x70` (Display).

### Test Display

```bash
python3 test_display.py
```

Runs through display tests: all segments, counting, colon blink, brightness levels, and current time.

### Test RTC

```bash
python3 test_rtc.py
```

Shows RTC time, temperature, and compares to system time. Offers to sync if they differ.

### Test Buttons

```bash
python3 test_buttons.py
```

Prints a message when snooze or dismiss button is pressed. Press Ctrl+C to exit.

### Test Audio

```bash
./test_audio.sh
```

Lists audio devices and plays a test tone through the speakers.

## Troubleshooting

### I2C Devices Not Detected

1. Check wiring connections
2. Ensure I2C is enabled: `sudo raspi-config`
3. Check for loose connections or damaged wires
4. Verify 3.3V power is reaching devices

### Buttons Not Responding

1. Check button wiring (GPIO to one leg, GND to other leg)
2. Test with a multimeter in continuity mode
3. Verify GPIO pins are not damaged

### No Audio Output

1. Check USB speaker connection
2. Verify audio device is detected: `aplay -l`
3. Set the correct audio output: `sudo raspi-config` → System Options → Audio
4. Install audio player: `sudo apt install mpg123`

### Display Shows Wrong Time

1. Sync RTC from system: The app does this automatically
2. Check RTC battery (CR2032)
3. Ensure Pi has internet access for initial NTP sync
