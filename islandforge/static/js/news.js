// TriptokForge News JavaScript

let currentRegion = 'all';
let allNews = [];

async function loadLatestNews() {
    try {
        const response = await fetch('/api/news/latest');
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

async function loadRegionNews(region) {
    try {
        document.getElementById('newsGrid').innerHTML = 
            '<div class="loading">Loading news</div>';
        
        const response = await fetch(`/api/news/region/${region}`);
        const data = await response.json();
        
        allNews = data.news;
        renderNews();
        
    } catch (error) {
        console.error('Error loading region news:', error);
    }
}

function renderNews() {
    const grid = document.getElementById('newsGrid');
    
    if (!allNews || allNews.length === 0) {
        grid.innerHTML = '<div class="loading">No news available</div>';
        return;
    }
    
    grid.innerHTML = allNews.map(item => {
        const pubDate = new Date(item.published);
        const timeAgo = getTimeAgo(pubDate);
        const regionName = formatRegion(item.region || 'global');
        
        return `
            <div class="news-card" onclick="openNews('${item.link}')">
                <div class="news-source">
                    <span class="source-name">${item.source}</span>
                    <span class="news-time">${timeAgo}</span>
                </div>
                <h3 class="news-title">${item.title}</h3>
                <p class="news-summary">${item.summary || ''}</p>
                <div class="news-footer">
                    <span class="region-badge">${regionName}</span>
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

function formatRegion(region) {
    const regionNames = {
        'rhode_island': 'Rhode Island',
        'japan': 'Japan',
        'new_york': 'New York',
        'california': 'California',
        'hawaii': 'Hawaii',
        'mexico': 'Mexico',
        'global': 'World'
    };
    
    return regionNames[region] || region;
}

function openNews(url) {
    if (url) {
        window.open(url, '_blank');
    }
}

// Tab switching
document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.tab-btn');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const region = this.getAttribute('data-region');
            
            // Update active state
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Load news for region
            currentRegion = region;
            
            if (region === 'all') {
                loadLatestNews();
            } else {
                loadRegionNews(region);
            }
        });
    });
    
    // Initial load
    loadLatestNews();
    
    // Auto-refresh every 5 minutes
    setInterval(() => {
        if (currentRegion === 'all') {
            loadLatestNews();
        } else {
            loadRegionNews(currentRegion);
        }
    }, 300000);
});
