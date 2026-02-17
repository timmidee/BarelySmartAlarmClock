#!/usr/bin/env python3
"""Test script for the 7-segment display."""

import time

try:
    import board
    import busio
    from adafruit_ht16k33.segments import Seg7x4
except ImportError:
    print("Required libraries not installed. Run:")
    print("  pip install adafruit-circuitpython-ht16k33")
    exit(1)

print("Initializing display...")
i2c = busio.I2C(board.SCL, board.SDA)
display = Seg7x4(i2c, address=0x70)

print("Running display test (Ctrl+C to exit)...")
print("")

try:
    # Test 1: All segments
    print("Test 1: All segments on")
    display.fill(1)
    time.sleep(1)

    # Test 2: Clear
    print("Test 2: Clear display")
    display.fill(0)
    time.sleep(0.5)

    # Test 3: Count
    print("Test 3: Counting 0-9")
    for i in range(10):
        display.print(f"{i}{i}{i}{i}")
        time.sleep(0.3)

    # Test 4: Colon blink
    print("Test 4: Colon blink")
    display.print("1234")
    for _ in range(6):
        display.colon = True
        time.sleep(0.5)
        display.colon = False
        time.sleep(0.5)

    # Test 5: Brightness
    print("Test 5: Brightness levels")
    display.print("8888")
    for b in [0.0, 0.25, 0.5, 0.75, 1.0, 0.5]:
        display.brightness = b
        time.sleep(0.4)

    # Test 6: Current time
    print("Test 6: Showing current time")
    from datetime import datetime
    for _ in range(10):
        now = datetime.now()
        display.print(f"{now.hour:02d}{now.minute:02d}")
        display.colon = now.second % 2 == 0
        time.sleep(0.5)

    print("")
    print("Display test complete!")

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    display.fill(0)
