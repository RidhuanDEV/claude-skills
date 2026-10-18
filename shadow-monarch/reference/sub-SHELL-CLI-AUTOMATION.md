# sub-SHELL-CLI-AUTOMATION — Authoring Rules for PowerShell (`.ps1`), Bash (`.sh`) & Taskfiles

Use when writing automation scripts, build/deploy helpers, system administration scripts, or developer task runners
in PowerShell (Windows/cross-platform `pwsh`), Bash/POSIX shell (Linux/macOS/containers), or `Makefile`/`Taskfile`/`Justfile`.

## 1. PowerShell (`.ps1`) authoring rules

Every non-trivial PowerShell script must begin with strict safety headers and typed parameters:
```powershell
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Environment,

    [Parameter(Mandatory = $false)]
    [string]$OutputDir = (Join-Path $PSScriptRoot "dist")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true # PowerShell 7.3+
```
- **Native command exit codes**: in PowerShell 5.1 (or when `$PSNativeCommandUseErrorActionPreference` is unavailable),
  external CLI failures (`tsc`, `docker`, `python`) do NOT trigger `try/catch` automatically — always check
  `if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" }`.
- **Path & encoding safety**:
  - Always use `Join-Path` and `$PSScriptRoot` instead of string concatenation with `\` or relative `./` paths that break
    when called from another working directory.
  - Specify `-Encoding utf8` (or `utf8NoBOM` in `pwsh`) explicitly on `Out-File`, `Set-Content`, and `Get-Content`
    (Windows PowerShell 5.1 defaults to UTF-16LE / ANSI, which corrupts JSON and source files).
- **Pipeline & return hygiene**: PowerShell functions return **every uncaptured expression** written to the output stream.
  Assign noisy command outputs to `$null = ...` or `[void](...)` and use `Write-Host` / `Write-Information` / `Write-Verbose`
  for human logs so function return values are never polluted.

## 2. Bash / POSIX Shell (`.sh`) authoring rules

Every Bash script must start with the strict mode preamble and a cleanup trap:
```bash
#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

cleanup() {
  local exit_code=$?
  # Remove temp files or restore state here
  exit "$exit_code"
}
trap cleanup EXIT INT TERM
```
- **Quoting & arrays**:
  - **Always double-quote variable expansions**: `"$file_path"`, `"${args[@]}"`. Unquoted `$var` breaks on filenames with spaces and triggers glob expansion.
  - Resolve script directory safely: `SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"`.
- **Safe temporary files**: create temp files/dirs with `tmp_file="$(mktemp)"` and delete them inside the `cleanup` trap.
- **When to stop writing Bash**: if a script requires nested data structures (JSON maps), complex math, HTTP retries, or
  exceeds ~100 lines of logic, write it in **Python** or **Node/TypeScript** instead of fragile Bash string manipulation.
- Validate scripts against **`shellcheck`** rules.

## 3. `Makefile`, `Taskfile.yml` & `Justfile` authoring rules

- Provide a self-documenting `help` (default) target and standardized lifecycle targets:
  `setup` / `install`, `dev`, `lint`, `typecheck`, `test`, `build`, `clean`.
- In `Makefile`:
  - Declare `.PHONY: help install dev lint typecheck test build clean` so targets never collide with filenames.
  - Set `SHELL := /usr/bin/env bash` and `.SHELLFLAGS := -eu -o pipefail -c` when recipes use Bash features.
- Ensure cross-platform developer experience: if the team works on Windows without WSL/Make, provide equivalent `package.json`
  scripts, `Taskfile.yml` (`go-task`), or a `.ps1` wrapper.
