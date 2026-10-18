# Install a live link to the local Shadow Monarch source for Codex (PowerShell 5.1+).
[CmdletBinding()]
param(
    [string]$SkillsDirectory = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.agents\skills')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$skillSource = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'shadow-monarch')).ProviderPath
$skillsRoot = [System.IO.Path]::GetFullPath($SkillsDirectory)
$skillTarget = Join-Path $skillsRoot 'shadow-monarch'

if (-not (Test-Path -LiteralPath (Join-Path $skillSource 'SKILL.md') -PathType Leaf)) {
    throw "SKILL.md not found in $skillSource."
}
if ($skillTarget.TrimEnd('\') -eq $skillSource.TrimEnd('\')) {
    throw 'Installation target must differ from the source folder.'
}

$existingSkill = Get-Item -LiteralPath $skillTarget -Force -ErrorAction SilentlyContinue
if ($null -ne $existingSkill) {
    if (($existingSkill.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        $existingTargets = @($existingSkill.Target)
        if ($existingTargets.Count -eq 1 -and
            [System.IO.Path]::GetFullPath([string]$existingTargets[0]).TrimEnd('\') -eq $skillSource.TrimEnd('\')) {
            Write-Output "Already installed: $skillTarget -> $skillSource"
            return
        }
    }
    throw "Target already exists and was preserved: $skillTarget. Choose another SkillsDirectory or inspect it before replacing it."
}

New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
New-Item -ItemType Junction -Path $skillTarget -Target $skillSource | Out-Null
Write-Output "Installed: $skillTarget -> $skillSource"
Write-Output 'Invoke with $shadow-monarch. If the skill does not appear, restart Codex.'
