param([switch]$Fullscreen,[string]$Start='index.html')
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($Start -notmatch '^[A-Za-z0-9_-]+\.html$') { $Start = 'index.html' }
$Index = Join-Path $Root $Start
$LogRoot = Join-Path $env:LOCALAPPDATA 'DF-VM-Technical-Institute\logs'
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$Log = Join-Path $LogRoot ('launch-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.log')
function Write-Log([string]$Message) { Add-Content -LiteralPath $Log -Value ((Get-Date -Format o) + ' ' + $Message) -Encoding UTF8 }
function Show-Failure([string]$Message) {
    Write-Log ('ERROR ' + $Message)
    try {
        $ws = New-Object -ComObject WScript.Shell
        [void]$ws.Popup($Message + "`r`n`r`nDiagnostic log:`r`n" + $Log, 0, 'DF VM Technical Institute - Launch Error', 16)
    } catch { Write-Host $Message }
}
try {
    Write-Log ('Launcher root: ' + $Root)
    if (-not (Test-Path -LiteralPath $Index -PathType Leaf)) { throw "index.html not found at $Index" }
    foreach ($required in @('assets\styles.css','assets\data.js','assets\site.js')) {
        $p = Join-Path $Root $required
        if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Required asset missing: $p" }
    }
    $uri = ([System.Uri]$Index).AbsoluteUri
    Write-Log ('Index URI: ' + $uri)

    # IMPORTANT: force an array. A single pipeline result must never become a scalar string
    # whose [0] index is only the first character of the path.
    $pf86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
    $pf64 = [Environment]::GetEnvironmentVariable('ProgramFiles')
    $local = [Environment]::GetEnvironmentVariable('LOCALAPPDATA')
    $known = @(
        $(if ($pf86) { Join-Path $pf86 'Microsoft\Edge\Application\msedge.exe' }),
        $(if ($pf64) { Join-Path $pf64 'Microsoft\Edge\Application\msedge.exe' }),
        $(if ($local) { Join-Path $local 'Microsoft\Edge\Application\msedge.exe' }),
        $(if ($pf64) { Join-Path $pf64 'Google\Chrome\Application\chrome.exe' }),
        $(if ($pf86) { Join-Path $pf86 'Google\Chrome\Application\chrome.exe' }),
        $(if ($local) { Join-Path $local 'Google\Chrome\Application\chrome.exe' })
    ) | Where-Object { $_ }
    $discovered = New-Object System.Collections.Generic.List[string]
    foreach ($p in $known) { if ($p -and (Test-Path -LiteralPath $p -PathType Leaf)) { [void]$discovered.Add($p) } }
    foreach ($name in @('msedge.exe','chrome.exe')) {
        try {
            $cmd = Get-Command $name -ErrorAction Stop
            if ($cmd.Source -and (Test-Path -LiteralPath $cmd.Source)) { [void]$discovered.Add([string]$cmd.Source) }
        } catch {}
    }
    $candidates = @($discovered | Select-Object -Unique)
    Write-Log ('Browser candidates: ' + ($candidates -join ' | '))

    if ($candidates.Count -gt 0) {
        $browser = [string]$candidates[0]
        $args = @("--app=$uri", '--no-first-run', '--no-default-browser-check', '--disable-extensions')
        if ($Fullscreen) { $args += '--start-fullscreen' } else { $args += '--start-maximized' }
        Write-Log ('Starting browser: ' + $browser + ' ' + ($args -join ' '))
        Start-Process -FilePath $browser -ArgumentList $args | Out-Null
    } else {
        Write-Log 'No Edge/Chrome candidate found; using Windows file association fallback.'
        Start-Process -FilePath $Index | Out-Null
    }
    Write-Log 'Launch request completed.'
    exit 0
} catch {
    Show-Failure $_.Exception.Message
    exit 1
}
