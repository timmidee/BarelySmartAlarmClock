#!/usr/bin/env python3
"""
Raspberry Pi Alarm Clock - Main Application
Flask server with REST API, alarm scheduling, and hardware control.
"""

import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from alarm_manager import AlarmManager
from audio import AudioPlayer
from buttons import ButtonHandler
from display import Display
from rtc import RTC

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__, static_folder='static')

# Global instances
alarm_manager = None
display = None
rtc = None
audio_player = None
button_handler = None


def load_config():
    """Load configuration from config.json or use defaults."""
    config_path = Path(__file__).parent / 'config.json'
    default_config = {
        'use_mock_hardware': True,
        'display_brightness': 10,
        'snooze_duration_minutes': 9,
        'alarm_check_interval_seconds': 30,
        'sounds_directory': 'sounds'
    }

    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            return {**default_config, **config}
    return default_config


# --- Static file routes ---

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


# --- REST API routes ---

@app.route('/api/alarms', methods=['GET'])
def get_alarms():
    """Get all alarms."""
    alarms = alarm_manager.get_all_alarms()
    return jsonify(alarms)


@app.route('/api/alarms', methods=['POST'])
def create_alarm():
    """Create a new alarm."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['time', 'days']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    alarm = alarm_manager.create_alarm(
        time=data['time'],
        days=data['days'],
        sound=data.get('sound', 'default.mp3'),
        enabled=data.get('enabled', True),
        label=data.get('label', '')
    )

    return jsonify(alarm), 201


@app.route('/api/alarms/<alarm_id>', methods=['GET'])
def get_alarm(alarm_id):
    """Get a specific alarm."""
    alarm = alarm_manager.get_alarm(alarm_id)
    if alarm is None:
        return jsonify({'error': 'Alarm not found'}), 404
    return jsonify(alarm)


@app.route('/api/alarms/<alarm_id>', methods=['PUT'])
def update_alarm(alarm_id):
    """Update an existing alarm."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    alarm = alarm_manager.update_alarm(alarm_id, data)
    if alarm is None:
        return jsonify({'error': 'Alarm not found'}), 404

    return jsonify(alarm)


@app.route('/api/alarms/<alarm_id>', methods=['DELETE'])
def delete_alarm(alarm_id):
    """Delete an alarm."""
    success = alarm_manager.delete_alarm(alarm_id)
    if not success:
        return jsonify({'error': 'Alarm not found'}), 404
    return jsonify({'message': 'Alarm deleted'}), 200


@app.route('/api/alarms/<alarm_id>/toggle', methods=['POST'])
def toggle_alarm(alarm_id):
    """Toggle an alarm's enabled state."""
    alarm = alarm_manager.toggle_alarm(alarm_id)
    if alarm is None:
        return jsonify({'error': 'Alarm not found'}), 404
    return jsonify(alarm)


# --- Override endpoints ---

@app.route('/api/overrides', methods=['GET'])
def get_overrides():
    """Get all active overrides."""
    overrides = alarm_manager.get_all_overrides()
    return jsonify(overrides)


@app.route('/api/overrides', methods=['POST'])
def create_override():
    """Create a new override for an alarm instance."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['alarm_id', 'target_date']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    override = alarm_manager.create_override(
        alarm_id=data['alarm_id'],
        target_date=data['target_date'],
        override_time=data.get('override_time'),
        override_sound=data.get('override_sound'),
        skip=data.get('skip', False)
    )

    if override is None:
        return jsonify({'error': 'Alarm not found or override already exists'}), 400

    return jsonify(override), 201


@app.route('/api/overrides/<override_id>', methods=['GET'])
def get_override(override_id):
    """Get a specific override."""
    override = alarm_manager.get_override(override_id)
    if override is None:
        return jsonify({'error': 'Override not found'}), 404
    return jsonify(override)


@app.route('/api/overrides/<override_id>', methods=['PUT'])
def update_override(override_id):
    """Update an existing override."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    override = alarm_manager.update_override(override_id, data)
    if override is None:
        return jsonify({'error': 'Override not found'}), 404

    return jsonify(override)


@app.route('/api/overrides/<override_id>', methods=['DELETE'])
def delete_override(override_id):
    """Delete an override (restore original)."""
    success = alarm_manager.delete_override(override_id)
    if not success:
        return jsonify({'error': 'Override not found'}), 404
    return jsonify({'message': 'Override deleted'}), 200


