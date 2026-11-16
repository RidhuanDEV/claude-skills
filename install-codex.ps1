# Install live links for all Shadow Army skills into Codex (PowerShell 5.1+).
[CmdletBinding()]
param(
    [string]$SkillsDirectory = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.agents\skills')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$skillsRoot = [System.IO.Path]::GetFullPath($SkillsDirectory)
$skillDirs = Get-ChildItem -LiteralPath $PSScriptRoot -Directory | Where-Object {
    Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') -PathType Leaf
} | Sort-Object Name

if ($skillDirs.Count -eq 0) {
    throw "No skill directories containing SKILL.md found under $PSScriptRoot."
}

New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null

$linkedCount = 0
$alreadyCount = 0

foreach ($dir in $skillDirs) {
    $skillSource = $dir.FullName
    $skillTarget = Join-Path $skillsRoot $dir.Name

    if ($skillTarget.TrimEnd('\') -eq $skillSource.TrimEnd('\')) {
        throw "Installation target must differ from the source folder: $skillSource"
    }

    $existingSkill = Get-Item -LiteralPath $skillTarget -Force -ErrorAction SilentlyContinue
    if ($null -ne $existingSkill) {
        if (($existingSkill.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            $existingTargets = @($existingSkill.Target)
            if ($existingTargets.Count -eq 1 -and
                [System.IO.Path]::GetFullPath([string]$existingTargets[0]).TrimEnd('\') -eq $skillSource.TrimEnd('\')) {
                $alreadyCount++
                continue
            }
        }
        throw "Target already exists and was preserved: $skillTarget. Choose another SkillsDirectory or inspect it before replacing it."
    }

    New-Item -ItemType Junction -Path $skillTarget -Target $skillSource | Out-Null
    $linkedCount++
    Write-Output "Installed: $skillTarget -> $skillSource"
}

Write-Output "Done. Codex skills synced ($($skillDirs.Count) total: $linkedCount newly linked, $alreadyCount already linked) at $skillsRoot."
Write-Output 'Invoke with $shadow-monarch or any companion skill. If skills do not appear, restart Codex.'
