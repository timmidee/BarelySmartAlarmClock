#!/bin/bash
# Test script to verify I2C devices are connected

echo "Scanning I2C bus for devices..."
echo ""
i2cdetect -y 1
echo ""
echo "Expected devices:"
echo "  0x68 = DS3231 RTC"
echo "  0x70 = HT16K33 Display"
echo ""
echo "If devices are not shown, check wiring and ensure I2C is enabled:"
echo "  sudo raspi-config → Interface Options → I2C → Enable"
