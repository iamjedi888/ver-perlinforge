/**
 * TriptokForge - Verse Package Download UI
 * Add download button to forge interface
 */

// Add this to your forge.html or forge JavaScript file

class VerseDownloader {
    constructor() {
        this.currentVersePackage = null;
        this.currentSeed = null;
        this.init();
    }

    init() {
        // Create download button (call this after island generation)
        this.createDownloadButton();
        
        // Listen for island generation events
        window.addEventListener('islandGenerated', (e) => {
            this.handleIslandGenerated(e.detail);
        });
    }

    createDownloadButton() {
        const buttonHTML = `
            <button id="verseDownloadBtn" class="btn btn-primary" style="display: none;">
                <i class="fas fa-download"></i> Download UEFN Verse Package
            </button>
        `;
        
        // Insert button near the "Generate Island" button
        // Adjust selector based on your actual HTML structure
        const generateBtn = document.querySelector('#generateIslandBtn');
        if (generateBtn && generateBtn.parentElement) {
            generateBtn.parentElement.insertAdjacentHTML('beforeend', buttonHTML);
            
            // Add click handler
            document.getElementById('verseDownloadBtn').addEventListener('click', () => {
                this.downloadVersePackage();
            });
        }
    }

    handleIslandGenerated(data) {
        // Store verse package data from generation response
        if (data.verse_package) {
            this.currentVersePackage = data.verse_package;
            this.currentSeed = data.seed || data.island_seed || 0;
            
            // Show download button
            const btn = document.getElementById('verseDownloadBtn');
            if (btn) {
                btn.style.display = 'inline-block';
            }
            
            console.log('[VerseDownloader] Verse package ready for download');
        }
    }

    async downloadVersePackage() {
        if (!this.currentVersePackage) {
            alert('No Verse package available. Generate an island first.');
            return;
        }

        try {
            const btn = document.getElementById('verseDownloadBtn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Preparing zip...';
            btn.disabled = true;

            const response = await fetch('/api/forge/download-verse', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    verse_package: this.currentVersePackage,
                    island_seed: this.currentSeed
                })
            });

            if (!response.ok) {
                throw new Error(`Download failed: ${response.statusText}`);
            }

            // Get the blob and trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `island_${this.currentSeed}_verse_package.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            console.log('[VerseDownloader] Download complete');
            
            // Reset button
            btn.innerHTML = originalText;
            btn.disabled = false;

        } catch (error) {
            console.error('[VerseDownloader] Error:', error);
            alert('Failed to download Verse package. Check console for details.');
            
            const btn = document.getElementById('verseDownloadBtn');
            btn.innerHTML = '<i class="fas fa-download"></i> Download UEFN Verse Package';
            btn.disabled = false;
        }
    }

    // Load a previously saved verse package
    async loadSavedVerse(saveId, autoDownload = false) {
        try {
            const zipParam = autoDownload ? '?zip=true' : '';
            const response = await fetch(`/api/forge/get-saved-verse/${saveId}${zipParam}`);
            
            if (!response.ok) {
                throw new Error(`Failed to load saved verse: ${response.statusText}`);
            }

            if (autoDownload) {
                // Direct zip download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `saved_island_${saveId}_verse.zip`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                // Load into current session
                const data = await response.json();
                this.currentVersePackage = data.verse_package;
                this.currentSeed = data.seed;
                
                const btn = document.getElementById('verseDownloadBtn');
                if (btn) {
                    btn.style.display = 'inline-block';
                }
                
                console.log('[VerseDownloader] Loaded saved verse package');
            }

        } catch (error) {
            console.error('[VerseDownloader] Error loading saved verse:', error);
            alert('Failed to load saved Verse package.');
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.verseDownloader = new VerseDownloader();
});

// Helper: Dispatch custom event when island is generated
// Add this to your existing island generation code:
/*
function onIslandGenerationComplete(responseData) {
    // ... existing code ...
    
    // Dispatch event for verse downloader
    const event = new CustomEvent('islandGenerated', {
        detail: responseData
    });
    window.dispatchEvent(event);
}
*/
