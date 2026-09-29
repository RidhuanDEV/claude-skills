# Installs the shadow-monarch skill for Claude Code (Windows PowerShell 5.1+ / PowerShell 7+).
# - Copies .\shadow-monarch to %USERPROFILE%\.claude\skills\shadow-monarch (replacing an older copy)
# - Inserts GLOBAL.md into %USERPROFILE%\.claude\CLAUDE.md between markers (backs up the old file first)
# If script execution is blocked, run:  powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'

$Source   = Join-Path $PSScriptRoot 'shadow-monarch'
$ClaudeDir = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME '.claude' }
$Target   = Join-Path $ClaudeDir 'skills\shadow-monarch'
$ClaudeMd = Join-Path $ClaudeDir 'CLAUDE.md'
$Begin    = '<!-- BEGIN shadow-monarch -->'
$End      = '<!-- END shadow-monarch -->'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path (Join-Path $Source 'SKILL.md'))) {
    throw "SKILL.md not found in $Source. Run this script from the repo root."
}

New-Item -ItemType Directory -Force -Path (Join-Path $ClaudeDir 'skills') | Out-Null
if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
Copy-Item -Recurse -Path $Source -Destination $Target
Write-Host "Skill installed: $Target"

$global = [System.IO.File]::ReadAllText((Join-Path $Source 'GLOBAL.md'), $Utf8NoBom).TrimEnd()
$block  = "$Begin`n$global`n$End"

if (Test-Path $ClaudeMd) {
    $stamp = Get-Date -Format 'yyyyMMddHHmmss'
    Copy-Item $ClaudeMd "$ClaudeMd.bak.$stamp"
    $current = [System.IO.File]::ReadAllText($ClaudeMd, $Utf8NoBom)
    $pattern = [regex]::Escape($Begin) + '[\s\S]*?' + [regex]::Escape($End)
    if ($current -match $pattern) {
        $updated = [regex]::Replace($current, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $block })
        Write-Host "Updated shadow-monarch block in $ClaudeMd (backup saved)"
    } else {
        $updated = $current.TrimEnd() + "`n`n" + $block + "`n"
        Write-Host "Appended shadow-monarch block to $ClaudeMd (backup saved)"
    }
    [System.IO.File]::WriteAllText($ClaudeMd, $updated, $Utf8NoBom)
} else {
    [System.IO.File]::WriteAllText($ClaudeMd, $block + "`n", $Utf8NoBom)
    Write-Host "Created $ClaudeMd"
}

Write-Host 'Done. Restart Claude Code to pick up the changes.'
