// TriptokForge News - Interest-Based

let allNews = [];
let enabledCategories = [];

// Load user preferences from localStorage
function loadPreferences() {
    const saved = localStorage.getItem('news_interests');
    if (saved) {
        enabledCategories = JSON.parse(saved);
    } else {
        // Default: all safe categories enabled
        enabledCategories = [
            'gaming', 'anime', 'culture', 'food',
            'automotive', 'art', 'nature', 'restoration'
        ];
    }
}

// Save user preferences
function savePreferences() {
    localStorage.setItem('news_interests', JSON.stringify(enabledCategories));
}

// Load available interests and create checkboxes
async function loadInterests() {
    try {
        const response = await fetch('/api/news/interests');
        const interests = await response.json();
        
        const grid = document.getElementById('interestsGrid');
        
        Object.entries(interests).forEach(([category, data]) => {
            const checkbox = document.createElement('div');
            checkbox.className = `interest-checkbox ${!data.safe ? 'warning' : ''}`;
            
            const checked = enabledCategories.includes(category);
            
            checkbox.innerHTML = `
                <input type="checkbox" 
                       id="interest-${category}" 
                       ${checked ? 'checked' : ''}
                       onchange="toggleInterest('${category}')">
                <label for="interest-${category}">${data.name}</label>
            `;
            
            grid.appendChild(checkbox);
        });
        
    } catch (error) {
        console.error('Error loading interests:', error);
    }
}

// Toggle interest on/off
function toggleInterest(category) {
    if (enabledCategories.includes(category)) {
        enabledCategories = enabledCategories.filter(c => c !== category);
    } else {
        enabledCategories.push(category);
    }
    
    savePreferences();
    loadNews();
}

// Load news based on enabled interests
async function loadNews() {
    try {
        document.getElementById('newsGrid').innerHTML = 
            '<div class="loading">Loading news</div>';
        
        const response = await fetch('/api/news/latest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ categories: enabledCategories })
        });
        
        const data = await response.json();
        allNews = data.news;
        
        renderNews();
        updateTicker(data.news.slice(0, 10));
        
    } catch (error) {
        console.error('Error loading news:', error);
        document.getElementById('newsGrid').innerHTML = 
            '<div class="loading">Failed to load news. Please refresh.</div>';
    }
}

function renderNews() {
    const grid = document.getElementById('newsGrid');
    
    if (!allNews || allNews.length === 0) {
        grid.innerHTML = '<div class="loading">No news available for selected interests</div>';
        return;
    }
    
    grid.innerHTML = allNews.map(item => {
        const pubDate = new Date(item.published);
        const timeAgo = getTimeAgo(pubDate);
        const categoryName = formatCategory(item.category);
        
        return `
            <div class="news-card" onclick="openNews('${item.link}')">
                <div class="news-source">
                    <span class="source-name">${item.source}</span>
                    <span class="news-time">${timeAgo}</span>
                </div>
                <h3 class="news-title">${item.title}</h3>
                <p class="news-summary">${item.summary || ''}</p>
                <div class="news-footer">
                    <span class="category-badge">${categoryName}</span>
                    <a href="${item.link}" class="read-more" target="_blank" 
                       onclick="event.stopPropagation()">Read More →</a>
                </div>
            </div>
        `;
    }).join('');
}

function updateTicker(headlines) {
    const ticker = document.getElementById('tickerContent');
    
    const tickerText = headlines
        .map(item => `${item.source}: ${item.title}`)
        .join(' • ');
    
    ticker.innerHTML = `<span>${tickerText}</span>`;
}

function getTimeAgo(date) {
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function formatCategory(category) {
    const categoryNames = {
        'gaming': '🎮 Gaming',
        'anime': '🎌 Anime',
        'culture': '🇯🇵 Culture',
        'food': '🍜 Food',
        'automotive': '🏎️ Cars',
        'art': '🎨 Art',
        'nature': '🌿 Nature',
        'restoration': '🔧 Restoration',
        'general_news': '📰 News'
    };
    
    return categoryNames[category] || category;
}

function openNews(url) {
    if (url) {
        window.open(url, '_blank');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadPreferences();
    loadInterests();
    loadNews();
    
    // Auto-refresh every 10 minutes
    setInterval(loadNews, 600000);
});
