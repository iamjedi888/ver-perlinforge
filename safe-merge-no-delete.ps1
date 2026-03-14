# ==================== SAFE MERGE SCRIPT (PowerShell) ====================
# Claude branch = base (your new theme stays protected)
# Oracle branch = everything gets copied over
# No files are deleted

Write-Host "=== SAFE MERGE: Claude base + ALL Oracle files (no deletions) ===" -ForegroundColor Green

# Switch to your theme branch
git checkout claude/vault-terminal-ui-design-HZhBW
git pull origin claude/vault-terminal-ui-design-HZhBW

# Create temp copy of Oracle branch
if (Test-Path "C:\temp\oracle-temp") { Remove-Item "C:\temp\oracle-temp" -Recurse -Force }
git worktree add C:\temp\oracle-temp oracle-vm-backup

# Copy EVERYTHING from Oracle into Claude branch
Copy-Item -Path "C:\temp\oracle-temp\*" -Destination "." -Recurse -Force
Copy-Item -Path "C:\temp\oracle-temp\.*" -Destination "." -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "✅ All Oracle files copied into Claude branch" -ForegroundColor Green

# Open diffs for the important files
Write-Host "Opening diffs in VS Code..." -ForegroundColor Cyan

code --diff server.py "C:\temp\oracle-temp\server.py"
code --diff "islandforge/static/css/dashboard.css" "C:\temp\oracle-temp\islandforge/static/css/dashboard.css" -ErrorAction SilentlyContinue
code --diff "islandforge/templates/whitepages/index.html" "C:\temp\oracle-temp\islandforge/templates/whitepages/index.html" -ErrorAction SilentlyContinue
code --diff requirements.txt "C:\temp\oracle-temp\requirements.txt"

Write-Host "`n=== REVIEW THE DIFFS IN VS CODE ===" -ForegroundColor Yellow
Write-Host "Left side  = your new theme (Claude)"
Write-Host "Right side = Oracle logic"
Write-Host "Keep your theme + copy any useful routes/logic from Oracle"
Write-Host "When you finish saving the files, press Enter here..."

Read-Host "Press Enter when ready"

git add .
git commit -m "Merged ALL files from oracle-vm-backup into Claude branch (theme preserved)"

Write-Host "✅ Merge complete!" -ForegroundColor Green
Write-Host "Next: git push origin claude/vault-terminal-ui-design-HZhBW"