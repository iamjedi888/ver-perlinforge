"""
TriptokForge Member Dashboard
Iron Man / JARVIS style analytics interface
"""
from flask import Blueprint, render_template, session, jsonify
from routes.epic_games_api import get_player_stats, get_game_library, SUPPORTED_GAMES
import os

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def dashboard_page():
    """Main member dashboard page"""
    # TODO: Add login requirement check
    # For now, accessible to all (shows mock data)
    return render_template('dashboard.html')

@dashboard_bp.route('/api/dashboard/stats')
def get_dashboard_stats():
    """
    Get all stats for dashboard widgets
    Returns combined data from Epic Games + TriptokForge
    """
    # Get Epic account ID from session (or use mock)
    account_id = session.get('epic_account_id', 'mock_user_123')
    
    # Fetch stats (uses mock data until API keys configured)
    epic_stats = get_player_stats(account_id, use_mock=True)
    
    # Add TriptokForge internal stats
    triptok_stats = {
        'islands_generated': 12,
        'leaderboard_rank': 47,
        'total_downloads': 89,
        'community_score': 4.7
    }
    
    return jsonify({
        'epic_games': epic_stats,
        'triptokforge': triptok_stats,
        'timestamp': 'now'
    })

@dashboard_bp.route('/api/dashboard/games')
def get_available_games():
    """
    Get list of games in user's library
    Shows which ones have stats available
    """
    account_id = session.get('epic_account_id', 'mock_user_123')
    games = get_game_library(account_id, use_mock=True)
    
    return jsonify({
        'games': games,
        'supported_games': SUPPORTED_GAMES
    })

@dashboard_bp.route('/api/dashboard/preferences', methods=['GET', 'POST'])
def dashboard_preferences():
    """
    Save/load user's dashboard preferences
    (which games to display, layout, etc.)
    """
    # TODO: Implement preferences storage
    # For now, return defaults
    return jsonify({
        'featured_games': ['fortnite', 'rocket_league', 'fall_guys'],
        'layout': 'iron_man',
        'theme': 'cyan_blue'
    })

print("📊 Dashboard module loaded")
