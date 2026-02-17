// Alarm Clock Web UI

const API_BASE = '/api';
let alarms = [];
let sounds = [];
let settings = {};
let deleteAlarmId = null;
let isPreviewPlaying = false;
let nextAlarmInfo = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initDayButtons();
    loadAlarms();
    loadSounds();
    loadSettings();
    updateClock();
    checkStatus();
    setInterval(updateClock, 1000);
    setInterval(checkStatus, 5000);
});

// Clock display
function updateClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    document.getElementById('clock').textContent = `${hours}:${minutes}`;

    const options = { weekday: 'long', month: 'long', day: 'numeric' };
    document.getElementById('date').textContent = now.toLocaleDateString('en-US', options);
}

// Check system status
async function checkStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const status = await response.json();

        // Update alarm ringing state
        const ringingEl = document.getElementById('alarm-ringing');
        if (status.alarm_ringing) {
            ringingEl.classList.remove('hidden');
        } else {
            ringingEl.classList.add('hidden');
        }

        // Store and update next alarm info
        nextAlarmInfo = status.next_alarm;
        updateNextAlarmBanner();
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

// Update next alarm banner
function updateNextAlarmBanner() {
    const banner = document.getElementById('next-alarm-banner');
    const timeEl = document.getElementById('next-alarm-time');
    const labelEl = document.getElementById('next-alarm-label');
    const countdownEl = document.getElementById('next-alarm-countdown');
    const badgeEl = document.getElementById('next-alarm-badge');

    if (!nextAlarmInfo) {
        banner.classList.add('no-alarm');
        banner.onclick = null;
        timeEl.textContent = 'No alarms';
        labelEl.textContent = '';
        countdownEl.textContent = '';
        badgeEl.classList.add('hidden');
        document.querySelector('.next-alarm-chevron').classList.add('hidden');
        return;
    }

    banner.classList.remove('no-alarm');
    banner.onclick = editNextAlarm;
    document.querySelector('.next-alarm-chevron').classList.remove('hidden');

    // Display time
    timeEl.textContent = nextAlarmInfo.time;

    // Display label and day
    const dayNames = {
        mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday', thu: 'Thursday',
        fri: 'Friday', sat: 'Saturday', sun: 'Sunday',
        monday: 'Monday', tuesday: 'Tuesday', wednesday: 'Wednesday',
        thursday: 'Thursday', friday: 'Friday', saturday: 'Saturday', sunday: 'Sunday'
    };
    const dayName = dayNames[nextAlarmInfo.day.toLowerCase()] || nextAlarmInfo.day;
    const labelText = nextAlarmInfo.label ? `${nextAlarmInfo.label} · ${dayName}` : dayName;
    labelEl.textContent = labelText;

    // Display countdown
    const mins = nextAlarmInfo.minutes_until;
    let timeStr;
    if (mins < 60) {
        timeStr = `in ${mins} minute${mins !== 1 ? 's' : ''}`;
    } else if (mins < 1440) {
        const hours = Math.floor(mins / 60);
        const remainingMins = mins % 60;
        if (remainingMins > 0) {
            timeStr = `in ${hours}h ${remainingMins}m`;
        } else {
            timeStr = `in ${hours} hour${hours !== 1 ? 's' : ''}`;
        }
    } else {
        const days = Math.floor(mins / 1440);
        const remainingHours = Math.floor((mins % 1440) / 60);
        if (remainingHours > 0) {
            timeStr = `in ${days}d ${remainingHours}h`;
        } else {
            timeStr = `in ${days} day${days !== 1 ? 's' : ''}`;
        }
    }
    countdownEl.textContent = timeStr;

    // Show/hide modified badge
    if (nextAlarmInfo.has_override) {
        badgeEl.classList.remove('hidden');
    } else {
        badgeEl.classList.add('hidden');
    }
}

// Load alarms
async function loadAlarms() {
    try {
        const response = await fetch(`${API_BASE}/alarms`);
        alarms = await response.json();
        renderAlarms();
    } catch (error) {
        console.error('Error loading alarms:', error);
        document.getElementById('alarms-list').innerHTML =
            '<div class="loading">Failed to load alarms</div>';
    }
}

