#!/usr/bin/env python3
"""Test script for the DS3231 RTC module."""

import time
from datetime import datetime

try:
    import board
    import busio
    import adafruit_ds3231
except ImportError:
    print("Required libraries not installed. Run:")
    print("  pip install adafruit-circuitpython-ds3231")
    exit(1)

print("Initializing RTC...")
i2c = busio.I2C(board.SCL, board.SDA)
rtc = adafruit_ds3231.DS3231(i2c)

print("")
print("=== RTC Status ===")
print(f"RTC time:    {rtc.datetime.tm_hour:02d}:{rtc.datetime.tm_min:02d}:{rtc.datetime.tm_sec:02d}")
print(f"RTC date:    {rtc.datetime.tm_year}-{rtc.datetime.tm_mon:02d}-{rtc.datetime.tm_mday:02d}")
print(f"Temperature: {rtc.temperature:.1f}°C")
print("")

system_time = datetime.now()
print(f"System time: {system_time.strftime('%H:%M:%S')}")
print(f"System date: {system_time.strftime('%Y-%m-%d')}")
print("")

# Check if times match (within 2 seconds)
rtc_dt = datetime(
    rtc.datetime.tm_year, rtc.datetime.tm_mon, rtc.datetime.tm_mday,
    rtc.datetime.tm_hour, rtc.datetime.tm_min, rtc.datetime.tm_sec
)
diff = abs((system_time - rtc_dt).total_seconds())

if diff <= 2:
    print("RTC and system time are in sync.")
else:
    print(f"WARNING: RTC differs from system time by {diff:.0f} seconds")
    print("")
    response = input("Sync RTC to system time? [y/N]: ").strip().lower()
    if response == 'y':
        rtc.datetime = time.struct_time((
            system_time.year, system_time.month, system_time.day,
            system_time.hour, system_time.minute, system_time.second,
            system_time.weekday(), -1, -1
        ))
        print("RTC synced to system time.")
