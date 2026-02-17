"""
Display Module - Controls the 7-segment LED display.
Supports both real hardware (HT16K33) and mock mode for testing.
"""

import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class Display:
    """7-segment display controller."""

    # HT16K33 I2C address (default)
    DEFAULT_ADDRESS = 0x70

    def __init__(self, mock=True, address=None):
        self.mock = mock
        self.address = address or self.DEFAULT_ADDRESS

        self._running = False
        self._thread = None
        self._brightness = 10
        self._colon = True
        self._alarm_indicator = False
        self._alarm_armed = False
        self._rtc = None
        self._alarm_manager = None

        self._device = None
        if not mock:
            self._init_hardware()
        else:
            logger.info("Display running in mock mode")

    def _init_hardware(self):
        """Initialize the real HT16K33 hardware."""
        try:
            import board
            from adafruit_ht16k33.segments import BigSeg7x4

            i2c = board.I2C()
            self._device = BigSeg7x4(i2c, address=self.address)
            self._device.brightness = self._brightness / 15.0
            logger.info(f"HT16K33 display initialized at address 0x{self.address:02X}")
        except ImportError as e:
            logger.warning(f"Hardware libraries not available, falling back to mock: {e}")
            self.mock = True
        except Exception as e:
            logger.error(f"Failed to initialize display hardware: {e}")
            self.mock = True

    def set_rtc(self, rtc):
        """Set the RTC reference for time display."""
        self._rtc = rtc

    def set_alarm_manager(self, alarm_manager):
        """Set the alarm manager reference to check armed state."""
        self._alarm_manager = alarm_manager

    def set_brightness(self, level):
        """Set display brightness (0-15)."""
        self._brightness = max(0, min(15, level))

        if self._device:
            self._device.brightness = self._brightness / 15.0

        logger.debug(f"Display brightness set to {self._brightness}")

    def set_alarm_indicator(self, on):
        """Set the alarm indicator (uses the colon or extra LED)."""
        self._alarm_indicator = on
        logger.debug(f"Alarm indicator {'on' if on else 'off'}")

    def show_time(self, hours, minutes):
        """Display time on the 7-segment display."""
        if self._device:
            # Real hardware
            self._device.fill(0)

            # Format time string
            time_str = f"{hours:02d}{minutes:02d}"
            self._device.print(time_str)

            # Set colon (blinking effect handled in update loop)
            self._device.colons[0] = self._colon

            # Upper-left dot indicates alarm is armed
            self._device.ampm = self._alarm_armed
        else:
            # Mock mode - log to console
            colon = ':' if self._colon else ' '
            indicator = '*' if self._alarm_indicator else ' '
            armed = 'A' if self._alarm_armed else ' '
            logger.debug(f"Display: {armed}{hours:02d}{colon}{minutes:02d} {indicator}")

    def show_text(self, text):
        """Display text on the 7-segment display (limited to 4 chars)."""
        if self._device:
            self._device.fill(0)
            self._device.print(text[:4])
        else:
            logger.debug(f"Display: {text[:4]}")

    def clear(self):
        """Clear the display."""
        if self._device:
            self._device.fill(0)
        logger.debug("Display cleared")

    def _update_loop(self):
        """Background thread that updates the display."""
        logger.info("Display update thread started")

        blink_counter = 0

        while self._running:
            try:
                # Get current time
                if self._rtc:
                    now = self._rtc.get_time()
                else:
                    now = datetime.now()

                # Blink colon every half second
                blink_counter += 1
                self._colon = (blink_counter % 2) == 0

                # Check if any alarm is within the next 12 hours
                if self._alarm_manager:
                    next_alarm = self._alarm_manager.get_next_alarm_info()
                    self._alarm_armed = next_alarm is not None and next_alarm['minutes_until'] <= 720

                # If alarm is ringing, blink the display
                if self._alarm_indicator:
                    if blink_counter % 4 < 2:
                        self.show_time(now.hour, now.minute)
                    else:
                        self.clear()
                else:
                    self.show_time(now.hour, now.minute)

            except Exception as e:
                logger.error(f"Error updating display: {e}")

            time.sleep(0.5)

        self.clear()
        logger.info("Display update thread stopped")

    def start(self):
        """Start the display update thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the display update thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self.clear()
