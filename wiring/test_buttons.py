#!/usr/bin/env python3
"""Test script for snooze and dismiss buttons."""

import RPi.GPIO as GPIO
import time

SNOOZE_PIN = 17
DISMISS_PIN = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(SNOOZE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DISMISS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Button test running. Press buttons to test (Ctrl+C to exit)...")
print(f"  Snooze: GPIO{SNOOZE_PIN}")
print(f"  Dismiss: GPIO{DISMISS_PIN}")
print()

try:
    while True:
        if not GPIO.input(SNOOZE_PIN):
            print("Snooze button pressed")
            time.sleep(0.3)  # Debounce
        if not GPIO.input(DISMISS_PIN):
            print("Dismiss button pressed")
            time.sleep(0.3)  # Debounce
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nExiting...")
finally:
    GPIO.cleanup()
