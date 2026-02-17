"""
Audio Module - Handles alarm sound playback.
Uses subprocess to play audio files through USB speakers.
"""

import logging
import os
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Audio player for alarm sounds."""

    SUPPORTED_FORMATS = ['.mp3', '.wav', '.ogg', '.flac']

    def __init__(self, sounds_dir='sounds'):
        self.sounds_dir = Path(__file__).parent / sounds_dir
        self._process = None
        self._playing = False
        self._loop = False
        self._loop_thread = None
        self._stop_event = threading.Event()
        self._volume = 80  # 0-100

        # Create sounds directory if it doesn't exist
        self.sounds_dir.mkdir(exist_ok=True)

        # Create a default sound if none exists
        self._ensure_default_sound()

        logger.info(f"Audio player initialized, sounds directory: {self.sounds_dir}")

    def set_volume(self, volume):
        """Set volume level (0-100)."""
        self._volume = max(0, min(100, volume))
        # Try to set system volume via amixer (Linux/Raspberry Pi)
        try:
            subprocess.run(
                ['amixer', 'sset', 'Master', f'{self._volume}%'],
                capture_output=True,
                timeout=2
            )
            logger.info(f"Volume set to {self._volume}%")
        except Exception as e:
            logger.debug(f"Could not set system volume: {e}")

    def get_volume(self):
        """Get current volume level."""
        return self._volume

    def _ensure_default_sound(self):
        """Create a default alarm sound file if none exists."""
        default_path = self.sounds_dir / 'default.mp3'
        if not default_path.exists() and not list(self.sounds_dir.glob('*')):
            # No sounds exist - create a placeholder text file as a reminder
            placeholder = self.sounds_dir / 'ADD_SOUNDS_HERE.txt'
            placeholder.write_text(
                "Add MP3, WAV, OGG, or FLAC audio files to this directory.\n"
                "The first file alphabetically will be used as the default sound.\n"
            )
            logger.warning("No alarm sounds found. Add audio files to the sounds directory.")

    def get_available_sounds(self):
        """Get list of available alarm sounds."""
        sounds = []
        for ext in self.SUPPORTED_FORMATS:
            for path in self.sounds_dir.glob(f'*{ext}'):
                sounds.append({
                    'name': path.name,
                    'path': str(path)
                })

        sounds.sort(key=lambda x: x['name'])
        return sounds

    def _find_sound_file(self, sound_name):
        """Find the full path to a sound file."""
        # Try exact match first
        sound_path = self.sounds_dir / sound_name
        if sound_path.exists():
            return sound_path

        # Try without extension
        for ext in self.SUPPORTED_FORMATS:
            sound_path = self.sounds_dir / f"{sound_name}{ext}"
            if sound_path.exists():
                return sound_path

        # Fall back to first available sound
        sounds = self.get_available_sounds()
        if sounds:
            return Path(sounds[0]['path'])

        return None

    def _get_player_command(self, sound_path):
        """Get the appropriate command to play audio based on available players."""
        # Try different audio players in order of preference
        players = [
            ['mpg123', '-q'],  # Good for MP3
            ['aplay'],  # ALSA player for WAV
            ['paplay'],  # PulseAudio player
            ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet'],  # FFmpeg
            ['cvlc', '--play-and-exit', '--no-video'],  # VLC
        ]

        for player_cmd in players:
            try:
                # Check if player exists
                subprocess.run(
                    ['which', player_cmd[0]],
                    capture_output=True,
                    check=True
                )
                return player_cmd + [str(sound_path)]
            except subprocess.CalledProcessError:
                continue

        logger.warning("No audio player found. Install mpg123, aplay, or ffplay.")
        return None

    def play(self, sound_name, loop=False):
        """Play an alarm sound."""
        self.stop()

        sound_path = self._find_sound_file(sound_name)
        if not sound_path:
            logger.error(f"Sound not found: {sound_name}")
            return False

        cmd = self._get_player_command(sound_path)
        if not cmd:
            logger.error("No audio player available")
            return False

        self._playing = True
        self._loop = loop
        self._stop_event.clear()

        if loop:
            self._loop_thread = threading.Thread(
                target=self._play_loop,
                args=(cmd,),
                daemon=True
            )
            self._loop_thread.start()
        else:
            self._start_playback(cmd)

        logger.info(f"Playing {'(loop)' if loop else ''}: {sound_path.name}")
        return True

    def _start_playback(self, cmd):
        """Start audio playback subprocess."""
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.error(f"Failed to start audio playback: {e}")
            self._playing = False

    def _play_loop(self, cmd):
        """Play audio in a loop until stopped."""
        while self._playing and not self._stop_event.is_set():
            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                # Wait for playback to finish or stop signal
                while self._process.poll() is None:
                    if self._stop_event.wait(timeout=0.1):
                        self._process.terminate()
                        return

            except Exception as e:
                logger.error(f"Error in playback loop: {e}")
                break

        self._playing = False

    def preview(self, sound_name):
        """Preview a sound (play once, not looped)."""
        return self.play(sound_name, loop=False)

    def stop(self):
        """Stop any playing audio."""
        self._playing = False
        self._stop_event.set()

        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except Exception as e:
                logger.error(f"Error stopping audio: {e}")
            finally:
                self._process = None

        if self._loop_thread:
            self._loop_thread.join(timeout=1)
            self._loop_thread = None

        logger.debug("Audio stopped")

    def is_playing(self):
        """Check if audio is currently playing."""
        return self._playing
