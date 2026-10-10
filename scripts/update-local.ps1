# Local development update only. Explicit operator invocation is required.
# Never use this script on production; see docs/production-deployment.md.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$ApprovedSha,
    [string]$BackupDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-ExitCode {
    param([string]$Operation)
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed (exit code $LASTEXITCODE). Existing backup is retained."
    }
}

$repoDirectory = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($BackupDirectory)) {
    $BackupDirectory = Join-Path (Split-Path -Parent $repoDirectory) 'placespermbot-backups'
}
$BackupDirectory = [System.IO.Path]::GetFullPath($BackupDirectory)

Push-Location $repoDirectory
try {
    # Refuse an uncommitted checkout or an unknown/non-main release.
    & git fetch origin main
    Assert-ExitCode 'git fetch'
    $dirty = @(& git status --porcelain --untracked-files=all)
    Assert-ExitCode 'git status'
    if ($dirty.Count -gt 0) {
        throw 'Working tree is not clean; commit or preserve local changes before updating.'
    }
    $resolvedSha = @(& git rev-parse --verify "$ApprovedSha^{commit}")
    Assert-ExitCode 'git rev-parse'
    if ($resolvedSha.Count -ne 1 -or $resolvedSha[0].Trim() -ne $ApprovedSha.ToLowerInvariant()) {
        throw 'Approved SHA does not resolve to the exact requested commit.'
    }
    & git merge-base --is-ancestor $ApprovedSha origin/main
    Assert-ExitCode 'Verify commit belongs to origin/main'

    & docker compose config --quiet
    Assert-ExitCode 'Validate Docker Compose configuration'
    $runningServices = @(& docker compose ps --status running --services)
    Assert-ExitCode 'Inspect running Compose services'
    if ($runningServices -notcontains 'bot') {
        throw 'The bot must already be running for a safe local update.'
    }
    $environmentOutput = @(
        & docker compose exec -T bot python -c 'from app.config import get_settings; print(get_settings().environment)'
    )
    Assert-ExitCode 'Read running environment'
    if (($environmentOutput -join '').Trim() -ne 'development') {
        throw 'This script is development-only. Use the production operator checklist instead.'
    }
    & docker compose exec -T bot python -m app.healthcheck
    Assert-ExitCode 'Current bot healthcheck'

    # Online SQLite backup from the currently deployed image before any code switch.
    # Host directory is outside the Compose named volume and the Git checkout.
    New-Item -ItemType Directory -Force -Path $BackupDirectory | Out-Null
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $suffix = [guid]::NewGuid().ToString('N').Substring(0, 8)
    $snapshot = "places-$stamp-$suffix.db"
    & docker compose run --rm --no-deps -v "${BackupDirectory}:/backups" bot `
        python -m app.database_backup /app/data/places.db "/backups/$snapshot"
    Assert-ExitCode 'SQLite online backup'
    $backupFile = Join-Path $BackupDirectory $snapshot
    if (-not (Test-Path -LiteralPath $backupFile -PathType Leaf)) {
        throw 'SQLite backup not found on the host.'
    }
    if ((Get-Item -LiteralPath $backupFile).Length -le 0) {
        throw 'SQLite backup is empty.'
    }
    Write-Host "Backup retained: $backupFile"

    # Building and preflight never start another Telegram polling process.
    & git switch --detach $ApprovedSha
    Assert-ExitCode 'Switch to approved release'
    & docker compose build --build-arg "PLACES_BUILD_SHA=$ApprovedSha" bot web
    Assert-ExitCode 'Build approved image'
    & docker compose run --rm --no-deps -v "${BackupDirectory}:/backups:ro" bot `
        python -m app.local_deployment_preflight --backup "/backups/$snapshot" `
        --expected-sha $ApprovedSha --max-age-hours 24
    Assert-ExitCode 'Development release preflight'

    # No volume deletion, manual WAL modifications, or speculative DB rollback.
    & docker compose up -d --no-deps --no-build bot web
    Assert-ExitCode 'Start approved image'
    $healthy = $false
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        & docker compose exec -T bot python -m app.healthcheck
        if ($LASTEXITCODE -eq 0) {
            $healthy = $true
            break
        }
        Start-Sleep -Seconds 3
    }
    if (-not $healthy) {
        throw 'Updated bot healthcheck failed. Inspect logs; do not restore DB while running.'
    }
    $diagnostics = @(& docker compose exec -T bot python -m app.diagnostics)
    Assert-ExitCode 'Updated bot diagnostics'
    $status = ($diagnostics -join "`n") | ConvertFrom-Json
    if ($status.status -ne 'healthy' -or $status.build_sha -ne $ApprovedSha) {
        throw 'Updated container does not report the approved healthy build SHA.'
    }
    $webHealthy = $false
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        & docker compose exec -T web python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8080/healthz", timeout=3).read().decode())'
        if ($LASTEXITCODE -eq 0) {
            $webHealthy = $true
            break
        }
        Start-Sleep -Seconds 3
    }
    if (-not $webHealthy) {
        throw 'Mini App web API did not become healthy. Inspect Docker logs.'
    }
    & docker compose ps
    Assert-ExitCode 'Inspect updated bot and Mini App'
    Write-Host "Local Docker update verified: $ApprovedSha"
    Write-Host "Backup retained: $backupFile"
    Write-Host 'Check Telegram /start, /city, and a saved route manually.'
}
finally {
    Pop-Location
}
