# OSINT E-post Etterforsker - Database Backup Script (Windows / PowerShell)
# Run manually or via Windows Task Scheduler.
#
# To register as a daily scheduled task (run once as Administrator):
#   .\scripts\schedule_backup.ps1
#
# Manual run:
#   .\scripts\run_backup.ps1

$ErrorActionPreference = "Stop"

$ProjectDir  = Split-Path -Parent $PSScriptRoot
$BackupDir   = Join-Path $ProjectDir "backups"
$Timestamp   = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile  = Join-Path $BackupDir "osint_backup_$Timestamp.sql.gz"
$LogFile     = Join-Path $ProjectDir "logs" "backup.log"
$RetainDays  = 30

# ── helpers ──────────────────────────────────────────────────────────────────
function Log($msg) { $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"; Write-Host $line; Add-Content -Path $LogFile -Value $line }
function Die($msg) { Log "ERROR: $msg"; exit 1 }

# ── ensure dirs ──────────────────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $BackupDir  | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

Log "Starting database backup → $BackupFile"

# ── run pg_dump inside the database container ─────────────────────────────
$envFile = Join-Path $ProjectDir ".env.production"
if (-not (Test-Path $envFile)) {
    Die ".env.production not found at $envFile. Run scripts/generate_prod_env.py first."
}

# Parse required vars from .env.production
$envVars = @{}
Get-Content $envFile | Where-Object { $_ -match "^\s*([A-Z_]+)\s*=\s*(.+)$" } | ForEach-Object {
    if ($_ -match "^\s*([A-Z_]+)\s*=\s*(.+)$") { $envVars[$matches[1]] = $matches[2].Trim() }
}

$PgUser   = $envVars["POSTGRES_USER"]   ?? "osint_user"
$PgPass   = $envVars["POSTGRES_PASSWORD"] ?? ""
$PgDb     = $envVars["POSTGRES_DB"]     ?? "osint_db"

if (-not $PgPass) { Die "POSTGRES_PASSWORD not set in .env.production" }

# pg_dump runs inside the osint-database container; output piped through gzip on host
$dumpCmd = "pg_dump -U $PgUser -d $PgDb --no-password"

try {
    docker exec -e "PGPASSWORD=$PgPass" osint-database bash -c $dumpCmd | `
        & { param($input) $input | gzip } | `
        Set-Content -AsByteStream -Path $BackupFile

    $sizeMB = [math]::Round((Get-Item $BackupFile).Length / 1MB, 2)
    Log "Backup completed: $BackupFile ($sizeMB MB)"
} catch {
    Die "pg_dump failed: $_"
}

# ── prune old backups ─────────────────────────────────────────────────────
$cutoff = (Get-Date).AddDays(-$RetainDays)
$pruned = 0
Get-ChildItem -Path $BackupDir -Filter "osint_backup_*.sql.gz" |
    Where-Object { $_.LastWriteTime -lt $cutoff } |
    ForEach-Object { Remove-Item $_.FullName; $pruned++ }

if ($pruned -gt 0) { Log "Pruned $pruned backup(s) older than $RetainDays days." }
Log "Done."
