/* TriptokForge VR Arena - Spectator Stadium */

// ═══════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎮 VR Arena initializing...');
    
    // Hide loading screen after A-Frame loads
    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
        console.log('✓ VR Arena ready');
    }, 2000);
    
    // Load leaderboard data
    loadLeaderboard();
    
    // Load video streams
    loadVideoStreams();
    
    // Update leaderboard every 30 seconds
    setInterval(loadLeaderboard, 30000);
});

// ═══════════════════════════════════════════════════════════════
// LEADERBOARD
// ═══════════════════════════════════════════════════════════════

async function loadLeaderboard() {
    console.log('📊 Loading leaderboard...');
    
    try {
        const response = await fetch('/api/leaderboard/global');
        const data = await response.json();
        
        if (data.players && data.players.length > 0) {
            renderLeaderboard(data.players.slice(0, 10)); // Top 10
        } else {
            renderPlaceholderLeaderboard();
        }
        
    } catch (error) {
        console.error('❌ Failed to load leaderboard:', error);
        renderPlaceholderLeaderboard();
    }
}

function renderLeaderboard(players) {
    const container = document.getElementById('leaderboard');
    container.innerHTML = ''; // Clear existing
    
    players.forEach((player, index) => {
        const yPos = -index * 0.7; // Vertical spacing
        
        // Rank number
        const rank = document.createElement('a-text');
        rank.setAttribute('value', `#${index + 1}`);
        rank.setAttribute('position', `0 ${yPos} 0`);
        rank.setAttribute('color', getRankColor(index));
        rank.setAttribute('width', '8');
        rank.setAttribute('align', 'left');
        
        // Player name
        const name = document.createElement('a-text');
        name.setAttribute('value', player.display_name || player.epic_username || 'Unknown');
        name.setAttribute('position', `1.5 ${yPos} 0`);
        name.setAttribute('color', '#c8d0e0');
        name.setAttribute('width', '8');
        name.setAttribute('align', 'left');
        
        // Wins
        const wins = document.createElement('a-text');
        wins.setAttribute('value', `${player.total_wins || 0} W`);
        wins.setAttribute('position', `8 ${yPos} 0`);
        wins.setAttribute('color', '#00e5a0');
        wins.setAttribute('width', '8');
        wins.setAttribute('align', 'right');
        
        // Eliminations
        const elims = document.createElement('a-text');
        elims.setAttribute('value', `${player.total_eliminations || 0} E`);
        elims.setAttribute('position', `11 ${yPos} 0`);
        elims.setAttribute('color', '#ff6b35');
        elims.setAttribute('width', '8');
        elims.setAttribute('align', 'right');
        
        container.appendChild(rank);
        container.appendChild(name);
        container.appendChild(wins);
        container.appendChild(elims);
    });
    
    console.log(`✓ Rendered ${players.length} players on leaderboard`);
}

function renderPlaceholderLeaderboard() {
    // Fake data for demo purposes
    const placeholderData = [
        { display_name: 'NinjaWarrior', total_wins: 342, total_eliminations: 8521 },
        { display_name: 'BuildMaster99', total_wins: 298, total_eliminations: 7234 },
        { display_name: 'SniperElite', total_wins: 276, total_eliminations: 6891 },
        { display_name: 'StormChaser', total_wins: 245, total_eliminations: 6543 },
        { display_name: 'VictoryRoyale', total_wins: 234, total_eliminations: 6012 },
        { display_name: 'TiltedTowers', total_wins: 198, total_eliminations: 5678 },
        { display_name: 'LootLegend', total_wins: 187, total_eliminations: 5234 },
        { display_name: 'CrankMaster', total_wins: 165, total_eliminations: 4987 },
        { display_name: 'BoxFighter', total_wins: 142, total_eliminations: 4321 },
        { display_name: 'EditKing', total_wins: 128, total_eliminations: 3987 }
    ];
    
    renderLeaderboard(placeholderData);
}

function getRankColor(index) {
    if (index === 0) return '#FFD700'; // Gold
    if (index === 1) return '#C0C0C0'; // Silver
    if (index === 2) return '#CD7F32'; // Bronze
    return '#00e5a0'; // Default cyan
}

// ═══════════════════════════════════════════════════════════════
// VIDEO STREAMS
// ═══════════════════════════════════════════════════════════════

function loadVideoStreams() {
    console.log('📺 Loading video streams...');
    
    // Stream 1: ABC News (from channels)
    const stream1 = document.getElementById('stream1');
    stream1.src = 'https://www.youtube.com/embed/w_Ma8oQLmSM?autoplay=1&mute=1&controls=0';
    
    // Stream 2: NASA TV
    const stream2 = document.getElementById('stream2');
    stream2.src = 'https://www.youtube.com/embed/21X5lGlDOfg?autoplay=1&mute=1&controls=0';
    
    console.log('✓ Video streams loaded');
}

// ═══════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════

// Auto-hide controls help after 10 seconds
setTimeout(() => {
    const help = document.getElementById('controls-help');
    if (help) {
        help.style.opacity = '0';
        help.style.transition = 'opacity 1s';
        setTimeout(() => help.style.display = 'none', 1000);
    }
}, 10000);

console.log('🎬 Arena script loaded');
