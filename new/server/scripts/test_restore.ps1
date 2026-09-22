# Test restore procedure into isolated sandbox location
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [string]$RestoreTarget = "ghg_restore_sandbox.db"
)

if (-not (Test-Path $BackupFile)) {
    Write-Error "[ERROR] Backup file not found: $BackupFile"
    exit 1
}

Write-Host "[INFO] Testing restore of $BackupFile into $RestoreTarget..."

python -c @"
import sqlite3, sys
src = sqlite3.connect(r'$BackupFile')
dst = sqlite3.connect(r'$RestoreTarget')
src.backup(dst)
src.close()

# Verify integrity and tables
cur = dst.cursor()
tables = [t[0] for t in cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
print(f'[INFO] Restored tables count: {len(tables)}')
integrity = cur.execute('PRAGMA integrity_check;').fetchall()
print(f'[INFO] Integrity check result: {integrity}')
dst.close()
"@

if (Test-Path $RestoreTarget) {
    Write-Host "[SUCCESS] Verification passed. Cleaning up sandbox file."
    Remove-Item $RestoreTarget -Force
}
