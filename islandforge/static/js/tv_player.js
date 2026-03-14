/* TriptokForge TV Player - Pluto TV Style */

// ═══════════════════════════════════════════════════════════════
// GLOBAL VARIABLES
// ═══════════════════════════════════════════════════════════════

let player;                    // YouTube player object
let channels = [];             // List of all channels
let currentChannelIndex = 0;   // Which channel we're watching
let epgData = {};              // TV Guide data

// ═══════════════════════════════════════════════════════════════
// STEP 1: Load All Channels from Backend
// ═══════════════════════════════════════════════════════════════

async function loadChannels() {
    console.log('📡 Loading channels...');
    
    try {
        const response = await fetch('/api/channels');
        const data = await response.json();
        
        channels = data.channels;
        console.log(`✓ Loaded ${channels.length} channels`);
        
        // Start playing first channel
        if (channels.length > 0) {
            playChannel(0);
        }
        
    } catch (error) {
        console.error('❌ Failed to load channels:', error);
    }
}

// ═══════════════════════════════════════════════════════════════
// STEP 2: Initialize YouTube Player
// This function is called automatically by YouTube API
// ═══════════════════════════════════════════════════════════════

function onYouTubeIframeAPIReady() {
    console.log('📺 YouTube API ready');
    
    // Create YouTube player
    player = new YT.Player('player', {
        height: '100%',
        width: '100%',
        videoId: '',  // Will be set when we play a channel
        playerVars: {
            autoplay: 1,      // Start playing immediately
            controls: 0,      // Hide YouTube controls
            modestbranding: 1, // Hide YouTube logo
            rel: 0,           // Don't show related videos
            showinfo: 0,      // Hide video info
            fs: 0,            // Hide fullscreen button
            iv_load_policy: 3 // Hide annotations
        },
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
        }
    });
}

// ═══════════════════════════════════════════════════════════════
// STEP 3: Player Ready - Load Channels
// ═══════════════════════════════════════════════════════════════

function onPlayerReady(event) {
    console.log('✓ Player ready');
    loadChannels();
}

// ═══════════════════════════════════════════════════════════════
// STEP 4: Handle Player State Changes (playing, paused, etc.)
// ═══════════════════════════════════════════════════════════════

function onPlayerStateChange(event) {
    // When video starts playing, hide loading screen
    if (event.data === YT.PlayerState.PLAYING) {
        document.getElementById('loadingScreen').classList.add('hidden');
    }
}

// ═══════════════════════════════════════════════════════════════
// STEP 5: Play a Channel
// ═══════════════════════════════════════════════════════════════

function playChannel(index) {
    // Make sure index is valid
    if (index < 0) index = channels.length - 1;
    if (index >= channels.length) index = 0;
    
    currentChannelIndex = index;
    const channel = channels[index];
    
    console.log(`▶️ Playing: ${channel.name}`);
    
    // Show loading screen
    document.getElementById('loadingScreen').classList.remove('hidden');
    
    // Load video in YouTube player
    if (player && player.loadVideoById) {
        player.loadVideoById(channel.stream_id);
    }
    
    // Update info card
    updateInfoCard(channel);
    
    // Load schedule for this channel
    loadChannelSchedule(channel.id);
}

// ═══════════════════════════════════════════════════════════════
// STEP 6: Update Info Card (top-left overlay)
// ═══════════════════════════════════════════════════════════════

function updateInfoCard(channel) {
    // Update channel number
    document.querySelector('.channel-number').textContent = channel.number;
    
    // Update channel name
    document.querySelector('.channel-name').textContent = channel.name;
    
    // Update channel logo
    const logoImg = document.getElementById('channelLogo');
    logoImg.src = channel.logo || '';
    logoImg.alt = channel.name;
    
    // Update program title (will be replaced when schedule loads)
    document.querySelector('.program-title').textContent = 'Loading schedule...';
}

// ═══════════════════════════════════════════════════════════════
// STEP 7: Load EPG Schedule for Current Channel
// ═══════════════════════════════════════════════════════════════