// Load available sounds
async function loadSounds() {
    try {
        const response = await fetch(`${API_BASE}/sounds`);
        sounds = await response.json();
        updateSoundSelector();
    } catch (error) {
        console.error('Error loading sounds:', error);
    }
}

function updateSoundSelector() {
    const select = document.getElementById('alarm-sound');
    select.innerHTML = '';

    if (sounds.length === 0) {
        select.innerHTML = '<option value="default.mp3">Default</option>';
        return;
    }

    sounds.forEach(sound => {
        const option = document.createElement('option');
        option.value = sound.name;
        option.textContent = sound.name.replace(/\.[^/.]+$/, ''); // Remove extension
        select.appendChild(option);
    });
}

// Render alarms list
function renderAlarms() {
    const container = document.getElementById('alarms-list');

    if (alarms.length === 0) {
        container.innerHTML = `
            <div class="no-alarms">
                <p>No alarms set</p>
                <button class="btn btn-add" onclick="showAddAlarm()">Add your first alarm</button>
            </div>
        `;
        return;
    }

    // Sort by time
    const sorted = [...alarms].sort((a, b) => a.time.localeCompare(b.time));

    container.innerHTML = sorted.map(alarm => `
        <div class="alarm-card ${alarm.enabled ? '' : 'disabled'}">
            <div class="alarm-info" onclick="editAlarm('${alarm.id}')">
                <div class="alarm-time">${alarm.time}</div>
                ${alarm.label ? `<div class="alarm-label">${escapeHtml(alarm.label)}</div>` : ''}
                <div class="alarm-days">${formatDays(alarm.days)}</div>
            </div>
            <label class="toggle">
                <input type="checkbox" ${alarm.enabled ? 'checked' : ''}
                       onchange="toggleAlarm('${alarm.id}')">
                <span class="toggle-slider"></span>
            </label>
            <button class="btn-delete-alarm" onclick="showDeleteModal('${alarm.id}')" title="Delete">
                🗑
            </button>
        </div>
    `).join('');
}

function formatDays(days) {
    if (!days || days.length === 0) return 'No days selected';

    const dayOrder = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
    const dayNames = {
        mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu',
        fri: 'Fri', sat: 'Sat', sun: 'Sun'
    };

    const sortedDays = days
        .map(d => d.toLowerCase().substring(0, 3))
        .sort((a, b) => dayOrder.indexOf(a) - dayOrder.indexOf(b));

    // Check for common patterns
    const weekdays = ['mon', 'tue', 'wed', 'thu', 'fri'];
    const weekend = ['sat', 'sun'];
    const everyday = [...weekdays, ...weekend];

    if (sortedDays.length === 7) return 'Every day';
    if (sortedDays.length === 5 && weekdays.every(d => sortedDays.includes(d))) return 'Weekdays';
    if (sortedDays.length === 2 && weekend.every(d => sortedDays.includes(d))) return 'Weekends';

    return sortedDays.map(d => dayNames[d]).join(', ');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Toggle alarm enabled state
async function toggleAlarm(id) {
    try {
        const response = await fetch(`${API_BASE}/alarms/${id}/toggle`, { method: 'POST' });
        const alarm = await response.json();

        const index = alarms.findIndex(a => a.id === id);
        if (index !== -1) {
            alarms[index] = alarm;
            renderAlarms();
        }
    } catch (error) {
        console.error('Error toggling alarm:', error);
        loadAlarms(); // Reload on error
    }
}

// Day buttons
function initDayButtons() {
    document.querySelectorAll('.day-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.classList.toggle('selected');
        });
    });
}

function getSelectedDays() {
    return Array.from(document.querySelectorAll('.day-btn.selected'))
        .map(btn => btn.dataset.day);
}

