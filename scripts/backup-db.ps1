# scripts/backup-db.ps1
# Backs up the Saksha Supabase (pooler) database into backups\saksha_<timestamp>.dump
# using a throwaway PostgreSQL 16 Docker container (no local Postgres needed).
#
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\backup-db.ps1
#
# Restore later (example):
#   docker run --rm -v "$PWD\backups:/backup" postgres:16 ^
#     pg_restore --no-owner --no-privileges -h <host> -p 5432 -U <user> -d <db> ^
#     "/backup/saksha_20260907_153000.dump"

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root 'backend\.env'
$backupDir = Join-Path $root 'backups'

if (-not (Test-Path -LiteralPath $envFile)) { throw "backend\.env not found at $envFile" }
if (-not (Test-Path -LiteralPath $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }

$kv = @{}
Get-Content -LiteralPath $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') {
        $kv[$matches[1]] = $matches[2].Trim().Trim('"').Trim("'")
    }
}

$url = $kv['DATABASE_URL']
if (-not $url) { throw 'DATABASE_URL is not set in backend\.env' }
if ($url -like '*@*') {
    $serverPart = $url.Substring($url.IndexOf('@') + 1)
    $db = $serverPart.Substring($serverPart.IndexOf('/') + 1).Split('?')[0]
    $auth = $url.Substring($url.IndexOf('//') + 2, $url.IndexOf('@') - $url.IndexOf('//') - 2)
    $user = $auth.Split(':')[0]
    $pass = [System.Uri]::UnescapeDataString($auth.Substring($auth.IndexOf(':') + 1))
    $hostPart = $serverPart.Split('/')[0]
    if ($hostPart -match '^(.+):(\d+)$') { $host0 = $matches[1]; $port = [int]$matches[2] }
    else { $host0 = $hostPart; $port = 5432 }
} else {
    throw 'Only postgres DATABASE_URL (host:port/user:pass) is supported by this script.'
}

if (-not $db -or -not $user -or -not $host0) { throw 'Could not parse DATABASE_URL into host/db/user.' }

# Session pooler (5432) gives pg_dump one stable connection; transaction
# pooler (6543) can also work, so that is the fallback.
$ports = @(5432, 6543)
if ($port -ne 5432 -and $port -ne 6543) { $ports = @($port) + $ports }

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$leaf = "saksha_$stamp.dump"
$dumpFile = Join-Path $backupDir $leaf

foreach ($p in $ports) {
    Write-Host "Dumping ${host0}:$p / $db -> backups\$leaf ..."
    $dockerArgs = @(
        'run', '--rm',
        '-e', "PGPASSWORD=$pass",
        '-v', "$backupDir`:/backup",
        'postgres:16',
        'pg_dump', '--no-owner', '--no-privileges',
        '-h', $host0, '-p', "$p", '-U', $user, '-d', $db,
        '-F', 'c', '-f', "/backup/$leaf"
    )
    & docker @dockerArgs
    if ($LASTEXITCODE -eq 0) {
        $size = if ((Test-Path -LiteralPath $dumpFile)) { "{0:N1} MB" -f ((Get-Item -LiteralPath $dumpFile).Length / 1MB) } else { '?' }
        Write-Host "OK. Backup written: $dumpFile ($size)"
        exit 0
    } else {
        Write-Host "Port $p failed (exit $LASTEXITCODE); trying next." -ForegroundColor Yellow
        if (Test-Path -LiteralPath $dumpFile) { Remove-Item -LiteralPath $dumpFile -Force }
    }
}

throw 'pg_dump failed on all ports.'