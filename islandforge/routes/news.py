"""
TriptokForge News Feed System
Aggregates legitimate news from RSS/JSON feeds worldwide
"""

from flask import Blueprint, jsonify
import feedparser
from datetime import datetime
from functools import lru_cache

news_bp = Blueprint('news', __name__)

# ═══════════════════════════════════════════════════════════════
# LEGITIMATE NEWS RSS FEEDS (Official Sources)
# ═══════════════════════════════════════════════════════════════

NEWS_FEEDS = {
    # RHODE ISLAND / LOCAL
    "ri_wpri": {
        "name": "WPRI 12 (CBS Rhode Island)",
        "url": "https://www.wpri.com/feed/",
        "region": "rhode_island",
        "type": "rss",
        "category": "local"
    },
    "ri_nbc10": {
        "name": "NBC 10 WJAR (Providence)",
        "url": "https://turnto10.com/feed",
        "region": "rhode_island",
        "type": "rss",
        "category": "local"
    },
    
    # JAPAN
    "japan_nhk": {
        "name": "NHK World (Japan)",
        "url": "https://www3.nhk.or.jp/rss/news/cat0.xml",
        "region": "japan",
        "type": "rss",
        "category": "international"
    },
    "japan_kyodo": {
        "name": "Kyodo News",
        "url": "https://english.kyodonews.net/rss/all.xml",
        "region": "japan",
        "type": "rss",
        "category": "international"
    },
    
    # NEW YORK / NYC
    "nyc_nytimes": {
        "name": "New York Times - NYC",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/NYRegion.xml",
        "region": "new_york",
        "type": "rss",
        "category": "local"
    },
    
    # CALIFORNIA
    "ca_latimes": {
        "name": "LA Times",
        "url": "https://www.latimes.com/rss2.0.xml",
        "region": "california",
        "type": "rss",
        "category": "local"
    },
    
    # HAWAII
    "hawaii_staradvertiser": {
        "name": "Honolulu Star-Advertiser",
        "url": "https://www.staradvertiser.com/feed/",
        "region": "hawaii",
        "type": "rss",
        "category": "local"
    },
    
    # WORLD / MAJOR
    "world_bbc": {
        "name": "BBC World News",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "region": "global",
        "type": "rss",
        "category": "international"
    },
}


# ═══════════════════════════════════════════════════════════════
# RSS FEED PARSER WITH CACHING
# ═══════════════════════════════════════════════════════════════

def fetch_rss_feed(feed_url, max_items=10):
    """Fetch and parse RSS feed"""
    try:
        feed = feedparser.parse(feed_url)
        
        items = []
        for entry in feed.entries[:max_items]:
            # Parse published date
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            if published:
                pub_date = datetime(*published[:6])
            else:
                pub_date = datetime.now()
            
            items.append({
                'title': entry.get('title', 'No title'),
                'summary': entry.get('summary', entry.get('description', ''))[:200] + '...',
                'link': entry.get('link', ''),
                'published': pub_date.isoformat(),
                'author': entry.get('author', ''),
            })
        
        return {
            'success': True,
            'items': items,
            'feed_title': feed.feed.get('title', ''),
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[RSS] Error fetching {feed_url}: {e}")
        return {
            'success': False,
            'error': str(e),
            'items': []
        }


# ═══════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════

@news_bp.route('/api/news/feeds', methods=['GET'])
def get_news_feeds():
    """Get list of all available news feeds"""
    feeds = []
    
    for feed_id, feed_data in NEWS_FEEDS.items():
        feeds.append({
            'id': feed_id,
            'name': feed_data['name'],
            'region': feed_data['region'],
            'category': feed_data['category'],
            'type': feed_data['type']
        })
    
    return jsonify({
        'feeds': feeds,
        'total': len(feeds)
    })


@news_bp.route('/api/news/regions', methods=['GET'])
def get_regions():
    """Get news grouped by region"""
    regions = {}
    
    for feed_id, feed_data in NEWS_FEEDS.items():
        region = feed_data['region']
        if region not in regions:
            regions[region] = []
        
        regions[region].append({
            'id': feed_id,
            'name': feed_data['name'],
            'category': feed_data['category']
        })
    
    return jsonify(regions)


@news_bp.route('/api/news/feed/<feed_id>', methods=['GET'])
def get_news_feed_items(feed_id):
    """Get latest news items from a specific feed"""
    
    if feed_id not in NEWS_FEEDS:
        return jsonify({'error': 'Feed not found'}), 404
    
    feed_config = NEWS_FEEDS[feed_id]
    
    if feed_config['type'] == 'rss':
        result = fetch_rss_feed(feed_config['url'])
        
        return jsonify({
            'feed_id': feed_id,
            'feed_name': feed_config['name'],
            'region': feed_config['region'],
            **result
        })
    
    return jsonify({'error': 'Invalid feed type'}), 400


@news_bp.route('/api/news/latest', methods=['GET'])
def get_latest_news():
    """Get latest headlines from all feeds (aggregated)"""
    
    all_news = []
    
    # Fetch from priority feeds
    priority_feeds = [
        'ri_wpri', 'japan_nhk', 'nyc_nytimes', 
        'ca_latimes', 'world_bbc', 'hawaii_staradvertiser'
    ]
    
    for feed_id in priority_feeds:
        if feed_id in NEWS_FEEDS:
            feed_config = NEWS_FEEDS[feed_id]
            
            if feed_config['type'] == 'rss':
                result = fetch_rss_feed(feed_config['url'], max_items=5)
                
                if result['success']:
                    for item in result['items']:
                        all_news.append({
                            **item,
                            'source': feed_config['name'],
                            'region': feed_config['region'],
                            'feed_id': feed_id
                        })
    
    # Sort by published date
    all_news.sort(key=lambda x: x['published'], reverse=True)
    
    return jsonify({
        'news': all_news[:50],
        'total': len(all_news),
        'last_updated': datetime.now().isoformat()
    })


@news_bp.route('/api/news/region/<region_name>', methods=['GET'])
def get_region_news(region_name):
    """Get all news for a specific region"""
    
    region_feeds = {
        feed_id: feed_data 
        for feed_id, feed_data in NEWS_FEEDS.items() 
        if feed_data['region'] == region_name
    }
    
    if not region_feeds:
        return jsonify({'error': 'Region not found'}), 404
    
    news = []
    
    for feed_id, feed_config in region_feeds.items():
        if feed_config['type'] == 'rss':
            result = fetch_rss_feed(feed_config['url'], max_items=10)
            
            if result['success']:
                for item in result['items']:
                    news.append({
                        **item,
                        'source': feed_config['name'],
                        'feed_id': feed_id
                    })
    
    news.sort(key=lambda x: x['published'], reverse=True)
    
    return jsonify({
        'region': region_name,
        'news': news,
        'total': len(news)
    })