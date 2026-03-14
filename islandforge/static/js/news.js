let prefs = { interests: [], filter_negative: true };
let currentCategory = 'all';

async function loadPrefs() {
    try {
        const res = await fetch('/api/news/preferences');
        prefs = await res.json();
        document.getElementById('filterNegative').checked = prefs.filter_negative;
        await loadInterests();
    } catch (e) {
        console.error('Error loading prefs:', e);
    }
}

async function savePrefs() {
    const checkboxes = document.querySelectorAll('.interest-checkbox');
    prefs.interests = [];
    checkboxes.forEach(cb => {
        if (cb.checked) prefs.interests.push(cb.value);
    });
    prefs.filter_negative = document.getElementById('filterNegative').checked;
    
    try {
        await fetch('/api/news/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(prefs)
        });
        loadNews();
    } catch (e) {
        console.error('Error saving prefs:', e);
    }
}

async function loadInterests() {
    try {
        const res = await fetch('/api/news/interests');
        const interests = await res.json();
        
        const grid = document.getElementById('interestsGrid');
        grid.innerHTML = Object.entries(interests).map(([id, data]) => `
            <div class="interest-item">
                <input type="checkbox" class="interest-checkbox" value="${id}" 
                       id="int_${id}" ${prefs.interests.includes(id) ? 'checked' : ''}
                       onchange="savePrefs()">
                <label for="int_${id}">${data.name}</label>
                <small>${data.category}</small>
            </div>
        `).join('');
    } catch (e) {
        console.error('Error loading interests:', e);
    }
}

async function loadNews() {
    try {
        const res = await fetch('/api/news/latest');
        const data = await res.json();
        renderNews(data.news);
        updateTicker(data.news.slice(0, 10));
    } catch (e) {
        console.error('Error loading news:', e);
    }
}

function renderNews(news) {
    const grid = document.getElementById('newsGrid');
    if (!news || news.length === 0) {
        grid.innerHTML = '<div class="loading">No news for your selected interests</div>';
        return;
    }
    
    grid.innerHTML = news.map(item => `
        <div class="news-card" onclick="window.open('${item.link}', '_blank')">
            <div class="news-source">${item.source}</div>
            <h3 class="news-title">${item.title}</h3>
            <p class="news-summary">${item.summary || ''}</p>
        </div>
    `).join('');
}

function updateTicker(news) {
    const ticker = document.getElementById('tickerContent');
    const text = news.map(n => `${n.source}: ${n.title}`).join(' • ');
    ticker.innerHTML = `<span>${text}</span>`;
}

function togglePrefs() {
    document.getElementById('prefsPanel').classList.toggle('open');
}

document.addEventListener('DOMContentLoaded', function() {
    loadPrefs().then(() => loadNews());
    
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', async function() {
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            currentCategory = this.getAttribute('data-cat');
            
            if (currentCategory === 'all') {
                loadNews();
            } else {
                const res = await fetch(`/api/news/category/${currentCategory}`);
                const data = await res.json();
                renderNews(data.news);
            }
        });
    });
    
    setInterval(loadNews, 300000);
});
