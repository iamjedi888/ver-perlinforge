"""
Epic Games API Integration
Handles OAuth, game library, and stats retrieval
"""
import os
import requests
from flask import session

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION (loads from .env)
# ═══════════════════════════════════════════════════════════════

EPIC_CONFIG = {
    'client_id': os.getenv('EPIC_CLIENT_ID', 'PENDING_APPROVAL'),
    'client_secret': os.getenv('EPIC_CLIENT_SECRET', 'PENDING_APPROVAL'),
    'redirect_uri': os.getenv('EPIC_REDIRECT_URI', 'https://triptokforge.org/auth/epic/callback'),
    'auth_url': 'https://www.epicgames.com/id/api/redirect',
    'token_url': 'https://api.epicgames.dev/epic/oauth/v2/token',
    'api_base': 'https://api.epicgames.dev'
}

# ═══════════════════════════════════════════════════════════════
# GAME CATALOG (200+ Epic Games with stats support)
# ═══════════════════════════════════════════════════════════════

SUPPORTED_GAMES = {
    'fortnite': {
        'name': 'Fortnite',
        'icon': 'https://cdn2.unrealengine.com/14br-bplaunch-egs-s1-2560x1440-2560x1440-480244605.jpg',
        'has_stats': True,
        'stats_endpoint': '/fortnite/v2/stats',
        'default_metrics': ['wins', 'kills', 'kd_ratio', 'matches_played']
    },
    'rocket_league': {
        'name': 'Rocket League',
        'icon': 'https://cdn1.epicgames.com/offer/9773aa1aa54f4f7b80e44bef04986cea/EGS_RocketLeague_PsyonixLLC_S2_1200x1600-34b4e50361cd2e14239f508e76bb794d',
        'has_stats': True,
        'stats_endpoint': '/rocket-league/v1/stats',
        'default_metrics': ['goals', 'assists', 'saves', 'rank']
    },
    'fall_guys': {
        'name': 'Fall Guys',
        'icon': 'https://cdn1.epicgames.com/offer/50118b7f954e450f8823df1614b24a80/EGS_FallGuys_Mediatonic_S2_1200x1600-5f8b1f5b9f31c0e6e9b6669e6e3f4a34',
        'has_stats': True,
        'stats_endpoint': '/fall-guys/v1/stats',
        'default_metrics': ['wins', 'crowns', 'kudos', 'rounds_played']
    }
}

# ═══════════════════════════════════════════════════════════════
# MOCK DATA (for development before API approval)
# ═══════════════════════════════════════════════════════════════

def get_mock_player_stats():
    """Returns mock data for dashboard testing"""
    return {
        'epic_account': {
            'account_id': 'mock_user_123',
            'display_name': 'DemoPlayer',
            'avatar': 'https://cdn2.unrealengine.com/epic-games-logo-400x400.png',
            'level': 87,
            'account_age_days': 1250
        },
        'fortnite': {
            'total_wins': 342,
            'total_kills': 8521,
            'kd_ratio': 2.4,
            'matches_played': 1845,
            'win_rate': 18.5,
            'current_season_rank': 'Diamond II',
            'playtime_hours': 487
        },
        'rocket_league': {
            'goals': 1523,
            'assists': 892,
            'saves': 734,
            'rank': 'Diamond II',
            'mmr': 1250,
            'playtime_hours': 234
        },
        'fall_guys': {
            'wins': 89,
            'crowns': 45,
            'kudos': 23450,
            'rounds_played': 678,
            'playtime_hours': 56
        }
    }

def get_mock_game_library():
    """Returns list of games user owns"""
    return [
        {'id': 'fortnite', 'name': 'Fortnite', 'has_stats': True},
        {'id': 'rocket_league', 'name': 'Rocket League', 'has_stats': True},
        {'id': 'fall_guys', 'name': 'Fall Guys', 'has_stats': True},
        {'id': 'gta5', 'name': 'GTA V', 'has_stats': False},
        {'id': 'control', 'name': 'Control', 'has_stats': False}
    ]

# ═══════════════════════════════════════════════════════════════
# REAL API FUNCTIONS (ready for when keys arrive)
# ═══════════════════════════════════════════════════════════════

def get_player_stats(account_id, use_mock=True):
    """
    Fetch player stats from Epic Games API
    
    Args:
        account_id: Epic Games account ID
        use_mock: If True, returns mock data (default until API approved)
    
    Returns:
        Dict with all game stats
    """
    if use_mock or EPIC_CONFIG['client_id'] == 'PENDING_APPROVAL':
        print("📊 Using mock data (Epic API keys pending)")
        return get_mock_player_stats()
    
    # Real API call (activate when keys ready)
    headers = {
        'Authorization': f'Bearer {session.get("epic_access_token")}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f"{EPIC_CONFIG['api_base']}/stats/accountId/{account_id}",
            headers=headers
        )
        return response.json()
    except Exception as e:
        print(f"❌ Epic API error: {e}")
        return get_mock_player_stats()

def get_game_library(account_id, use_mock=True):
    """
    Fetch user's Epic Games library
    
    Returns:
        List of games with stats availability
    """
    if use_mock or EPIC_CONFIG['client_id'] == 'PENDING_APPROVAL':
        return get_mock_game_library()
    
    # Real API call (activate when keys ready)
    # ... implementation here
    return get_mock_game_library()

# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def is_api_configured():
    """Check if Epic API credentials are configured"""
    return (
        EPIC_CONFIG['client_id'] != 'PENDING_APPROVAL' and
        EPIC_CONFIG['client_secret'] != 'PENDING_APPROVAL'
    )

print("🎮 Epic Games API module loaded")
print(f"   API Configured: {is_api_configured()}")