function setSelectedDays(days) {
    document.querySelectorAll('.day-btn').forEach(btn => {
        const day = btn.dataset.day;
        btn.classList.toggle('selected', days.some(d =>
            d.toLowerCase().startsWith(day)
        ));
    });
}

function selectWeekdays() {
    document.querySelectorAll('.day-btn').forEach(btn => {
        const isWeekday = ['mon', 'tue', 'wed', 'thu', 'fri'].includes(btn.dataset.day);
        btn.classList.toggle('selected', isWeekday);
    });
}

function selectWeekends() {
    document.querySelectorAll('.day-btn').forEach(btn => {
        const isWeekend = ['sat', 'sun'].includes(btn.dataset.day);
        btn.classList.toggle('selected', isWeekend);
    });
}

function selectAll() {
    document.querySelectorAll('.day-btn').forEach(btn => {
        btn.classList.add('selected');
    });
}

// Modal handling
function showAddAlarm() {
    document.getElementById('modal-title').textContent = 'Add Alarm';
    document.getElementById('alarm-id').value = '';
    document.getElementById('alarm-time').value = '07:00';
    document.getElementById('alarm-label').value = '';
    setSelectedDays(['mon', 'tue', 'wed', 'thu', 'fri']);
    // Use default sound from settings, or first available sound
    const defaultSound = settings.default_sound || sounds[0]?.name || 'default.mp3';
    document.getElementById('alarm-sound').value = defaultSound;
    document.getElementById('alarm-modal').classList.remove('hidden');
}

