#!/bin/bash
# Test script to verify USB audio output

echo "=== Audio Device Check ==="
echo ""
echo "Available audio devices:"
aplay -l
echo ""

echo "=== Audio Test ==="
echo "Playing test tone (2 seconds)..."
speaker-test -t sine -f 440 -l 1 -p 2 2>/dev/null || {
    echo "speaker-test failed. Trying alternate method..."
    timeout 2 speaker-test -t wav -c 2 2>/dev/null || echo "Audio test failed. Check speaker connection."
}

echo ""
echo "If no sound was heard:"
echo "  1. Check USB speaker connection"
echo "  2. Set audio output: sudo raspi-config → System Options → Audio"
echo "  3. Install audio tools: sudo apt install alsa-utils mpg123"
