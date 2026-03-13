# TriptokForge Compression System - Auto-Deploy Script (Windows PowerShell)
# Run this in your ver-perlinforge directory

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TriptokForge Compression Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check we're in the right directory
if (!(Test-Path "islandforge")) {
    Write-Host "❌ ERROR: Run this from ver-perlinforge directory" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found islandforge directory" -ForegroundColor Green

# Step 1: Add imports to forge.py
Write-Host "📝 Adding imports to forge.py..." -ForegroundColor Yellow

$forgePy = "islandforge\forge.py"
$forgeContent = Get-Content $forgePy -Raw

if ($forgeContent -match "from compression_utils import") {
    Write-Host "  ⚠️  Imports already exist, skipping..." -ForegroundColor Yellow
} else {
    # Find last import and add after it
    $importBlock = @"

# Compression utilities
from compression_utils import compress_verse_package, decompress_verse_package, create_verse_package_zip
from flask import send_file
import io
"@
    
    # Add after the imports section
    $forgeContent = $forgeContent -replace "(import.*\n)+", "`$0$importBlock`n"
    Set-Content $forgePy -Value $forgeContent -NoNewline
    Write-Host "  ✓ Imports added" -ForegroundColor Green
}

# Step 2: Add download routes to forge.py
Write-Host "📝 Adding download routes to forge.py..." -ForegroundColor Yellow

$forgeContent = Get-Content $forgePy -Raw

if ($forgeContent -match "download_verse_package") {
    Write-Host "  ⚠️  Routes already exist, skipping..." -ForegroundColor Yellow
} else {
    $routesBlock = @"


@forge_bp.route('/api/forge/download-verse', methods=['POST'])
def download_verse_package():
    '''Download Verse package as zip'''
    try:
        data = request.get_json()
        verse_package = data.get('verse_package')
        island_seed = data.get('island_seed', 0)
        
        if not verse_package:
            return jsonify({'error': 'No verse_package provided'}), 400
        
        zip_bytes = create_verse_package_zip(verse_package, island_seed)
        
        return send_file(
            io.BytesIO(zip_bytes),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'island_{island_seed}_verse_package.zip'
        )
        
    except Exception as e:
        print(f'[verse_download] Error: {e}')
        return jsonify({'error': str(e)}), 500


@forge_bp.route('/api/forge/get-saved-verse/<int:save_id>', methods=['GET'])
def get_saved_verse_package(save_id):
    '''Retrieve saved Verse package from Oracle'''
    try:
        import oracle_db
        
        query = '''
            SELECT verse_data, seed, display_name 
            FROM island_saves 
            WHERE id = :save_id
        '''
        
        result = oracle_db.execute_query(query, {'save_id': save_id})
        
        if not result:
            return jsonify({'error': 'Save not found'}), 404
        
        row = result[0]
        compressed_verse = row[0]
        seed = row[1]
        display_name = row[2]
        
        if not compressed_verse:
            return jsonify({'error': 'No Verse data saved'}), 404
        
        verse_package = decompress_verse_package(compressed_verse)
        
        download_zip = request.args.get('zip', 'false').lower() == 'true'
        
        if download_zip:
            zip_bytes = create_verse_package_zip(verse_package, seed)
            filename = f'{display_name or f"island_{seed}"}_verse.zip'
            
            return send_file(
                io.BytesIO(zip_bytes),
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({
                'verse_package': verse_package,
                'seed': seed,
                'display_name': display_name
            })
        
    except Exception as e:
        print(f'[get_saved_verse] Error: {e}')
        return jsonify({'error': str(e)}), 500
"@
    
    Add-Content $forgePy -Value $routesBlock
    Write-Host "  ✓ Routes added" -ForegroundColor Green
}

# Step 3: Create static/js directory
Write-Host "📁 Creating static/js directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "islandforge\static\js" -Force | Out-Null
Write-Host "  ✓ Directory ready" -ForegroundColor Green

# Step 4: Move verse_downloader.js
Write-Host "📝 Moving verse_downloader.js..." -ForegroundColor Yellow
if (Test-Path "islandforge\verse_downloader.js") {
    Move-Item "islandforge\verse_downloader.js" "islandforge\static\js\" -Force
    Write-Host "  ✓ Moved to static/js/" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  verse_downloader.js not found" -ForegroundColor Yellow
}

# Step 5: Update forge.html
Write-Host "📝 Updating forge.html..." -ForegroundColor Yellow

$forgeHtml = "islandforge\templates\forge.html"

if (!(Test-Path $forgeHtml)) {
    Write-Host "  ⚠️  forge.html not found" -ForegroundColor Yellow
} else {
    $htmlContent = Get-Content $forgeHtml -Raw
    
    if ($htmlContent -match "verse_downloader.js") {
        Write-Host "  ⚠️  Script tag already exists, skipping..." -ForegroundColor Yellow
    } else {
        $scriptTag = "<script src=`"{{ url_for('static', filename='js/verse_downloader.js') }}`"></script>`n</body>"
        $htmlContent = $htmlContent -replace "</body>", $scriptTag
        Set-Content $forgeHtml -Value $htmlContent -NoNewline
        Write-Host "  ✓ Script tag added" -ForegroundColor Green
    }
}

# Step 6: Test compression
Write-Host ""
Write-Host "🧪 Running compression tests..." -ForegroundColor Yellow
python islandforge\test_compression.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. git add -A"
    Write-Host "2. git commit -m 'Add compression and zip download'"
    Write-Host "3. git push origin main"
    Write-Host "4. SSH to Oracle VM and pull"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Tests failed. Check output above." -ForegroundColor Red
    exit 1
}