function editAlarm(id) {
    const alarm = alarms.find(a => a.id === id);
    if (!alarm) return;

    document.getElementById('modal-title').textContent = 'Edit Alarm';
    document.getElementById('alarm-id').value = alarm.id;
    document.getElementById('alarm-time').value = alarm.time;
    document.getElementById('alarm-label').value = alarm.label || '';
    setSelectedDays(alarm.days);
    document.getElementById('alarm-sound').value = alarm.sound;
    document.getElementById('alarm-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('alarm-modal').classList.add('hidden');
    stopPreview();
}

// Save alarm
async function saveAlarm(event) {
    event.preventDefault();

    const id = document.getElementById('alarm-id').value;
    const time = document.getElementById('alarm-time').value;
    const label = document.getElementById('alarm-label').value.trim();
    const days = getSelectedDays();
    const sound = document.getElementById('alarm-sound').value;

    if (days.length === 0) {
        alert('Please select at least one day');
        return;
    }

    const data = { time, days, sound, label, enabled: true };

    try {
        let response;
        if (id) {
            response = await fetch(`${API_BASE}/alarms/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } else {
            response = await fetch(`${API_BASE}/alarms`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }

        if (response.ok) {
            closeModal();
            loadAlarms();
            checkStatus();
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to save alarm');
        }
    } catch (error) {
        console.error('Error saving alarm:', error);
        alert('Failed to save alarm');
    }
}

// Delete alarm
function showDeleteModal(id) {
    deleteAlarmId = id;
    document.getElementById('delete-modal').classList.remove('hidden');
}

function closeDeleteModal() {
    deleteAlarmId = null;
    document.getElementById('delete-modal').classList.add('hidden');
}

async function confirmDelete() {
    if (!deleteAlarmId) return;

    try {
        const response = await fetch(`${API_BASE}/alarms/${deleteAlarmId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            closeDeleteModal();
            loadAlarms();
            checkStatus();
        }
    } catch (error) {
        console.error('Error deleting alarm:', error);
    }
}

// Sound preview
async function previewSound() {
    if (isPreviewPlaying) {
        stopPreview();
        return;
    }

    const sound = document.getElementById('alarm-sound').value;
    try {
        await fetch(`${API_BASE}/sounds/preview/${encodeURIComponent(sound)}`, {
            method: 'POST'
        });
        isPreviewPlaying = true;
        document.querySelector('.btn-preview').textContent = '⏹';
    } catch (error) {
        console.error('Error previewing sound:', error);
    }
}

async function stopPreview() {
    if (!isPreviewPlaying) return;

    try {
        await fetch(`${API_BASE}/sounds/stop`, { method: 'POST' });
    } catch (error) {
        console.error('Error stopping preview:', error);
    }
    isPreviewPlaying = false;
    document.querySelector('.btn-preview').textContent = '▶';
}

// Snooze and dismiss
async function snoozeAlarm() {
    try {
        await fetch(`${API_BASE}/snooze`, { method: 'POST' });
        checkStatus();
    } catch (error) {
        console.error('Error snoozing alarm:', error);
    }
}

async function dismissAlarm() {
    try {
        await fetch(`${API_BASE}/dismiss`, { method: 'POST' });
        checkStatus();
    } catch (error) {
        console.error('Error dismissing alarm:', error);
    }
}

// Settings
async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/settings`);
        settings = await response.json();
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

function showSettings() {
    // Populate sound selector
    const soundSelect = document.getElementById('setting-sound');
    soundSelect.innerHTML = '<option value="">Select a sound...</option>';
    sounds.forEach(sound => {
        const option = document.createElement('option');
        option.value = sound.name;
        option.textContent = sound.name.replace(/\.[^/.]+$/, '');
        if (sound.name === settings.default_sound) {
            option.selected = true;
        }
        soundSelect.appendChild(option);
    });

    document.getElementById('setting-volume').value = settings.volume || 80;
    document.getElementById('volume-value').textContent = (settings.volume || 80) + '%';
    document.getElementById('setting-brightness').value = settings.display_brightness || 10;
    document.getElementById('brightness-value').textContent = settings.display_brightness || 10;
    document.getElementById('setting-snooze').value = settings.snooze_duration_minutes || 9;
    document.getElementById('settings-modal').classList.remove('hidden');

    // Update slider displays on change
    document.getElementById('setting-brightness').oninput = (e) => {
        document.getElementById('brightness-value').textContent = e.target.value;
    };
    document.getElementById('setting-volume').oninput = (e) => {
        document.getElementById('volume-value').textContent = e.target.value + '%';
    };
}

function closeSettings() {
    document.getElementById('settings-modal').classList.add('hidden');
}

async function saveSettings(event) {
    event.preventDefault();

    const newSettings = {
        volume: parseInt(document.getElementById('setting-volume').value),
        default_sound: document.getElementById('setting-sound').value,
        snooze_duration_minutes: parseInt(document.getElementById('setting-snooze').value),
        display_brightness: parseInt(document.getElementById('setting-brightness').value)
    };

    try {
        const response = await fetch(`${API_BASE}/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newSettings)
        });

        if (response.ok) {
            settings = await response.json();
            closeSettings();
        } else {
            alert('Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Failed to save settings');
    }
}

async function previewSettingsSound() {
    const sound = document.getElementById('setting-sound').value;
    if (!sound) {
        alert('Select a sound first');
        return;
    }

    if (isPreviewPlaying) {
        stopPreview();
        return;
    }

    try {
        await fetch(`${API_BASE}/sounds/preview/${encodeURIComponent(sound)}`, {
            method: 'POST'
        });
        isPreviewPlaying = true;
    } catch (error) {
        console.error('Error previewing sound:', error);
    }
}

