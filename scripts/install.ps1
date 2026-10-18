#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Installs windows-mcp (Windows Control via MCP over Cloudflare Tunnel).
.DESCRIPTION
  1. Installs Python (if missing)
  2. Installs cloudflared (if missing)
  3. Creates Python venv in %USERPROFILE%\windows-mcp
  4. Installs Python dependencies
  5. Creates desktop/start-menu shortcuts
  6. Generates a start script for the MCP server + Cloudflare tunnel
#>

$ErrorActionPreference = "Stop"
$InstallDir = "$env:USERPROFILE\windows-mcp"
$VenvDir = "$InstallDir\.venv"
$RepoDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  Windows MCP - KI-Agent Fernsteuerung" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Python check ---
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[1/6] Python nicht gefunden, installiere via winget ..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements | Out-Null
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "[1/6] Python gefunden: $(python --version)" -ForegroundColor Green
}

# --- 2. cloudflared check ---
$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cf) {
    Write-Host "[2/6] cloudflared nicht gefunden, installiere ..." -ForegroundColor Yellow
    winget install -e --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements | Out-Null
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "[2/6] cloudflared gefunden: $(cloudflared --version)" -ForegroundColor Green
}

# --- 3. Copy project files ---
Write-Host "[3/6] Kopiere nach $InstallDir ..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Path "$RepoDir\windows_mcp" -Destination "$InstallDir\" -Recurse -Force
Copy-Item -Path "$RepoDir\requirements.txt" -Destination "$InstallDir\" -Force
Copy-Item -Path "$RepoDir\scripts\start-mcp.ps1" -Destination "$InstallDir\" -Force
Copy-Item -Path "$RepoDir\scripts\start-mcp.bat" -Destination "$InstallDir\" -Force
Copy-Item -Path "$RepoDir\README.md" -Destination "$InstallDir\" -Force

# --- 4. Python venv & deps ---
Write-Host "[4/6] Erstelle Python venv und installiere Abhaengigkeiten ..." -ForegroundColor Yellow
if (-not (Test-Path "$VenvDir\Scripts\python.exe")) {
    python -m venv $VenvDir
}
& "$VenvDir\Scripts\python.exe" -m pip install --upgrade pip | Out-Null
& "$VenvDir\Scripts\pip.exe" install -r "$InstallDir\requirements.txt"
& "$VenvDir\Scripts\pip.exe" install "uvicorn>=0.27" "starlette>=0.37" "mcp[cli]>=1.0.0"

# --- 5. Desktop shortcut ---
Write-Host "[5/6] Erstelle Desktop-Verknuepfung ..." -ForegroundColor Yellow
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Windows MCP - Start.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -NoExit -File `"$InstallDir\start-mcp.ps1`""
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "Windows MCP Server mit Cloudflare Tunnel starten"
$Shortcut.Save()

# --- 6. Finish ---
Write-Host "[6/6] Fertig!" -ForegroundColor Green
Write-Host ""
Write-Host "Starte den Server ueber die Desktop-Verknuepfung, oder:" -ForegroundColor White
Write-Host "   powershell -ExecutionPolicy Bypass -File `"$InstallDir\start-mcp.ps1`"" -ForegroundColor Gray
Write-Host ""
Write-Host "Nach dem Start zeigt dir die Konsole deine Cloudflare-URL an," -ForegroundColor White
Write-Host "z.B. https://xxxx-xxxx.trycloudflare.com" -ForegroundColor White
Write-Host "Der MCP-Endpunkt ist dann:  <URL>/mcp/sse" -ForegroundColor White
Write-Host ""
