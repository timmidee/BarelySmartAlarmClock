"""
RTC Module - Real Time Clock interface.
Supports both real DS3231 hardware and mock mode for testing.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RTC:
    """Real Time Clock interface for DS3231."""

    DEFAULT_ADDRESS = 0x68

    def __init__(self, mock=True, address=None):
        self.mock = mock
        self.address = address or self.DEFAULT_ADDRESS

        self._device = None
        if not mock:
            self._init_hardware()
        else:
            logger.info("RTC running in mock mode (using system time)")

    def _init_hardware(self):
        """Initialize the real DS3231 hardware."""
        try:
            import board
            import busio
            import adafruit_ds3231

            i2c = busio.I2C(board.SCL, board.SDA)
            self._device = adafruit_ds3231.DS3231(i2c)
            logger.info(f"DS3231 RTC initialized at address 0x{self.address:02X}")
        except ImportError as e:
            logger.warning(f"Hardware libraries not available, falling back to mock: {e}")
            self.mock = True
        except Exception as e:
            logger.error(f"Failed to initialize RTC hardware: {e}")
            self.mock = True

    def get_time(self):
        """Get the current time from the RTC."""
        if self._device:
            # Real hardware - get time from DS3231
            try:
                rtc_time = self._device.datetime
                return datetime(
                    rtc_time.tm_year,
                    rtc_time.tm_mon,
                    rtc_time.tm_mday,
                    rtc_time.tm_hour,
                    rtc_time.tm_min,
                    rtc_time.tm_sec
                )
            except Exception as e:
                logger.error(f"Error reading RTC: {e}")
                return datetime.now()
        else:
            # Mock mode - use system time
            return datetime.now()

    def set_time(self, dt):
        """Set the RTC time."""
        if self._device:
            try:
                import time
                self._device.datetime = time.struct_time((
                    dt.year, dt.month, dt.day,
                    dt.hour, dt.minute, dt.second,
                    dt.weekday(), -1, -1
                ))
                logger.info(f"RTC time set to {dt}")
            except Exception as e:
                logger.error(f"Error setting RTC: {e}")
        else:
            logger.info(f"Mock RTC: would set time to {dt}")

    def sync_from_system(self):
        """Sync the RTC from the system clock."""
        self.set_time(datetime.now())

    def get_temperature(self):
        """Get the temperature from the DS3231 (it has a built-in sensor)."""
        if self._device:
            try:
                return self._device.temperature
            except Exception as e:
                logger.error(f"Error reading temperature: {e}")
                return None
        return None
