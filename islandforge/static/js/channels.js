// TriptokForge TV Guide JavaScript

let currentChannel = null;
let channels = [];
let epgData = null;

async function loadChannels() {
    const response = await fetch('/api/channels');
    const data = await response.json();
    channels = data.channels.sort((a, b) => a.number - b.number);
    
    renderChannelList();
    
    if (channels.length > 0) {
        switchChannel(channels[0].id);
    }
}

function renderChannelList() {
    const list = document.getElementById('channelList');
    
    list.innerHTML = channels.map(ch => {
        const isActive = currentChannel === ch.id;
        const liveBadge = ch.live ? '<span class="live-badge">● LIVE</span>' : 'VOD';
        
        return `
            <div class="channel-item${isActive ? ' active' : ''}" 
                 data-channel="${ch.id}">
                <div class="channel-number">${ch.number}</div>
                <div class="channel-info">
                    <div class="channel-name">${ch.name}</div>
                    <div class="channel-status">${liveBadge}</div>
                </div>
            </div>
        `;
    }).join('');
    
    document.querySelectorAll('.channel-item').forEach(item => {
        item.addEventListener('click', function() {
            const channelId = this.getAttribute('data-channel');
            switchChannel(channelId);
        });
    });
}

function switchChannel(channelId) {
    currentChannel = channelId;
    const channel = channels.find(c => c.id === channelId);
    
    if (!channel) return;
    
    renderChannelList();
    loadPlayer(channel);
    updateNowPlaying(channelId);
}

function loadPlayer(channel) {
    const wrapper = document.getElementById('playerWrapper');
    
    let embedUrl = '';
    const hostname = window.location.hostname;
    
    if (channel.type === 'twitch') {
        embedUrl = `https://player.twitch.tv/?channel=${channel.stream_id}&parent=${hostname}&muted=false`;
    } else if (channel.type === 'youtube') {
        embedUrl = `https://www.youtube.com/embed/live_stream?channel=${channel.stream_id}&autoplay=1`;
    }
    
    wrapper.innerHTML = `
        <iframe 
            src="${embedUrl}"
            frameborder="0"
            allow="autoplay; fullscreen"
            allowfullscreen>
        </iframe>
        <div class="player-info">
            <div class="now-playing">NOW PLAYING</div>
            <div class="program-title" id="currentProgram">Loading...</div>
        </div>
    `;
}

async function updateNowPlaying(channelId) {
    try {
        const response = await fetch(`/api/channels/${channelId}/schedule?days=1`);
        const data = await response.json();
        
        const now = new Date();
        const current = data.schedule.find(p => {
            const start = new Date(p.start);
            const end = new Date(p.end);
            return start <= now && now <= end;
        });
        
        const el = document.getElementById('currentProgram');
        if (current && el) {
            el.textContent = current.title;
        }
    } catch (error) {
        console.error('Error loading schedule:', error);
    }
}

async function loadGuide(hours) {
    try {
        const response = await fetch(`/api/channels/epg?hours=${hours}`);
        epgData = await response.json();
        renderGuide();
    } catch (error) {
        console.error('Error loading guide:', error);
    }
}

function renderGuide() {
    if (!epgData) return;
    
    const grid = document.getElementById('guideGrid');
    const startTime = new Date(epgData.start_time);
    
    const timeline = [];
    for (let i = 0; i < epgData.hours; i++) {
        const time = new Date(startTime.getTime() + i * 60 * 60 * 1000);
        timeline.push(time.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true }));
    }
    
    let html = '<div class="timeline">' + 
        timeline.map(t => `<div class="time-slot">${t}</div>`).join('') + 
        '</div>';
    
    epgData.channels.forEach(channelData => {
        const channel = channelData.channel;
        const programsHtml = channelData.programs.map(prog => {
            const now = new Date();
            const start = new Date(prog.start);
            const end = new Date(prog.end);
            const isLive = start <= now && now <= end;
            const width = (prog.duration / 60) * 200;
            const timeStr = start.toLocaleTimeString('en-US', {hour:'numeric', minute:'2-digit', hour12:true});
            
            return `<div class="guide-program${isLive ? ' live' : ''}" style="min-width:${width}px" data-channel="${channel.id}">
                <div class="program-time">${timeStr}</div>
                <div class="program-name">${prog.title}</div>
            </div>`;
        }).join('');
        
        html += `<div class="guide-row">
            <div class="guide-channel-label">
                <div>
                    <div style="font-weight:700">${channel.number}</div>
                    <div style="font-size:10px;color:var(--dim)">${channel.name}</div>
                </div>
            </div>
            <div class="guide-programs">${programsHtml}</div>
        </div>`;
    });
    
    grid.innerHTML = html;
    
    document.querySelectorAll('.guide-program').forEach(prog => {
        prog.addEventListener('click', function() {
            const channelId = this.getAttribute('data-channel');
            switchChannel(channelId);
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    loadChannels();
    loadGuide(12);
    
    document.getElementById('btn6h').addEventListener('click', () => loadGuide(6));
    document.getElementById('btn12h').addEventListener('click', () => loadGuide(12));
    document.getElementById('btn24h').addEventListener('click', () => loadGuide(24));
    
    setInterval(() => {
        if (currentChannel) {
            updateNowPlaying(currentChannel);
        }
    }, 60000);
});
