"""
Button Handler Module - Handles GPIO button input.
Supports both real GPIO hardware and mock mode for testing.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)


class ButtonHandler:
    """Handles physical button input for snooze and dismiss."""

    # Default GPIO pins (BCM numbering)
    DEFAULT_SNOOZE_PIN = 17
    DEFAULT_DISMISS_PIN = 27

    # Debounce time in seconds
    DEBOUNCE_TIME = 0.3

    def __init__(self, mock=True, snooze_pin=None, dismiss_pin=None,
                 on_snooze=None, on_dismiss=None):
        self.mock = mock
        self.snooze_pin = snooze_pin or self.DEFAULT_SNOOZE_PIN
        self.dismiss_pin = dismiss_pin or self.DEFAULT_DISMISS_PIN

        self.on_snooze = on_snooze
        self.on_dismiss = on_dismiss

        self._running = False
        self._thread = None
        self._gpio = None

        self._last_snooze_time = 0
        self._last_dismiss_time = 0

        if not mock:
            self._init_hardware()
        else:
            logger.info("Button handler running in mock mode")

    def _init_hardware(self):
        """Initialize GPIO hardware."""
        try:
            import RPi.GPIO as GPIO

            self._gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Set up buttons with internal pull-up resistors
            # Buttons are expected to connect pin to ground when pressed
            GPIO.setup(self.snooze_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.dismiss_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            # Add event detection with callbacks
            GPIO.add_event_detect(
                self.snooze_pin,
                GPIO.FALLING,
                callback=self._snooze_callback,
                bouncetime=int(self.DEBOUNCE_TIME * 1000)
            )
            GPIO.add_event_detect(
                self.dismiss_pin,
                GPIO.FALLING,
                callback=self._dismiss_callback,
                bouncetime=int(self.DEBOUNCE_TIME * 1000)
            )

            logger.info(f"GPIO buttons initialized: snooze=GPIO{self.snooze_pin}, dismiss=GPIO{self.dismiss_pin}")

        except ImportError as e:
            logger.warning(f"GPIO library not available, falling back to mock: {e}")
            self.mock = True
        except Exception as e:
            logger.error(f"Failed to initialize GPIO: {e}")
            self.mock = True

    def _snooze_callback(self, channel):
        """Callback for snooze button press."""
        current_time = time.time()
        if current_time - self._last_snooze_time < self.DEBOUNCE_TIME:
            return

        self._last_snooze_time = current_time
        logger.info("Snooze button pressed")

        if self.on_snooze:
            try:
                self.on_snooze()
            except Exception as e:
                logger.error(f"Error in snooze callback: {e}")

    def _dismiss_callback(self, channel):
        """Callback for dismiss button press."""
        current_time = time.time()
        if current_time - self._last_dismiss_time < self.DEBOUNCE_TIME:
            return

        self._last_dismiss_time = current_time
        logger.info("Dismiss button pressed")

        if self.on_dismiss:
            try:
                self.on_dismiss()
            except Exception as e:
                logger.error(f"Error in dismiss callback: {e}")

    def _mock_input_loop(self):
        """Mock input loop for testing without hardware."""
        logger.info("Mock button handler started (no input in mock mode)")

        while self._running:
            # In mock mode, buttons can only be triggered via API
            time.sleep(1)

        logger.info("Mock button handler stopped")

    def start(self):
        """Start the button handler."""
        if self._running:
            return

        self._running = True

        if self.mock:
            # Start mock input thread
            self._thread = threading.Thread(target=self._mock_input_loop, daemon=True)
            self._thread.start()
        # For real hardware, GPIO event detection is already set up

        logger.info("Button handler started")

    def stop(self):
        """Stop the button handler and clean up GPIO."""
        self._running = False

        if self._thread:
            self._thread.join(timeout=2)

        if self._gpio:
            try:
                self._gpio.cleanup([self.snooze_pin, self.dismiss_pin])
            except Exception as e:
                logger.error(f"Error cleaning up GPIO: {e}")

        logger.info("Button handler stopped")

    def simulate_snooze(self):
        """Simulate a snooze button press (for testing/API)."""
        logger.info("Simulating snooze button press")
        if self.on_snooze:
            self.on_snooze()

    def simulate_dismiss(self):
        """Simulate a dismiss button press (for testing/API)."""
        logger.info("Simulating dismiss button press")
        if self.on_dismiss:
            self.on_dismiss()
