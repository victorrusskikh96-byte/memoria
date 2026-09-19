[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget was not found. Install or update Microsoft App Installer first."
}

winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
winget install --id astral-sh.uv -e --source winget --accept-package-agreements --accept-source-agreements

Write-Output "Git and uv are installed. Open a new PowerShell window, then run: uv python install 3.13"
Write-Output "WSL and Docker Desktop require an explicit OS-level setup; follow the engineering guide."
