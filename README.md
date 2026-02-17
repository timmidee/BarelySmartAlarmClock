# Raspberry Pi Alarm Clock

A bedside alarm clock built on a Raspberry Pi Zero 2 W with a retro 7-segment LED display, physical snooze/dismiss buttons, and a web interface for configuration.

## Features

- **7-segment LED display** showing the current time
- **Multiple alarms** with individual day selection (any combination of days)
- **Web interface** for managing alarms from your phone or computer
- **Physical buttons** for snooze and dismiss
- **Audio playback** through USB speakers
- **Battery-backed RTC** keeps time during power loss
- **Mock mode** for development/testing without hardware

## Hardware

| Component | Description |
|-----------|-------------|
| Raspberry Pi Zero 2 W | Main controller |
| Adafruit 1.2" 4-digit 7-segment display | I2C, HT16K33 driver |
| DS3231 RTC module | I2C, battery backup |
| USB speakers | Alarm audio output |
| Micro USB OTG hub | Expands single USB port |
| Tactile push buttons (x2) | Snooze and dismiss |

See [wiring/WIRING.md](wiring/WIRING.md) for detailed wiring instructions and test scripts.

## Project Structure

```
alarmclock/
├── app.py              # Flask server with REST API
├── alarm_manager.py    # Alarm storage, scheduling, triggering
├── display.py          # 7-segment display controller
├── rtc.py              # Real-time clock interface
├── audio.py            # Sound playback
├── buttons.py          # GPIO button handling
├── config.json         # Configuration settings
├── alarms.json         # Alarm data storage
├── requirements.txt    # Python dependencies
├── wiring/             # Hardware wiring guide and test scripts
├── static/
│   ├── index.html      # Web UI
│   ├── style.css       # Styles (dark theme, mobile-friendly)
│   └── app.js          # Frontend JavaScript
└── sounds/             # Alarm sound files (MP3, WAV, OGG, FLAC)
```

## Quick Start (Local Testing)

Run on any machine without hardware using mock mode:

```bash
cd alarmclock
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install flask
python app.py
```

Open http://localhost:8080 in your browser.

## Raspberry Pi Setup

### 1. Install Raspberry Pi OS Lite

Use Raspberry Pi Imager to flash Raspberry Pi OS Lite (64-bit) to your SD card. Enable SSH and configure WiFi in the imager settings.

### 2. Enable I2C

```bash
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable
sudo reboot
```

### 3. Install Dependencies

```bash
sudo apt update
sudo apt install python3-pip python3-venv i2c-tools mpg123

# Create virtual environment
python3 -m venv ~/alarmclock/clockenv
source ~/alarmclock/clockenv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### 4. Copy Project Files

Copy all project files to the Pi (replace `pi@raspberrypi.local` with your Pi's address):

```bash
scp -r /path/to/alarmclock pi@raspberrypi.local:~/alarmclock
```

### 5. Configure for Real Hardware

Edit `config.json`:

```json
{
    "use_mock_hardware": false,
    "display_brightness": 10,
    "snooze_duration_minutes": 9,
    "alarm_check_interval_seconds": 30,
    "sounds_directory": "sounds"
}
```

### 6. Add Alarm Sounds

Copy MP3, WAV, OGG, or FLAC files to the `sounds/` directory.

### 7. Wire the Hardware

Follow the instructions in [wiring/WIRING.md](wiring/WIRING.md) and use the test scripts to verify each component.

### 8. Verify I2C Devices

```bash
i2cdetect -y 1
```

You should see devices at addresses `0x68` (RTC) and `0x70` (display).

### 9. Run the Application

```bash
source ~/alarmclock/clockenv/bin/activate
cd ~/alarmclock
python app.py
```

Access the web UI at `http://<pi-ip>:5000`

## Run on Boot (systemd)

Create `/etc/systemd/system/alarmclock.service`:

```ini
[Unit]
Description=Alarm Clock
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/alarmclock
Environment=PATH=/home/pi/alarmclock/clockenv/bin
ExecStart=/home/pi/alarmclock/clockenv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable alarmclock
sudo systemctl start alarmclock
```

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alarms` | GET | List all alarms |
| `/api/alarms` | POST | Create alarm |
| `/api/alarms/<id>` | GET | Get alarm |
| `/api/alarms/<id>` | PUT | Update alarm |
| `/api/alarms/<id>` | DELETE | Delete alarm |
| `/api/alarms/<id>/toggle` | POST | Toggle enabled |
| `/api/status` | GET | System status |
| `/api/snooze` | POST | Snooze ringing alarm |
| `/api/dismiss` | POST | Dismiss ringing alarm |
| `/api/sounds` | GET | List available sounds |
| `/api/sounds/preview/<name>` | POST | Preview a sound |
| `/api/sounds/stop` | POST | Stop playing sound |

## Configuration

`config.json` options:

| Option | Default | Description |
|--------|---------|-------------|
| `use_mock_hardware` | `true` | Use mock hardware for testing |
| `display_brightness` | `10` | Display brightness (0-15) |
| `snooze_duration_minutes` | `9` | Snooze duration |
| `alarm_check_interval_seconds` | `30` | How often to check alarms |
| `sounds_directory` | `"sounds"` | Directory containing alarm sounds |

## Troubleshooting

### I2C devices not detected
- Check wiring connections
- Verify I2C is enabled: `sudo raspi-config`
- Ensure 3.3V power is reaching devices

### No audio
- Check USB speaker connection: `aplay -l`
- Install audio player: `sudo apt install mpg123`
- Set audio output: `sudo raspi-config` → System Options → Audio

### Display shows wrong time
- Check RTC battery (CR2032)
- Sync RTC from system time (automatic on startup with internet)