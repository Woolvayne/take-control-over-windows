<#
.SYNOPSIS
  Starts the Windows MCP server (HTTP/SSE) on port 8787 and pipes it through
  a free Cloudflare Quick Tunnel so AI agents can reach it from the internet.
.DESCRIPTION
  - Starts the MCP HTTP server in the background
  - Starts `cloudflared tunnel --url http://localhost:8787`
  - Parses the generated *.trycloudflare.com URL
  - Sets MCP_TUNNEL_URL env var and prints the /mcp/sse endpoint
#>

$ErrorActionPreference = "Continue"
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = "$InstallDir\.venv\Scripts\python.exe"
$Port = 8787

if (-not (Test-Path $VenvPython)) {
    # Fall back to system python when not installed via install.ps1 (dev mode)
    $VenvPython = "python"
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  Windows MCP Server" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# Kill anything that still holds port 8787 (prevents "address in use")
Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | ForEach-Object {
    try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
}

# 1. Start MCP server (background)
$serverLog = "$env:TEMP\windows-mcp-server.log"
Write-Host "[1] Starte MCP HTTP/SSE Server auf Port $Port ..." -ForegroundColor Yellow
$serverProc = Start-Process -FilePath $VenvPython `
    -ArgumentList "-m", "windows_mcp", "serve", "--port", "$Port" `
    -WorkingDirectory $InstallDir `
    -RedirectStandardOutput $serverLog `
    -RedirectStandardError "$env:TEMP\windows-mcp-server.err" `
    -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 3

# 2. Start cloudflared quick tunnel and parse the URL
$cfLog = "$env:TEMP\cloudflared.log"
Write-Host "[2] Starte Cloudflare Quick Tunnel (cloudflared tunnel --url http://localhost:$Port) ..." -ForegroundColor Yellow
$cfProc = Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://localhost:$Port", "--no-autoupdate", "--logfile", $cfLog `
    -PassThru -WindowStyle Hidden -NoNewWindow:$false

# Wait for tunnel URL to appear
$tunnelUrl = $null
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-Path $cfLog) {
        $matches = Select-String -Path $cfLog -Pattern "https://[a-zA-Z0-9\-]+\.trycloudflare\.com" -AllMatches -ErrorAction SilentlyContinue
        if ($matches) {
            $tunnelUrl = $matches.Matches[-1].Value
            break
        }
    }
}

if (-not $tunnelUrl) {
    # fallback: parse stdout if logfile empty
    Start-Sleep -Seconds 5
    if (Test-Path $cfLog) {
        $m2 = Select-String -Path $cfLog -Pattern "https://[a-zA-Z0-9\-]+\.trycloudflare\.com" -AllMatches -ErrorAction SilentlyContinue
        if ($m2) { $tunnelUrl = $m2.Matches[-1].Value }
    }
}

# 3. Set env var and restart server with tunnel URL so screenshots get public URLs
if ($tunnelUrl) {
    $env:MCP_TUNNEL_URL = $tunnelUrl
    # Restart server with tunnel env so public_url in screenshots is correct
    Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    $serverProc = Start-Process -FilePath $VenvPython `
        -ArgumentList "-m", "windows_mcp", "serve", "--port", "$Port" `
        -WorkingDirectory $InstallDir `
        -RedirectStandardOutput $serverLog `
        -RedirectStandardError "$env:TEMP\windows-mcp-server.err" `
        -PassThru -WindowStyle Hidden -NoNewWindow:$false `
        -Environment @{ MCP_TUNNEL_URL = $tunnelUrl }
    Start-Sleep -Seconds 2
}

# 4. Print info
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  SERVER LÄUFT!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
if ($tunnelUrl) {
    Write-Host ""
    Write-Host " Cloudflare-Tunnel-URL : $tunnelUrl" -ForegroundColor White
    Write-Host " MCP-Endpunkt (SSE)    : $tunnelUrl/mcp/sse" -ForegroundColor White
    Write-Host " Screenshots (public)  : $tunnelUrl/files/" -ForegroundColor White
    Write-Host " Health-Check          : $tunnelUrl/health" -ForegroundColor Gray
    Write-Host ""
    Write-Host " Gib diese MCP-URL in deinen KI-Client ein" -ForegroundColor Cyan
    Write-Host " (z.B. in deinem Agenten als Remote-MCP)." -ForegroundColor Cyan
    Write-Host ""
    # Copy to clipboard
    try { Set-Clipboard -Value "$tunnelUrl/mcp/sse" ; Write-Host " (MCP-URL wurde in die Zwischenablage kopiert)" -ForegroundColor Gray } catch {}
} else {
    Write-Host "WARNUNG: Cloudflare-URL konnte nicht erkannt werden. Siehe $cfLog" -ForegroundColor Red
    Write-Host "Lokal erreichbar unter: http://localhost:$Port/mcp/sse" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Server-Log: $serverLog" -ForegroundColor Gray
Write-Host "Cloudflared-Log: $cfLog" -ForegroundColor Gray
Write-Host ""
Write-Host "Druecke STRG+C zum Beenden, oder schliesse dieses Fenster." -ForegroundColor Yellow

# Keep window alive, monitor processes
try {
    while ($true) {
        if ($serverProc.HasExited -or $cfProc.HasExited) {
            Write-Host "Ein Prozess wurde beendet. Schliesse ab..." -ForegroundColor Red
            break
        }
        Start-Sleep -Seconds 2
    }
} finally {
    if (-not $serverProc.HasExited) { Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue }
    if (-not $cfProc.HasExited) { Stop-Process -Id $cfProc.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "Alle Prozesse beendet." -ForegroundColor Green
}