async function loadChannelSchedule(channelId) {
    try {
        const response = await fetch(`/api/channels/${channelId}/schedule`);
        const data = await response.json();
        
        if (data.schedule && data.schedule.length > 0) {
            // Find what's playing NOW
            const now = new Date();
            const currentProgram = data.schedule.find(program => {
                const start = new Date(program.start);
                const end = new Date(program.end);
                return now >= start && now < end;
            });
            
            if (currentProgram) {
                document.querySelector('.program-title').textContent = currentProgram.title;
            }
        }
        
    } catch (error) {
        console.error('Failed to load schedule:', error);
    }
}

// ═══════════════════════════════════════════════════════════════
// STEP 8: Load Full EPG (All Channels)
// ═══════════════════════════════════════════════════════════════

async function loadEPG() {
    console.log('📋 Loading EPG...');
    
    try {
        const response = await fetch('/api/epg');
        epgData = await response.json();
        
        console.log('✓ EPG loaded');
        renderEPG();
        
    } catch (error) {
        console.error('❌ Failed to load EPG:', error);
    }
}

// ═══════════════════════════════════════════════════════════════
// STEP 9: Render EPG Guide
// ═══════════════════════════════════════════════════════════════

function renderEPG() {
    const epgGrid = document.getElementById('epgGrid');
    epgGrid.innerHTML = '';  // Clear existing content
    
    channels.forEach((channel, index) => {
        const channelData = epgData[channel.id];
        
        // Find current program
        let currentProgram = 'No schedule available';
        if (channelData && channelData.schedule) {
            const now = new Date();
            const program = channelData.schedule.find(p => {
                const start = new Date(p.start);
                const end = new Date(p.end);
                return now >= start && now < end;
            });
            if (program) currentProgram = program.title;
        }
        
        // Create channel row
        const channelDiv = document.createElement('div');
        channelDiv.className = 'epg-channel';
        channelDiv.onclick = () => {
            playChannel(index);
            closeEPG();
        };
        
        channelDiv.innerHTML = `
            <div class="epg-channel-number">${channel.number}</div>
            <div class="epg-channel-logo">
                <img src="${channel.logo}" alt="${channel.name}">
            </div>
            <div class="epg-channel-info">
                <div class="epg-channel-name">${channel.name}</div>
                <div class="epg-program-title">${currentProgram}</div>
            </div>
        `;
        
        epgGrid.appendChild(channelDiv);
    });
}

// ═══════════════════════════════════════════════════════════════
// STEP 10: Toggle EPG Overlay
// ═══════════════════════════════════════════════════════════════

function toggleEPG() {
    const overlay = document.getElementById('epgOverlay');
    
    if (overlay.classList.contains('epg-hidden')) {
        // Opening EPG
        loadEPG();  // Load fresh data
        overlay.classList.remove('epg-hidden');
    } else {
        // Closing EPG
        closeEPG();
    }
}

function closeEPG() {
    document.getElementById('epgOverlay').classList.add('epg-hidden');
}

// ═══════════════════════════════════════════════════════════════
// STEP 11: Keyboard Controls
// ═══════════════════════════════════════════════════════════════

document.addEventListener('keydown', (event) => {
    switch(event.key) {
        case 'g':
        case 'G':
            // Open/close TV Guide
            toggleEPG();
            break;
            
        case 'ArrowUp':
            // Previous channel
            playChannel(currentChannelIndex - 1);
            break;
            
        case 'ArrowDown':
            // Next channel
            playChannel(currentChannelIndex + 1);
            break;
            
        case 'i':
        case 'I':
            // Toggle info card
            document.getElementById('infoCard').classList.toggle('hidden');
            break;
            
        case 'Escape':
            // Close EPG if open
            closeEPG();
            break;
    }
});

// ═══════════════════════════════════════════════════════════════
// STEP 12: Close EPG Button
// ═══════════════════════════════════════════════════════════════

document.getElementById('closeEpg').addEventListener('click', closeEPG);

console.log('🎬 TV Player initialized');
