# TriptokForge TV Guide - Deployment Guide

## What We Built

✅ **Backend** (channels_backend.py):
   - Channel database (Twitch/YouTube support)
   - EPG (Electronic Program Guide) generator
   - Schedule blocks (like TV programming)
   - Live status tracking
   - REST API for all channel data

✅ **Frontend** (channels_page.html):
   - TV Guide grid interface
   - Live channel switcher
   - Embedded video player (Twitch/YouTube)
   - Program schedules with time blocks
   - Responsive design

---

## Quick Deploy (3 Steps)

### Step 1: Add Backend Routes

Copy `channels_backend.py` to: `islandforge/routes/channels.py`

In your `server.py`, add:
```python
from routes.channels import channels_bp
app.register_blueprint(channels_bp)
```

### Step 2: Add Frontend Page

Copy `channels_page.html` to: `islandforge/templates/channels.html`

Add a route in `server.py`:
```python
@app.route('/channels')
def channels_page():
    return render_template('channels.html')
```

### Step 3: Configure Your Channels

Edit `islandforge/routes/channels.py`, find the `CHANNELS` dict:

```python
CHANNELS = {
    "ttf-live": {
        "id": "ttf-live",
        "name": "TriptokForge LIVE",
        "number": 1,
        "type": "twitch",
        "stream_id": "YOUR_TWITCH_CHANNEL_NAME",  # ← Change this!
        "live": True,
    },
    # Add more channels...
}
```

**Deploy:**
```powershell
.\deploy.ps1 "Add TV Guide channel system"
```

---

## How It Works

### Channel Types Supported:
- **Twitch** - Live streams (24/7 or scheduled)
- **YouTube** - Live streams or VOD playlists

### TV Guide Features:
- **EPG Grid** - See all channels and schedules at once
- **Time Blocks** - Programs scheduled like real TV
- **Live Indicators** - Red badges for live channels
- **Channel Switcher** - Click any channel to watch
- **Now Playing** - Shows current program

### Program Schedule System:
Each channel has a daily schedule template that repeats:
```python
"ttf-live": [
    {"start": "09:00", "duration": 120, "title": "Morning Scrims"},
    {"start": "14:00", "duration": 180, "title": "Ranked Arena"},
    {"start": "18:00", "duration": 240, "title": "Prime Time Tournament"},
]
```

This generates a full TV Guide for the next 7 days.

---

## Customization

### Add New Channels:
Edit the `CHANNELS` dict in `channels.py`:
```python
"new-channel": {
    "id": "new-channel",
    "name": "New Channel",
    "number": 5,
    "type": "twitch",  # or "youtube"
    "stream_id": "twitch_username",
    "logo": "/static/img/channels/logo.png",
    "description": "Channel description",
    "live": True,
    "category": "competitive"
}
```

### Modify Schedule Blocks:
Edit `generate_schedule()` in `channels.py`:
```python
schedule_templates = {
    "your-channel": [
        {"start": "10:00", "duration": 60, "title": "Your Show"},
        {"start": "12:00", "duration": 120, "title": "Another Show"},
    ]
}
```

### Change EPG Time Window:
In the frontend, modify the time controls:
```javascript
loadGuide(6)   // 6 hours
loadGuide(12)  // 12 hours
loadGuide(24)  // 24 hours
```

---

## Real-World Setup Examples

### Example 1: Tournament Channel (24/7 Live)
```python
"tournaments": {
    "id": "tournaments",
    "name": "TriptokForge Tournaments",
    "type": "twitch",
    "stream_id": "triptokforge_official",
    "live": True,
    "schedule": [
        {"start": "09:00", "duration": 180, "title": "Morning Qualifiers"},
        {"start": "14:00", "duration": 240, "title": "Main Event"},
        {"start": "20:00", "duration": 180, "title": "Finals"},
    ]
}
```

### Example 2: Highlights Channel (VOD Playlist)
```python
"highlights": {
    "id": "highlights",
    "name": "Best Plays",
    "type": "youtube",
    "stream_id": "UC_your_youtube_channel",
    "live": False,
    "schedule": [
        {"start": "00:00", "duration": 30, "title": "Top 10 #47"},
        {"start": "00:30", "duration": 45, "title": "Pro Highlights"},
        # Loops through playlist
    ]
}
```

### Example 3: Member Streams (Rotating)
```python
"community": {
    "id": "community",
    "name": "Member Streams",
    "type": "twitch",
    "stream_id": "community_channel",
    "live": True,
    "schedule": [
        {"start": "10:00", "duration": 120, "title": "Player1 Stream"},
        {"start": "14:00", "duration": 120, "title": "Player2 Stream"},
        {"start": "18:00", "duration": 120, "title": "Player3 Stream"},
    ]
}
```

---

## API Endpoints

After deployment, you'll have:

- `GET /api/channels` - All channels
- `GET /api/channels/<id>` - Specific channel
- `GET /api/channels/<id>/schedule` - Channel schedule
- `GET /api/channels/now-playing` - Current programs on all channels
- `GET /api/channels/epg?hours=12` - Full TV Guide grid

Test:
```bash
curl http://localhost:5000/api/channels
curl http://localhost:5000/api/channels/epg?hours=12
```

---

## Future Enhancements

### Phase 2: Save Schedules to Oracle
Move `CHANNELS` and schedules to Oracle database:
```sql
CREATE TABLE channels (
    id VARCHAR2(64) PRIMARY KEY,
    name VARCHAR2(128),
    type VARCHAR2(32),
    stream_id VARCHAR2(128),
    live NUMBER(1)
);

CREATE TABLE programs (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    channel_id VARCHAR2(64),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    title VARCHAR2(256)
);
```

### Phase 3: Multi-View
Show 2-4 channels on screen at once (picture-in-picture style)

### Phase 4: Chat Integration
Embed Twitch chat or custom chat alongside streams

### Phase 5: Admin Panel
Web UI to add/edit channels and schedules without code changes

---

## Troubleshooting

### Player Not Loading:
1. Check `parent` parameter matches your domain
2. Verify Twitch/YouTube stream IDs are correct
3. Check browser console for errors

### Schedule Not Showing:
1. Verify channel ID exists in `CHANNELS` dict
2. Check schedule template in `generate_schedule()`
3. Test API: `/api/channels/<channel_id>/schedule`

### EPG Grid Empty:
1. Test EPG endpoint: `/api/channels/epg?hours=12`
2. Check browser console for JavaScript errors
3. Verify time zone is correct

---

## Ready to Deploy?

1. Put files in place (Step 1-2)
2. Configure your Twitch/YouTube channels (Step 3)
3. Run: `.\deploy.ps1 "Add TV Guide"`
4. Visit: `https://triptokforge.org/channels`

🎬 You'll have a professional TV Guide streaming hub!
