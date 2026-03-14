"""
TriptokForge Interest-Based News Feed System
Curated positive content: Gaming, Anime, Cars, Art, Food, Nature
Users can toggle content types on/off
"""

from flask import Blueprint, jsonify, request
import feedparser
from datetime import datetime

news_bp = Blueprint('news', __name__)

# ═══════════════════════════════════════════════════════════════
# INTEREST-BASED RSS FEEDS (Positive Content Only)
# ═══════════════════════════════════════════════════════════════

NEWS_FEEDS = {
    # POKEMON
    "pokemon_official": {
        "name": "Pokemon Official News",
        "url": "https://www.pokemon.com/us/pokemon-news/rss",
        "category": "gaming",
        "interest": "pokemon",
        "safe": True
    },
    
    # MAGIC THE GATHERING
    "mtg_official": {
        "name": "Magic: The Gathering News",
        "url": "https://magic.wizards.com/en/rss/rss.xml",
        "category": "gaming",
        "interest": "mtg",
        "safe": True
    },
    
    # ANIME & STUDIO GHIBLI
    "crunchyroll": {
        "name": "Crunchyroll Anime News",
        "url": "https://feeds.feedburner.com/crunchyroll/rss/news",
        "category": "anime",
        "interest": "anime",
        "safe": True
    },
    "anime_news": {
        "name": "Anime News Network",
        "url": "https://www.animenewsnetwork.com/news/rss.xml",
        "category": "anime",
        "interest": "anime",
        "safe": True
    },
    
    # JAPAN CULTURE & FOOD
    "japan_today": {
        "name": "Japan Today - Culture",
        "url": "https://japantoday.com/category/features/lifestyle/feed",
        "category": "culture",
        "interest": "japan_culture",
        "safe": True
    },
    "ramen_adventures": {
        "name": "Ramen Adventures",
        "url": "https://www.ramenadventures.com/feed/",
        "category": "food",
        "interest": "ramen",
        "safe": True
    },
    
    # CARS & JDM
    "speedhunters": {
        "name": "Speedhunters (JDM/Tuner)",
        "url": "https://www.speedhunters.com/feed/",
        "category": "automotive",
        "interest": "jdm_cars",
        "safe": True
    },
    
    # ART & NATURE
    "colossal_art": {
        "name": "Colossal Art & Design",
        "url": "https://www.thisiscolossal.com/feed/",
        "category": "art",
        "interest": "art",
        "safe": True
    },
    "earth_org": {
        "name": "Earth.Org - Nature & Conservation",
        "url": "https://earth.org/feed/",
        "category": "nature",
        "interest": "nature",
        "safe": True
    },
    
    # BAKING & FOOD
    "king_arthur": {
        "name": "King Arthur Baking",
        "url": "https://www.kingarthurbaking.com/blog/feed",
        "category": "food",
        "interest": "baking",
        "safe": True
    },
    "serious_eats": {
        "name": "Serious Eats",
        "url": "https://www.seriouseats.com/feed/recipes",
        "category": "food",
        "interest": "food",
        "safe": True
    },
    
    # RESTORATIONS & CRAFTS
    "old_house": {
        "name": "This Old House",
        "url": "https://www.thisoldhouse.com/feed",
        "category": "restoration",
        "interest": "restoration",
        "safe": True
    },
    
    # GENERAL NEWS (OPTIONAL - Users can toggle off)
    "ri_wpri": {
        "name": "WPRI 12 (CBS Rhode Island)",
        "url": "https://www.wpri.com/feed/",
        "category": "general_news",
        "interest": "local_news",
        "safe": False  # Contains negative content
    },
    "world_bbc": {
        "name": "BBC World News",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "category": "general_news",
        "interest": "world_news",
        "safe": False
    },
}


# ═══════════════════════════════════════════════════════════════
# CONTENT FILTERING
# ═══════════════════════════════════════════════════════════════

NEGATIVE_KEYWORDS = [
    'war', 'conflict', 'violence', 'attack', 'shooting', 'death', 'killed',
    'murder', 'assault', 'abuse', 'scandal', 'controversy', 'lawsuit',
    'fired', 'accused', 'arrested', 'crime', 'victim', 'threat'
]


