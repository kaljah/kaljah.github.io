# Backup procedure for SQLite database using online hot backup API
param(
    [string]$DbPath = "ghg_app.db",
    [string]$BackupDir = "backups"
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
}

$destPath = Join-Path $BackupDir "ghg_app_$timestamp.db"

Write-Host "[INFO] Starting safe online backup from $DbPath to $destPath..."

python -c @"
import sqlite3, sys
src = sqlite3.connect('$DbPath')
dst = sqlite3.connect('$destPath')
src.backup(dst)
src.close()
dst.close()
print('[SUCCESS] Hot backup completed successfully.')
"@

if (Test-Path $destPath) {
    $sizeBytes = (Get-Item $destPath).Length
    $sizeMB = [math]::Round($sizeBytes / 1MB, 2)
    Write-Host "[INFO] Verified backup size: $sizeMB MB at $destPath"
} else {
    Write-Error "[ERROR] Backup file was not created."
}
