"""
TriptokForge Interest-Based News - Backend with User Preferences
"""

from flask import Blueprint, jsonify, request, session
import feedparser
from datetime import datetime

news_bp = Blueprint('news', __name__)

NEWS_FEEDS = {
    "pokemon": {"name": "Pokemon", "url": "https://www.pokemon.com/us/pokemon-news/rss", "category": "gaming", "interest": "pokemon"},
    "mtg": {"name": "Magic: The Gathering", "url": "https://magic.wizards.com/en/rss/rss.xml", "category": "gaming", "interest": "mtg"},
    "anime": {"name": "Anime News", "url": "https://www.animenewsnetwork.com/news/rss.xml", "category": "anime", "interest": "anime"},
    "japan": {"name": "Japan Culture", "url": "https://japantoday.com/category/features/lifestyle/feed", "category": "culture", "interest": "japan"},
    "ramen": {"name": "Ramen", "url": "https://www.ramenadventures.com/feed/", "category": "food", "interest": "ramen"},
    "jdm": {"name": "JDM/Tuner Cars", "url": "https://www.speedhunters.com/feed/", "category": "automotive", "interest": "jdm"},
    "art": {"name": "Art & Design", "url": "https://www.thisiscolossal.com/feed/", "category": "art", "interest": "art"},
    "nature": {"name": "Nature", "url": "https://earth.org/feed/", "category": "nature", "interest": "nature"},
    "baking": {"name": "Baking", "url": "https://www.kingarthurbaking.com/blog/feed", "category": "food", "interest": "baking"},
    "restoration": {"name": "Restorations", "url": "https://www.thisoldhouse.com/feed", "category": "restoration", "interest": "restoration"},
}

NEGATIVE_KEYWORDS = ['war', 'conflict', 'violence', 'attack', 'death', 'killed', 'murder', 'assault', 'abuse', 'scandal', 'lawsuit', 'fired', 'accused', 'arrested', 'crime']

def should_filter(title, summary, filter_on):
    if not filter_on: return False
    text = (title + ' ' + summary).lower()
    return any(kw in text for kw in NEGATIVE_KEYWORDS)

def fetch_rss(url, max_items=10, filter_neg=True):
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries:
            if len(items) >= max_items: break
            title = entry.get('title', '')
            summary = entry.get('summary', entry.get('description', ''))
            if should_filter(title, summary, filter_neg): continue
            pub = entry.get('published_parsed') or entry.get('updated_parsed')
            items.append({'title': title, 'summary': summary[:200] + '...', 'link': entry.get('link', ''), 'published': datetime(*pub[:6]).isoformat() if pub else datetime.now().isoformat()})
        return {'success': True, 'items': items}
    except Exception as e:
        return {'success': False, 'items': []}

@news_bp.route('/api/news/preferences', methods=['GET', 'POST'])
def prefs():
    if request.method == 'POST':
        data = request.json
        session['news_interests'] = data.get('interests', [])
        session['filter_negative'] = data.get('filter_negative', True)
        return jsonify({'success': True, 'preferences': {'interests': session.get('news_interests', []), 'filter_negative': session.get('filter_negative', True)}})
    return jsonify({'interests': session.get('news_interests', list(set([f['interest'] for f in NEWS_FEEDS.values()]))), 'filter_negative': session.get('filter_negative', True)})

@news_bp.route('/api/news/interests', methods=['GET'])
def interests():
    res = {}
    for fid, fd in NEWS_FEEDS.items():
        i = fd['interest']
        if i not in res: res[i] = {'name': i.replace('_', ' ').title(), 'category': fd['category'], 'enabled': True}
    return jsonify(res)

@news_bp.route('/api/news/latest', methods=['GET'])
def latest():
    enabled = session.get('news_interests', list(set([f['interest'] for f in NEWS_FEEDS.values()])))
    filter_neg = session.get('filter_negative', True)
    news = []
    for fid, fc in NEWS_FEEDS.items():
        if fc['interest'] not in enabled: continue
        r = fetch_rss(fc['url'], 3, filter_neg)
        if r['success']:
            for item in r['items']:
                news.append({**item, 'source': fc['name'], 'category': fc['category'], 'interest': fc['interest']})
    news.sort(key=lambda x: x['published'], reverse=True)
    return jsonify({'news': news[:50], 'total': len(news)})

@news_bp.route('/api/news/category/<cat>', methods=['GET'])
def cat_news(cat):
    enabled = session.get('news_interests', list(set([f['interest'] for f in NEWS_FEEDS.values()])))
    filter_neg = session.get('filter_negative', True)
    feeds = {fid: fd for fid, fd in NEWS_FEEDS.items() if fd['category'] == cat and fd['interest'] in enabled}
    news = []
    for fid, fc in feeds.items():
        r = fetch_rss(fc['url'], 10, filter_neg)
        if r['success']:
            for item in r['items']: news.append({**item, 'source': fc['name']})
    news.sort(key=lambda x: x['published'], reverse=True)
    return jsonify({'category': cat, 'news': news, 'total': len(news)})