def is_safe_content(title, summary):
    """Filter out negative news from general sources"""
    text = (title + ' ' + summary).lower()
    
    for keyword in NEGATIVE_KEYWORDS:
        if keyword in text:
            return False
    
    return True


# ═══════════════════════════════════════════════════════════════
# RSS FEED PARSER
# ═══════════════════════════════════════════════════════════════

def fetch_rss_feed(feed_url, feed_config, max_items=10):
    """Fetch and parse RSS feed with optional filtering"""
    try:
        feed = feedparser.parse(feed_url)
        items = []
        
        for entry in feed.entries:
            if len(items) >= max_items:
                break
            
            title = entry.get('title', 'No title')
            summary = entry.get('summary', entry.get('description', ''))
            
            # Filter negative content from non-safe sources
            if not feed_config.get('safe', True):
                if not is_safe_content(title, summary):
                    continue
            
            # Parse published date
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            if published:
                pub_date = datetime(*published[:6])
            else:
                pub_date = datetime.now()
            
            items.append({
                'title': title,
                'summary': summary[:200] + '...' if len(summary) > 200 else summary,
                'link': entry.get('link', ''),
                'published': pub_date.isoformat(),
            })
        
        return {'success': True, 'items': items}
        
    except Exception as e:
        print(f"[RSS] Error: {e}")
        return {'success': False, 'items': []}


# ═══════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════

@news_bp.route('/api/news/interests', methods=['GET'])
def get_interests():
    """Get all available interest categories for user toggles"""
    interests = {}
    
    for feed_id, feed_data in NEWS_FEEDS.items():
        category = feed_data['category']
        if category not in interests:
            interests[category] = {
                'name': category.replace('_', ' ').title(),
                'safe': feed_data.get('safe', True),
                'feeds': []
            }
        
        interests[category]['feeds'].append({
            'id': feed_id,
            'name': feed_data['name']
        })
    
    return jsonify(interests)


@news_bp.route('/api/news/latest', methods=['POST'])
def get_latest_news():
    """Get latest news based on user's enabled interests"""
    
    # Get user's enabled categories from request
    data = request.get_json() or {}
    enabled_categories = data.get('categories', [])
    
    # If no preferences, default to safe content only
    if not enabled_categories:
        enabled_categories = [
            'gaming', 'anime', 'culture', 'food', 
            'automotive', 'art', 'nature', 'restoration'
        ]
    
    all_news = []
    
    for feed_id, feed_config in NEWS_FEEDS.items():
        # Skip if category not enabled
        if feed_config['category'] not in enabled_categories:
            continue
        
        result = fetch_rss_feed(feed_config['url'], feed_config, max_items=3)
        
        if result['success']:
            for item in result['items']:
                all_news.append({
                    **item,
                    'source': feed_config['name'],
                    'category': feed_config['category'],
                    'interest': feed_config['interest'],
                    'feed_id': feed_id
                })
    
    all_news.sort(key=lambda x: x['published'], reverse=True)
    
    return jsonify({
        'news': all_news[:50],
        'total': len(all_news),
        'last_updated': datetime.now().isoformat()
    })


@news_bp.route('/api/news/category/<category_name>', methods=['GET'])
def get_category_news(category_name):
    """Get all news for a specific category"""
    
    category_feeds = {
        feed_id: feed_data 
        for feed_id, feed_data in NEWS_FEEDS.items() 
        if feed_data['category'] == category_name
    }
    
    if not category_feeds:
        return jsonify({'error': 'Category not found'}), 404
    
    news = []
    
    for feed_id, feed_config in category_feeds.items():
        result = fetch_rss_feed(feed_config['url'], feed_config, max_items=10)
        
        if result['success']:
            for item in result['items']:
                news.append({
                    **item,
                    'source': feed_config['name'],
                    'feed_id': feed_id
                })
    
    news.sort(key=lambda x: x['published'], reverse=True)
    
    return jsonify({
        'category': category_name,
        'news': news,
        'total': len(news)
    })