# --- Status and control endpoints ---

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current system status."""
    now = rtc.get_time()
    return jsonify({
        'time': now.strftime('%H:%M:%S'),
        'date': now.strftime('%Y-%m-%d'),
        'day': now.strftime('%A'),
        'alarm_ringing': alarm_manager.is_ringing(),
        'next_alarm': alarm_manager.get_next_alarm_info()
    })


@app.route('/api/snooze', methods=['POST'])
def snooze():
    """Snooze the currently ringing alarm."""
    if alarm_manager.is_ringing():
        alarm_manager.snooze()
        return jsonify({'message': 'Alarm snoozed'})
    return jsonify({'error': 'No alarm currently ringing'}), 400


@app.route('/api/dismiss', methods=['POST'])
def dismiss():
    """Dismiss the currently ringing alarm."""
    if alarm_manager.is_ringing():
        alarm_manager.dismiss()
        return jsonify({'message': 'Alarm dismissed'})
    return jsonify({'error': 'No alarm currently ringing'}), 400


@app.route('/api/sounds', methods=['GET'])
def get_sounds():
    """Get list of available alarm sounds."""
    sounds = audio_player.get_available_sounds()
    return jsonify(sounds)


@app.route('/api/sounds/preview/<sound_name>', methods=['POST'])
def preview_sound(sound_name):
    """Preview an alarm sound."""
    success = audio_player.preview(sound_name)
    if not success:
        return jsonify({'error': 'Sound not found'}), 404
    return jsonify({'message': 'Playing preview'})


@app.route('/api/sounds/stop', methods=['POST'])
def stop_sound():
    """Stop any playing sound."""
    audio_player.stop()
    return jsonify({'message': 'Sound stopped'})


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings."""
    config_path = Path(__file__).parent / 'config.json'
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}

    return jsonify({
        'display_brightness': config.get('display_brightness', 10),
        'snooze_duration_minutes': config.get('snooze_duration_minutes', 9),
        'volume': config.get('volume', 80),
        'default_sound': config.get('default_sound', '')
    })


@app.route('/api/settings', methods=['PUT'])
def update_settings():
    """Update settings."""
    data = request.get_json()
    config_path = Path(__file__).parent / 'config.json'

    # Load existing config
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}

    # Update brightness
    if 'display_brightness' in data:
        brightness = max(0, min(15, int(data['display_brightness'])))
        config['display_brightness'] = brightness
        display.set_brightness(brightness)

    # Update snooze duration
    if 'snooze_duration_minutes' in data:
        snooze = max(1, min(30, int(data['snooze_duration_minutes'])))
        config['snooze_duration_minutes'] = snooze
        alarm_manager.snooze_minutes = snooze

    # Update volume
    if 'volume' in data:
        volume = max(0, min(100, int(data['volume'])))
        config['volume'] = volume
        audio_player.set_volume(volume)

    # Update default sound
    if 'default_sound' in data:
        config['default_sound'] = data['default_sound']

    # Save config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

    return jsonify({
        'display_brightness': config.get('display_brightness', 10),
        'snooze_duration_minutes': config.get('snooze_duration_minutes', 9),
        'volume': config.get('volume', 80),
        'default_sound': config.get('default_sound', '')
    })


# --- Initialization and shutdown ---

def init_hardware(config):
    """Initialize hardware components (or mocks)."""
    global display, rtc, audio_player, button_handler, alarm_manager

    use_mock = config.get('use_mock_hardware', True)

    display = Display(mock=use_mock)
    rtc = RTC(mock=use_mock)
    audio_player = AudioPlayer(sounds_dir=config.get('sounds_directory', 'sounds'))

    alarm_manager = AlarmManager(
        rtc=rtc,
        audio_player=audio_player,
        display=display,
        snooze_minutes=config.get('snooze_duration_minutes', 9),
        check_interval=config.get('alarm_check_interval_seconds', 30)
    )

    button_handler = ButtonHandler(
        mock=use_mock,
        on_snooze=alarm_manager.snooze,
        on_dismiss=alarm_manager.dismiss
    )

    display.set_brightness(config.get('display_brightness', 10))
    audio_player.set_volume(config.get('volume', 80))

    logger.info(f"Hardware initialized (mock={use_mock})")


def start_background_threads():
    """Start all background threads."""
    alarm_manager.start()
    display.start()
    button_handler.start()
    logger.info("Background threads started")


def shutdown(signum=None, frame=None):
    """Clean shutdown of all components."""
    logger.info("Shutting down...")

    if alarm_manager:
        alarm_manager.stop()
    if display:
        display.stop()
    if button_handler:
        button_handler.stop()
    if audio_player:
        audio_player.stop()

    logger.info("Shutdown complete")
    sys.exit(0)


def main():
    """Main entry point."""
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    config = load_config()
    init_hardware(config)
    start_background_threads()

    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
