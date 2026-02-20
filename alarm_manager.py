"""
Alarm Manager - Handles alarm storage, scheduling, and triggering.
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class AlarmManager:
    """Manages alarm storage and scheduling."""

    DAYS_MAP = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6,
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
    }

    def __init__(self, rtc, audio_player, display, snooze_minutes=9, check_interval=30, timeout_minutes=5):
        self.rtc = rtc
        self.audio_player = audio_player
        self.display = display
        self.snooze_minutes = snooze_minutes
        self.check_interval = check_interval
        self.timeout_minutes = timeout_minutes

        self.alarms_file = Path(__file__).parent / 'alarms.json'
        self.overrides_file = Path(__file__).parent / 'overrides.json'
        self.alarms = {}
        self.overrides = {}
        self._load_alarms()
        self._load_overrides()

        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        self._ringing = False
        self._ringing_alarm_id = None
        self._ringing_override_id = None
        self._ringing_since = None
        self._snooze_until = None

    def _load_alarms(self):
        """Load alarms from JSON file."""
        if self.alarms_file.exists():
            try:
                with open(self.alarms_file) as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError(f"Expected dict, got {type(data).__name__}")
                self.alarms = data
                logger.info(f"Loaded {len(self.alarms)} alarms")
            except (json.JSONDecodeError, IOError, ValueError) as e:
                logger.error(f"Failed to load alarms: {e}")
                self.alarms = {}
        else:
            self.alarms = {}
            self._save_alarms()

    def _save_alarms(self):
        """Save alarms to JSON file."""
        try:
            with open(self.alarms_file, 'w') as f:
                json.dump(self.alarms, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save alarms: {e}")

    def _load_overrides(self):
        """Load overrides from JSON file."""
        if self.overrides_file.exists():
            try:
                with open(self.overrides_file) as f:
                    self.overrides = json.load(f)
                logger.info(f"Loaded {len(self.overrides)} overrides")
                self._cleanup_expired_overrides()
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load overrides: {e}")
                self.overrides = {}
        else:
            self.overrides = {}
            self._save_overrides()

    def _save_overrides(self):
        """Save overrides to JSON file."""
        try:
            with open(self.overrides_file, 'w') as f:
                json.dump(self.overrides, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save overrides: {e}")

    def _cleanup_expired_overrides(self):
        """Remove overrides for past dates (not today - those are cleared on trigger/dismiss)."""
        now = self.rtc.get_time()
        yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')

        expired = []
        for override_id, override in self.overrides.items():
            target_date = override.get('target_date', '')
            if target_date <= yesterday:
                expired.append(override_id)

        for override_id in expired:
            del self.overrides[override_id]
            logger.info(f"Cleaned up expired override {override_id}")

        if expired:
            self._save_overrides()

    def get_all_overrides(self):
        """Get all overrides as a list."""
        with self._lock:
            return list(self.overrides.values())

    def get_override(self, override_id):
        """Get a specific override by ID."""
        with self._lock:
            return self.overrides.get(override_id)

    def get_override_for_alarm(self, alarm_id, target_date):
        """Get override for a specific alarm and date."""
        with self._lock:
            for override in self.overrides.values():
                if override['alarm_id'] == alarm_id and override['target_date'] == target_date:
                    return override
            return None

    def create_override(self, alarm_id, target_date, override_time=None, override_sound=None, skip=False):
        """Create a new override for an alarm instance."""
        with self._lock:
            if alarm_id not in self.alarms:
                return None

            # Check if override already exists for this alarm/date
            for override in self.overrides.values():
                if override['alarm_id'] == alarm_id and override['target_date'] == target_date:
                    return None  # Already exists

            override_id = str(uuid.uuid4())[:8]
            override = {
                'id': override_id,
                'alarm_id': alarm_id,
                'target_date': target_date,
                'override_time': override_time,
                'override_sound': override_sound,
                'skip': skip
            }

            self.overrides[override_id] = override
            self._save_overrides()
            logger.info(f"Created override {override_id} for alarm {alarm_id} on {target_date}")
            return override

    def update_override(self, override_id, data):
        """Update an existing override."""
        with self._lock:
            if override_id not in self.overrides:
                return None

            override = self.overrides[override_id]

            if 'override_time' in data:
                override['override_time'] = data['override_time']
            if 'override_sound' in data:
                override['override_sound'] = data['override_sound']
            if 'skip' in data:
                override['skip'] = data['skip']

            self._save_overrides()
            logger.info(f"Updated override {override_id}")
            return override

    def delete_override(self, override_id):
        """Delete an override (restore original)."""
        with self._lock:
            if override_id not in self.overrides:
                return False

            del self.overrides[override_id]
            self._save_overrides()
            logger.info(f"Deleted override {override_id}")
            return True

    def _delete_overrides_for_alarm(self, alarm_id):
        """Delete all overrides for a specific alarm."""
        to_delete = [oid for oid, o in self.overrides.items() if o['alarm_id'] == alarm_id]
        for override_id in to_delete:
            del self.overrides[override_id]
        if to_delete:
            self._save_overrides()
            logger.info(f"Deleted {len(to_delete)} overrides for alarm {alarm_id}")

    def get_all_alarms(self):
        """Get all alarms as a list."""
        with self._lock:
            return list(self.alarms.values())

    def get_alarm(self, alarm_id):
        """Get a specific alarm by ID."""
        with self._lock:
            return self.alarms.get(alarm_id)

    def create_alarm(self, time, days, sound='default.mp3', enabled=True, label=''):
        """Create a new alarm."""
        alarm_id = str(uuid.uuid4())[:8]

        # Normalize days to lowercase list
        if isinstance(days, str):
            days = [days]
        days = [d.lower() for d in days]

        alarm = {
            'id': alarm_id,
            'time': time,
            'days': days,
            'sound': sound,
            'enabled': enabled,
            'label': label
        }

        with self._lock:
            self.alarms[alarm_id] = alarm
            self._save_alarms()

        logger.info(f"Created alarm {alarm_id}: {time} on {days}")
        return alarm

    def update_alarm(self, alarm_id, data):
        """Update an existing alarm."""
        with self._lock:
            if alarm_id not in self.alarms:
                return None

            alarm = self.alarms[alarm_id]

            if 'time' in data:
                alarm['time'] = data['time']
            if 'days' in data:
                days = data['days']
                if isinstance(days, str):
                    days = [days]
                alarm['days'] = [d.lower() for d in days]
            if 'sound' in data:
                alarm['sound'] = data['sound']
            if 'enabled' in data:
                alarm['enabled'] = data['enabled']
            if 'label' in data:
                alarm['label'] = data['label']

            self._save_alarms()
            logger.info(f"Updated alarm {alarm_id}")
            return alarm

    def delete_alarm(self, alarm_id):
        """Delete an alarm."""
        with self._lock:
            if alarm_id not in self.alarms:
                return False

            del self.alarms[alarm_id]
            self._save_alarms()
            self._delete_overrides_for_alarm(alarm_id)
            logger.info(f"Deleted alarm {alarm_id}")
            return True

    def toggle_alarm(self, alarm_id):
        """Toggle an alarm's enabled state."""
        with self._lock:
            if alarm_id not in self.alarms:
                return None

            alarm = self.alarms[alarm_id]
            alarm['enabled'] = not alarm['enabled']
            self._save_alarms()
            logger.info(f"Toggled alarm {alarm_id} to {alarm['enabled']}")
            return alarm

    def is_ringing(self):
        """Check if an alarm is currently ringing."""
        return self._ringing

    def snooze(self):
        """Snooze the currently ringing alarm."""
        if not self._ringing:
            return

        self._snooze_until = self.rtc.get_time() + timedelta(minutes=self.snooze_minutes)
        self._ringing = False
        self.audio_player.stop()
        self.display.set_alarm_indicator(False)
        logger.info(f"Alarm snoozed until {self._snooze_until.strftime('%H:%M')}")

    def dismiss(self):
        """Dismiss the currently ringing alarm."""
        if not self._ringing:
            return

        # Clear the override that was used for this alarm instance
        if self._ringing_override_id:
            self.delete_override(self._ringing_override_id)

        self._ringing = False
        self._ringing_alarm_id = None
        self._ringing_override_id = None
        self._ringing_since = None
        self._snooze_until = None
        self.audio_player.stop()
        self.display.set_alarm_indicator(False)
        logger.info("Alarm dismissed")

    def get_next_alarm_info(self):
        """Get information about the next upcoming alarm."""
        now = self.rtc.get_time()
        current_day = now.weekday()
        current_time = now.strftime('%H:%M')

        next_alarm = None
        min_minutes = float('inf')

        with self._lock:
            for alarm in self.alarms.values():
                if not alarm['enabled']:
                    continue

                for day_name in alarm['days']:
                    day_num = self.DAYS_MAP.get(day_name)
                    if day_num is None:
                        continue

                    # Calculate days until this alarm
                    days_until = (day_num - current_day) % 7

                    # Calculate target date for this instance
                    target_datetime = now + timedelta(days=days_until)
                    target_date = target_datetime.strftime('%Y-%m-%d')

                    # Check for override
                    override = None
                    for o in self.overrides.values():
                        if o['alarm_id'] == alarm['id'] and o['target_date'] == target_date:
                            override = o
                            break

                    # Get effective time (from override or original)
                    effective_time = override['override_time'] if override and override.get('override_time') else alarm['time']

                    # If it's today, check if the effective time has passed
                    if days_until == 0 and effective_time <= current_time:
                        days_until = 7
                        # Recalculate target date for next week
                        target_datetime = now + timedelta(days=days_until)
                        target_date = target_datetime.strftime('%Y-%m-%d')
                        # Re-check for override on the new date
                        override = None
                        for o in self.overrides.values():
                            if o['alarm_id'] == alarm['id'] and o['target_date'] == target_date:
                                override = o
                                break
                        effective_time = override['override_time'] if override and override.get('override_time') else alarm['time']

                    # Skip if override has skip flag
                    if override and override.get('skip'):
                        continue

                    # Calculate total minutes until alarm
                    alarm_hour, alarm_minute = map(int, effective_time.split(':'))
                    minutes_until = days_until * 24 * 60 + alarm_hour * 60 + alarm_minute
                    minutes_until -= now.hour * 60 + now.minute

                    if minutes_until < min_minutes:
                        min_minutes = minutes_until
                        next_alarm = {
                            'id': alarm['id'],
                            'time': effective_time,
                            'original_time': alarm['time'],
                            'day': day_name,
                            'label': alarm['label'],
                            'sound': override['override_sound'] if override and override.get('override_sound') else alarm['sound'],
                            'minutes_until': minutes_until,
                            'target_date': target_date,
                            'has_override': override is not None,
                            'override_id': override['id'] if override else None
                        }

        return next_alarm

    def _check_alarms(self):
        """Check if any alarm should be triggered."""
        now = self.rtc.get_time()
        current_day = now.weekday()
        current_time = now.strftime('%H:%M')
        today = now.strftime('%Y-%m-%d')

        # Check if we're in snooze period
        if self._snooze_until:
            if now >= self._snooze_until:
                # Snooze period ended, ring again
                self._snooze_until = None
                self._trigger_alarm(self._ringing_alarm_id, self._ringing_override_id)
            return

        # Auto-dismiss if alarm has been ringing too long
        if self._ringing and self._ringing_since:
            elapsed = (now - self._ringing_since).total_seconds() / 60
            if elapsed >= self.timeout_minutes:
                logger.info(f"Alarm timed out after {self.timeout_minutes} minutes, auto-dismissing")
                self.dismiss()
                return

        # Already ringing, don't check
        if self._ringing:
            return

        alarm_to_trigger = None
        with self._lock:
            for alarm_id, alarm in self.alarms.items():
                if not alarm['enabled']:
                    continue

                # Check if current day matches alarm days
                day_names = ['monday', 'tuesday', 'wednesday', 'thursday',
                           'friday', 'saturday', 'sunday']
                current_day_name = day_names[current_day]

                alarm_days = [d.lower() for d in alarm['days']]
                # Also check short day names
                short_day_names = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                current_short_day = short_day_names[current_day]

                if current_day_name not in alarm_days and current_short_day not in alarm_days:
                    continue

                # Check for override on today's date
                override = None
                for o in self.overrides.values():
                    if o['alarm_id'] == alarm_id and o['target_date'] == today:
                        override = o
                        break

                # Skip if override has skip flag
                if override and override.get('skip'):
                    continue

                # Get effective time (from override or original)
                effective_time = override['override_time'] if override and override.get('override_time') else alarm['time']

                # Check if current time matches effective alarm time
                if effective_time == current_time:
                    alarm_to_trigger = (alarm_id, override['id'] if override else None)
                    break

        if alarm_to_trigger:
            self._trigger_alarm(*alarm_to_trigger)

    def _trigger_alarm(self, alarm_id, override_id=None):
        """Trigger an alarm."""
        with self._lock:
            alarm = self.alarms.get(alarm_id)
            override = self.overrides.get(override_id) if override_id else None

        if not alarm:
            return

        # Get effective sound (from override or original)
        sound = override['override_sound'] if override and override.get('override_sound') else alarm['sound']

        logger.info(f"Triggering alarm {alarm_id}: {alarm['label'] or alarm['time']}")
        self._ringing = True
        self._ringing_alarm_id = alarm_id
        self._ringing_override_id = override_id
        self._ringing_since = self.rtc.get_time()
        self.display.set_alarm_indicator(True)
        self.audio_player.play(sound, loop=True)

    def _run(self):
        """Background thread that checks alarms."""
        logger.info("Alarm manager thread started")

        while self._running:
            try:
                self._check_alarms()
            except Exception as e:
                logger.error(f"Error checking alarms: {e}")

            # Sleep in small intervals to allow quick shutdown
            for _ in range(self.check_interval):
                if not self._running:
                    break
                threading.Event().wait(1)

        logger.info("Alarm manager thread stopped")

    def start(self):
        """Start the alarm manager background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the alarm manager."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self.dismiss()