// Instance modal functions
function editNextAlarm() {
    if (!nextAlarmInfo) return;

    // Populate sound selector
    const soundSelect = document.getElementById('instance-sound');
    soundSelect.innerHTML = '<option value="">Use default</option>';
    sounds.forEach(sound => {
        const option = document.createElement('option');
        option.value = sound.name;
        option.textContent = sound.name.replace(/\.[^/.]+$/, '');
        soundSelect.appendChild(option);
    });

    // Format date for display
    const targetDate = new Date(nextAlarmInfo.target_date + 'T00:00:00');
    const options = { weekday: 'long', month: 'long', day: 'numeric' };
    document.getElementById('instance-date').textContent = targetDate.toLocaleDateString('en-US', options);

    // Show label
    document.getElementById('instance-label').textContent = nextAlarmInfo.label || '';

    // Set time (use current effective time)
    document.getElementById('instance-time').value = nextAlarmInfo.time;

    // Show original time if modified
    const originalEl = document.getElementById('instance-original');
    if (nextAlarmInfo.has_override && nextAlarmInfo.original_time !== nextAlarmInfo.time) {
        originalEl.textContent = `Original time: ${nextAlarmInfo.original_time}`;
        originalEl.classList.remove('hidden');
    } else {
        originalEl.textContent = `Recurring time: ${nextAlarmInfo.original_time}`;
        originalEl.classList.remove('hidden');
    }

    // Set sound if override exists
    if (nextAlarmInfo.has_override && nextAlarmInfo.sound) {
        soundSelect.value = nextAlarmInfo.sound;
    }

    // Show/hide restore button
    const restoreBtn = document.getElementById('btn-restore');
    if (nextAlarmInfo.has_override) {
        restoreBtn.classList.remove('hidden');
    } else {
        restoreBtn.classList.add('hidden');
    }

    document.getElementById('instance-modal').classList.remove('hidden');
}

function closeInstanceModal() {
    document.getElementById('instance-modal').classList.add('hidden');
    stopPreview();
}

async function saveInstance(event) {
    event.preventDefault();

    if (!nextAlarmInfo) return;

    const time = document.getElementById('instance-time').value;
    const sound = document.getElementById('instance-sound').value || null;

    const data = {
        alarm_id: nextAlarmInfo.id,
        target_date: nextAlarmInfo.target_date,
        override_time: time,
        override_sound: sound,
        skip: false
    };

    try {
        let response;
        if (nextAlarmInfo.override_id) {
            // Update existing override
            response = await fetch(`${API_BASE}/overrides/${nextAlarmInfo.override_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    override_time: time,
                    override_sound: sound,
                    skip: false
                })
            });
        } else {
            // Create new override
            response = await fetch(`${API_BASE}/overrides`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }

        if (response.ok) {
            closeInstanceModal();
            checkStatus();
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to save changes');
        }
    } catch (error) {
        console.error('Error saving instance:', error);
        alert('Failed to save changes');
    }
}

async function skipInstance() {
    if (!nextAlarmInfo) return;

    if (!confirm('Skip this alarm? It will ring again at its next scheduled time.')) {
        return;
    }

    try {
        let response;
        if (nextAlarmInfo.override_id) {
            // Update existing override to skip
            response = await fetch(`${API_BASE}/overrides/${nextAlarmInfo.override_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ skip: true })
            });
        } else {
            // Create new skip override
            response = await fetch(`${API_BASE}/overrides`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    alarm_id: nextAlarmInfo.id,
                    target_date: nextAlarmInfo.target_date,
                    skip: true
                })
            });
        }

        if (response.ok) {
            closeInstanceModal();
            checkStatus();
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to skip alarm');
        }
    } catch (error) {
        console.error('Error skipping instance:', error);
        alert('Failed to skip alarm');
    }
}

async function restoreInstance() {
    if (!nextAlarmInfo || !nextAlarmInfo.override_id) return;

    try {
        const response = await fetch(`${API_BASE}/overrides/${nextAlarmInfo.override_id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            closeInstanceModal();
            checkStatus();
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to restore original');
        }
    } catch (error) {
        console.error('Error restoring instance:', error);
        alert('Failed to restore original');
    }
}

function editRecurringAlarm(event) {
    event.preventDefault();
    if (!nextAlarmInfo) return;

    closeInstanceModal();
    editAlarm(nextAlarmInfo.id);
}

async function previewInstanceSound() {
    const sound = document.getElementById('instance-sound').value;
    if (!sound) {
        alert('Select a sound first');
        return;
    }

    if (isPreviewPlaying) {
        stopPreview();
        return;
    }

    try {
        await fetch(`${API_BASE}/sounds/preview/${encodeURIComponent(sound)}`, {
            method: 'POST'
        });
        isPreviewPlaying = true;
    } catch (error) {
        console.error('Error previewing sound:', error);
    }
}
