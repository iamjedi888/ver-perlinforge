"""
TriptokForge TV Guide - Streaming Channels System
Backend routes for live channels, schedules, and EPG data
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import json

channels_bp = Blueprint('channels', __name__)


# ═══════════════════════════════════════════════════════════════
# CHANNEL DATABASE (Replace with Oracle later)
# ═══════════════════════════════════════════════════════════════

CHANNELS = {
    "ttf-live": {
        "id": "ttf-live",
        "name": "TriptokForge LIVE",
        "number": 1,
        "type": "twitch",
        "stream_id": "oxenv",  # Replace with your channel
        "logo": "/static/img/channels/ttf-logo.png",
        "description": "24/7 Fortnite tournaments and scrims",
        "live": True,
        "category": "competitive"
    },
    "highlights": {
        "id": "highlights",
        "name": "Highlight Reels",
        "number": 2,
        "type": "youtube",
        "stream_id": "UCxvCwXjO_zYCza4AyN3ARjg",
        "logo": "/static/img/channels/highlights-logo.png",
        "description": "Best plays and tournament highlights",
        "live": False,
        "category": "highlights"
    },
    "tutorial": {
        "id": "tutorial",
        "name": "Pro Tips & Tutorials",
        "number": 3,
        "type": "youtube",
        "stream_id": "tutorial_channel",
        "logo": "/static/img/channels/tutorial-logo.png",
        "description": "Learn from the pros",
        "live": False,
        "category": "education"
    },
    "community": {
        "id": "community",
        "name": "Community Streams",
        "number": 4,
        "type": "twitch",
        "stream_id": "community_channel",
        "logo": "/static/img/channels/community-logo.png",
        "description": "Member-submitted content",
        "live": True,
        "category": "community"
    }
}


# ═══════════════════════════════════════════════════════════════
# PROGRAM SCHEDULE (TV Guide blocks)
# ═══════════════════════════════════════════════════════════════

def generate_schedule(channel_id, days=7):
    """Generate TV-style program schedule for a channel"""
    
    # Example schedule blocks (customize per channel)
    schedule_templates = {
        "ttf-live": [
            {"start": "09:00", "duration": 120, "title": "Morning Scrims", "type": "live"},
            {"start": "12:00", "duration": 60, "title": "Tournament Prep", "type": "live"},
            {"start": "14:00", "duration": 180, "title": "Ranked Arena", "type": "live"},
            {"start": "18:00", "duration": 240, "title": "Prime Time Tournament", "type": "live"},
            {"start": "22:00", "duration": 120, "title": "Late Night Scrims", "type": "live"},
        ],
        "highlights": [
            {"start": "00:00", "duration": 60, "title": "Yesterday's Best Plays", "type": "vod"},
            {"start": "06:00", "duration": 120, "title": "Tournament Recap", "type": "vod"},
            {"start": "12:00", "duration": 180, "title": "Top 10 Eliminations", "type": "vod"},
            {"start": "18:00", "duration": 120, "title": "Pro Player Highlights", "type": "vod"},
        ],
        "tutorial": [
            {"start": "08:00", "duration": 30, "title": "Building Basics", "type": "vod"},
            {"start": "10:00", "duration": 45, "title": "Advanced Edits", "type": "vod"},
            {"start": "14:00", "duration": 60, "title": "Rotation Strategies", "type": "vod"},
            {"start": "16:00", "duration": 45, "title": "Aim Training Tips", "type": "vod"},
            {"start": "20:00", "duration": 90, "title": "Pro VOD Review", "type": "vod"},
        ]
    }
    
    template = schedule_templates.get(channel_id, [])
    schedule = []
    
    now = datetime.now()
    for day_offset in range(days):
        date = now + timedelta(days=day_offset)
        
        for block in template:
            start_time = datetime.strptime(block["start"], "%H:%M").time()
            program_start = datetime.combine(date.date(), start_time)
            program_end = program_start + timedelta(minutes=block["duration"])
            
            schedule.append({
                "start": program_start.isoformat(),
                "end": program_end.isoformat(),
                "title": block["title"],
                "type": block["type"],
                "duration": block["duration"]
            })
    
    return schedule


# ═══════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════

@channels_bp.route('/api/channels', methods=['GET'])
def get_channels():
    """Get all available channels"""
    return jsonify({
        'channels': list(CHANNELS.values()),
        'count': len(CHANNELS)
    })


@channels_bp.route('/api/channels/<channel_id>', methods=['GET'])
def get_channel(channel_id):
    """Get specific channel details"""
    channel = CHANNELS.get(channel_id)
    
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    return jsonify(channel)


@channels_bp.route('/api/channels/<channel_id>/schedule', methods=['GET'])
def get_channel_schedule(channel_id):
    """Get TV Guide schedule for a channel"""
    
    if channel_id not in CHANNELS:
        return jsonify({'error': 'Channel not found'}), 404
    
    days = int(request.args.get('days', 7))
    schedule = generate_schedule(channel_id, days)
    
    return jsonify({
        'channel_id': channel_id,
        'channel_name': CHANNELS[channel_id]['name'],
        'schedule': schedule,
        'timezone': 'UTC'
    })


@channels_bp.route('/api/channels/now-playing', methods=['GET'])
def get_now_playing():
    """Get current program on all channels (TV Guide 'now' row)"""
    
    now = datetime.now()
    current_programs = {}
    
    for channel_id in CHANNELS:
        schedule = generate_schedule(channel_id, days=1)
        
        # Find current program
        for program in schedule:
            start = datetime.fromisoformat(program['start'])
            end = datetime.fromisoformat(program['end'])
            
            if start <= now <= end:
                current_programs[channel_id] = {
                    'channel': CHANNELS[channel_id],
                    'program': program,
                    'progress': ((now - start).seconds / (end - start).seconds) * 100
                }
                break
    
    return jsonify(current_programs)


@channels_bp.route('/api/channels/epg', methods=['GET'])
def get_epg_grid():
    """Get full Electronic Program Guide grid (like cable TV guide)"""
    
    hours = int(request.args.get('hours', 12))
    now = datetime.now()
    
    # Round to nearest hour
    start_time = now.replace(minute=0, second=0, microsecond=0)
    
    grid = {
        'start_time': start_time.isoformat(),
        'hours': hours,
        'channels': []
    }
    
    for channel_id, channel in CHANNELS.items():
        schedule = generate_schedule(channel_id, days=2)
        
        # Filter programs in time window
        end_time = start_time + timedelta(hours=hours)
        visible_programs = [
            p for p in schedule
            if datetime.fromisoformat(p['start']) < end_time
            and datetime.fromisoformat(p['end']) > start_time
        ]
        
        grid['channels'].append({
            'channel': channel,
            'programs': visible_programs
        })
    
    return jsonify(grid)


# ═══════════════════════════════════════════════════════════════
# ADMIN ROUTES (Add/Edit Channels - for later)
# ═══════════════════════════════════════════════════════════════

@channels_bp.route('/api/channels/admin/add', methods=['POST'])
def add_channel():
    """Add a new channel (admin only)"""
    # TODO: Add authentication
    data = request.get_json()
    
    channel_id = data.get('id')
    if channel_id in CHANNELS:
        return jsonify({'error': 'Channel already exists'}), 400
    
    CHANNELS[channel_id] = data
    
    return jsonify({'success': True, 'channel': data})


@channels_bp.route('/api/channels/admin/<channel_id>/live', methods=['POST'])
def set_channel_live(channel_id):
    """Toggle channel live status"""
    
    if channel_id not in CHANNELS:
        return jsonify({'error': 'Channel not found'}), 404
    
    data = request.get_json()
    CHANNELS[channel_id]['live'] = data.get('live', True)
    
    return jsonify({'success': True, 'channel': CHANNELS[channel_id]})
