# Installs the full 36-skill Shadow Army suite (shadow-monarch + companion /shadow-* skills)
# and updates %USERPROFILE%\.claude\CLAUDE.md between markers.
# Run with: powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'

$Source    = Join-Path $PSScriptRoot 'shadow-monarch'
$ClaudeDir = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME '.claude' }
$ClaudeMd  = Join-Path $ClaudeDir 'CLAUDE.md'
$Begin     = '<!-- BEGIN shadow-monarch -->'
$End       = '<!-- END shadow-monarch -->'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path (Join-Path $Source 'SKILL.md'))) {
    throw "SKILL.md not found in $Source. Run this script from the repo root."
}

$SkillFolders = @(
    'shadow-monarch',
    'shadow-discovery',
    'shadow-architect',
    'shadow-plan',
    'shadow-bootstrap',
    'shadow-design',
    'shadow-auth',
    'shadow-data',
    'shadow-db',
    'shadow-api',
    'shadow-cache',
    'shadow-integrate',
    'shadow-accessibility',
    'shadow-quality',
    'shadow-test',
    'shadow-sec',
    'shadow-perf',
    'shadow-uat',
    'shadow-release',
    'shadow-compat',
    'shadow-browser',
    'shadow-ops',
    'shadow-observe',
    'shadow-resilience',
    'shadow-maintain',
    'shadow-handover',
    'shadow-doc',
    'shadow-git',
    'handoff',
    'context7',
    'antislop',
    'antislop-ui',
    'antislop-layoutmobile',
    'antislop-human',
    'antislop-copywriting',
    'antislop-code'
)

$TargetRoots = @(
    (Join-Path $HOME '.gemini\config\skills'),
    (Join-Path $HOME '.gemini\skills'),
    (Join-Path $ClaudeDir 'skills'),
    (Join-Path $HOME '.agents\skills'),
    (Join-Path $HOME '.codex\skills')
)

foreach ($Root in $TargetRoots) {
    New-Item -ItemType Directory -Force -Path $Root | Out-Null
    foreach ($Folder in $SkillFolders) {
        $SrcPath = Join-Path $PSScriptRoot $Folder
        if (Test-Path (Join-Path $SrcPath 'SKILL.md')) {
            $DstPath = Join-Path $Root $Folder
            if (Test-Path $DstPath) { Remove-Item -Recurse -Force $DstPath }
            Copy-Item -Recurse -Force -Path $SrcPath -Destination $DstPath
        }
    }
    Write-Host "Synced $($SkillFolders.Count) Shadow Army skills to: $Root"
}

$global = [System.IO.File]::ReadAllText((Join-Path $Source 'GLOBAL.md'), $Utf8NoBom).TrimEnd()
$block  = "$Begin`n$global`n$End"
$CodexDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$GeminiDir = Join-Path $HOME '.gemini'

$GlobalInstructionFiles = @(
    $ClaudeMd,
    (Join-Path $CodexDir 'AGENTS.md'),
    (Join-Path $GeminiDir 'GEMINI.md')
)

foreach ($InstructionFile in $GlobalInstructionFiles) {
    $ParentDir = Split-Path -Parent $InstructionFile
    if (-not (Test-Path $ParentDir)) {
        New-Item -ItemType Directory -Force -Path $ParentDir | Out-Null
    }
    if (Test-Path $InstructionFile) {
        $stamp = Get-Date -Format 'yyyyMMddHHmmss'
        Copy-Item $InstructionFile "$InstructionFile.bak.$stamp"
        $current = [System.IO.File]::ReadAllText($InstructionFile, $Utf8NoBom)
        $pattern = [regex]::Escape($Begin) + '[\s\S]*?' + [regex]::Escape($End)
        if ($current -match $pattern) {
            $updated = [regex]::Replace($current, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $block })
            Write-Host "Updated shadow-monarch block in $InstructionFile (backup saved)"
        } else {
            $updated = $current.TrimEnd() + "`n`n" + $block + "`n"
            Write-Host "Appended shadow-monarch block to $InstructionFile (backup saved)"
        }
        [System.IO.File]::WriteAllText($InstructionFile, $updated, $Utf8NoBom)
    } else {
        [System.IO.File]::WriteAllText($InstructionFile, $block + "`n", $Utf8NoBom)
        Write-Host "Created $InstructionFile"
    }
}

Write-Host 'Done. All 36 Shadow Army skills and global instruction files (CLAUDE.md, AGENTS.md, GEMINI.md) are synced across Antigravity, Gemini CLI, Claude Code, and Codex.'
