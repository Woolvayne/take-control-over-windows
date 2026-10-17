# Uninstall windows-mcp
$InstallDir = "$env:USERPROFILE\windows-mcp"
$DesktopShortcut = "$env:USERPROFILE\Desktop\Windows MCP - Start.lnk"

Write-Host "Entferne Windows MCP..." -ForegroundColor Yellow
if (Test-Path $DesktopShortcut) { Remove-Item $DesktopShortcut -Force }
if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
Write-Host "Fertig. Python und cloudflared bleiben installiert." -ForegroundColor Green
