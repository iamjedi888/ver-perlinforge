# Save as: islandforge/routes/news.py

from flask import Blueprint, jsonify
import feedparser
from datetime import datetime

news_bp = Blueprint('news', __name__)

NEWS_FEEDS = {
    # POKEMON
    "pokemon": {"name": "Pokemon News", "url": "https://pokemonblog.com/feed", "category": "gaming"},
    
    # ANIME  
    "anime": {"name": "Anime News Network", "url": "https://www.animenewsnetwork.com/all/rss.xml", "category": "anime"},
    "crunchyroll": {"name": "Crunchyroll", "url": "https://feeds.feedburner.com/crunchyroll/rss/news", "category": "anime"},
    
    # CARS/JDM
    "speedhunters": {"name": "Speedhunters JDM", "url": "https://www.speedhunters.com/feed/", "category": "cars"},
    
    # ART
    "colossal": {"name": "Colossal Art", "url": "https://www.thisiscolossal.com/feed/", "category": "art"},
    
    # NATURE
    "earth": {"name": "Earth.Org Nature", "url": "https://earth.org/feed/", "category": "nature"},
    
    # BAKING/FOOD
    "baking": {"name": "King Arthur Baking", "url": "https://www.kingarthurbaking.com/blog/feed", "category": "baking"},
    
    # JAPAN CULTURE
    "japan": {"name": "Japan Today Culture", "url": "https://japantoday.com/category/features/lifestyle/feed", "category": "japan"}
}

NEGATIVE_KEYWORDS = ['war', 'violence', 'death', 'murder', 'assault', 'crime', 'arrest', 'scandal', 'lawsuit']

def is_positive(title, summary):
    text = (title + ' ' + summary).lower()
    return not any(keyword in text for keyword in NEGATIVE_KEYWORDS)

def fetch_feed(url, max_items=10):
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries:
            if len(items) >= max_items:
                break
            title = entry.get('title', '')
            summary = entry.get('summary', entry.get('description', ''))
            if not is_positive(title, summary):
                continue
            published = entry.get('published_parsed')
            items.append({
                'title': title,
                'summary': summary[:150] + '...',
                'link': entry.get('link', ''),
                'published': datetime(*published[:6]).isoformat() if published else datetime.now().isoformat()
            })
        return {'success': True, 'items': items}
    except:
        return {'success': False, 'items': []}

@news_bp.route('/api/news/categories')
def get_categories():
    cats = {}
    for fid, data in NEWS_FEEDS.items():
        cat = data['category']
        if cat not in cats:
            cats[cat] = []
        cats[cat].append({'id': fid, 'name': data['name']})
    return jsonify(cats)

@news_bp.route('/api/news/feed/<feed_id>')
def get_feed(feed_id):
    if feed_id not in NEWS_FEEDS:
        return jsonify({'error': 'Not found'}), 404
    config = NEWS_FEEDS[feed_id]
    result = fetch_feed(config['url'])
    return jsonify({'feed_id': feed_id, 'feed_name': config['name'], 'category': config['category'], **result})

@news_bp.route('/api/news/latest')
def get_latest():
    all_news = []
    for fid, config in NEWS_FEEDS.items():
        result = fetch_feed(config['url'], 3)
        if result['success']:
            for item in result['items']:
                all_news.append({**item, 'source': config['name'], 'category': config['category'], 'feed_id': fid})
    all_news.sort(key=lambda x: x['published'], reverse=True)
    return jsonify({'news': all_news[:30], 'total': len(all_news)})