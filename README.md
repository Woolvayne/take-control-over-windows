# 🖥️ Windows MCP – Dein PC für KI-Agenten über Cloudflare Tunnel

> Mach deinen Windows-PC von überall aus für KI-Agenten (Claude, GPT, Open Interpreter,
> eigene Agents …) steuerbar – Maus, Tastatur, Screenshots, Dateien, Shell, Prozesse,
> Fenster und mehr – erreichbar über einen **kostenlosen Cloudflare Quick-Tunnel**
> unter deiner eigenen `*.trycloudflare.com/MCP` URL.

---

## ✨ Features

Der MCP-Server (**M**odel **C**ontext **P**rotocol) gibt KI-Agenten folgende Werkzeuge:

| Kategorie     | Funktionen                                                                                             |
|---------------|--------------------------------------------------------------------------------------------------------|
| 👁️ Bildschirm   | Screenshot als Datei oder direkt als Base64 (Inline im Chat), Screenshot-Verlauf, Bildschirmgröße       |
| 🖱️ Maus         | bewegen, klicken, doppel-/rechtsklick, ziehen, scrollen                                                |
| ⌨️ Tastatur     | Text tippen, Einzel-Tasten, Hotkeys (z.B. `Strg+C`, `Win+D`), KeyDown/KeyUp                            |
| 📋 Zwischenablage | Lesen & schreiben                                                                                     |
| 🪟 Fenster      | Fenster auflisten, fokussieren, minimieren, schließen (nach Titel-Suche)                               |
| ⚙️ System       | System-Info (CPU/RAM/Disk/Uptime), Batteriestatus, Prozess-Liste, Prozesse killen                      |
| 💻 Shell        | Beliebige CMD/PowerShell-Kommandos ausführen (mit Timeout), Dateien lesen & schreiben, Ordner listen   |
| 🔊 Extra       | Message-Boxen, TTS (Text-to-Speech), Browser-URL öffnen, Warte-Befehle                                 |

Screenshots werden automatisch in ein `public/` Verzeichnis gespeichert und sind über
den Cloudflare-Tunnel unter `https://<deine-tunnel-url>/files/...` erreichbar – so kann
der Agent sie direkt im Chat anzeigen oder an Onlyfiles/andere Filesharing-Dienste
schicken.

---

## 🚀 Schnellstart (Installation über Terminal)

### 1. Projekt klonen oder downloaden

```powershell
git clone https://github.com/Woolvayne/take-control-over-windows.git
cd take-control-over-windows
```

### 2. Installieren (einmalig)

Rechtsklick auf PowerShell → **"Als Administrator ausführen"**, dann:

```powershell
cd <pfad-zum-repo>
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

Das Skript erledigt automatisch:
- ✅ Python (3.12) installieren, falls nicht vorhanden (via `winget`)
- ✅ `cloudflared` installieren, falls nicht vorhanden (via `winget`)
- ✅ Virtuelles Python-Environment in `%USERPROFILE%\windows-mcp\.venv`
- ✅ Abhängigkeiten installieren (`pyautogui`, `Pillow`, `psutil`, `mcp`, `uvicorn` …)
- ✅ Desktop-Verknüpfung **"Windows MCP – Start"** anlegen

### 3. Starten

Doppelklick auf die Desktop-Verknüpfung, oder:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\windows-mcp\start-mcp.ps1"
```

Die Konsole zeigt dir nach ein paar Sekunden deine **Cloudflare-URL** an, z.B.:

```
Cloudflare-Tunnel-URL : https://helpful-tiger-guides-example.trycloudflare.com
MCP-Endpunkt (SSE)    : https://helpful-tiger-guides-example.trycloudflare.com/mcp/sse
Screenshots (public)  : https://helpful-tiger-guides-example.trycloudflare.com/files/
```

👉 Die MCP-URL wird **automatisch in die Zwischenablage kopiert** – du kannst sie
sofort in deinen KI-Client einfügen.

### 4. Mit einem KI-Agenten verbinden

Füge den Server in deinem MCP-Client als **Remote-SSE-Server** hinzu:
- URL: `https://<deine-subdomain>.trycloudflare.com/mcp/sse`
- Transport: `SSE (HTTP)`

Beispiel-Client-Konfigurationen (JSON) findest du in [`examples/`](examples/).

---

## 🔌 Lokaler STDIO-Modus (ohne Cloudflare)

Wenn du den Agenten lokal (z.B. in Claude Desktop) nutzen willst – ohne Internet –
einfach das Python-Modul direkt aufrufen:

```powershell
cd $env:USERPROFILE\windows-mcp
.\.venv\Scripts\python.exe -m windows_mcp
```

In `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "windows-control": {
      "command": "C:\\Users\\<DU>\\windows-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "windows_mcp"]
    }
  }
}
```

---

## 📁 Projekt-Struktur

```
take-control-over-windows/
├── windows_mcp/
│   ├── __init__.py
│   ├── __main__.py         # python -m windows_mcp
│   └── server.py           # Alle MCP-Tools (Maus, Tastatur, Screenshot, …)
├── scripts/
│   ├── install.ps1         # Ein-Klick-Installation
│   ├── start-mcp.ps1       # Startet Server + Cloudflare-Tunnel
│   ├── start-mcp.bat       # Doppelklick-Start
│   └── uninstall.ps1       # Deinstallation
├── examples/
│   └── claude_desktop_config.json
├── screenshots/            # (wird zur Laufzeit benutzt)
├── requirements.txt
└── README.md
```

---

## 💡 Eigene Ideen / Erweiterungen (schon eingebaut & Roadmap)

Was ich zusätzlich eingebaut und/oder als Ausblick vorgesehen habe:

- ✅ **Screenshot-Public-URL**: Jeder Screenshot bekommt automatisch eine öffentliche
  Cloudflare-URL, die der Agent direkt in den Chat einbetten kann.
- ✅ **Base64-Inline-Screenshots**: Für Clients die keine externen URLs laden, gibt es
  `screenshot_base64` – Bild kommt direkt als Data-URI.
- ✅ **Fail-Safe**: `pyautogui.FAILSAFE = True` – wenn du die Maus in die obere-linke
  Ecke (0,0) ziehst, bricht jede laufende Aktion sofort ab. **Sicherheit zuerst!**
- ✅ **Health-Endpoint**: `/health` zeigt Status + Tunnel-URL – einfach zum Testen im Browser.
- ✅ **TTS & Message-Boxen**: Der Agent kann dich nicht nur schriftlich, sondern per
  Sprachausgabe oder Popup benachrichtigen.
- ✅ **Hotkey-Support**: Win+D (Desktop), Alt+Tab, Strg+Shift+Esc – alle Kombos gehen.
- ✅ **Zwischenablage-Brücke**: Agent kopiert etwas und du siehst es sofort in Windows.

### 🗺️ Roadmap-Ideen (kann ich gern bauen)

- 🔜 **Onlyfiles/File.io Upload-Tool**: Screenshots automatisch auf Filehoster laden,
      damit der Agent sie auch bei Clients einbetten kann, die Fremd-URLs blockieren.
- 🔜 **Datei-Drag&Drop-Simulation**: `pyautogui` kann Dateien per Drag&Drop verschieben.
- 🔜 **Webcam-Snapshot**: Ein `take_webcam_photo`-Tool für das Bild nach vorne.
- 🔜 **Audio-Mikrofon-Aufnahme**: Agent kann zuhören + Sprache-zu-Text.
- 🔜 **Vision-Rückkanal mit GPT-4-Vision/Claude-Vision**: Screenshots automatisch
      untersuchen lassen ("was ist auf dem Bildschirm zu sehen?").
- 🔜 **Auth-Token für den Tunnel**: Aktuell ist der Tunnel öffentlich. Ein einfacher
      API-Key-Header schützt vor Fremdzugriff.
- 🔜 **Windows-System-Tray-Icon**: Start/Stop per Rechtsklick-Menü neben der Uhr.
- 🔜 **Aufgaben-Planer / Cron**: Agent kann zeitgesteuerte Aktionen hinterlegen.
- 🔜 **Zwischenablage-Bilder direkt als MCP-Resource**: Wenn du etwas Screenshots in
      die Zwischenablage machst, erkennt es der Server automatisch.
- 🔜 **Multi-Monitor-Screenshot** (schon aktiv dank `all_screens=True`, aber noch
      pro-Monitor-Auswahl-UI).

> 💬 Sag mir, welche dieser Erweiterungen du zuerst haben willst – oder schick mir
> deine eigenen Ideen!

---

## 🔒 Sicherheitshinweise

- **Cloudflare Quick-Tunnel** sind **öffentlich!** Jeder, der die URL erraten könnte
  (die Subdomain ist zufällig und ändert sich bei jedem Neustart), kann deinen PC
  steuern. Benutze es nur in vertrauenswürdigen Umgebungen oder füge einen Auth-Token
  hinzu (siehe Roadmap).
- **Failsafe**: Maus sofort in die linke obere Ecke ziehen → jede PyAutoGUI-Aktion
  stoppt mit einer `pyautogui.FailSafeException`.
- Das Start-Skript läuft nicht als Windows-Dienst – es stoppt wenn du das Fenster
  schließt oder `Strg+C` drückst.
- Shell-Kommandos laufen unter deinem Benutzer – der Agent hat also dieselben Rechte
  wie du. Das ist gewollt ("der Agent soll alles können was der User kann"), aber
  **sei vorsichtig** mit welchen Anweisungen du ihn betraust.

---

## ❓ FAQ / Troubleshooting

**Q: `cloudflared` wird nicht gefunden?**
Starte PowerShell nach der Installation neu, damit der PATH neu geladen wird.

**Q: Maus bewegt sich, aber Klicks gehen nicht?**
Stelle sicher, dass das Zielfenster nicht als Administrator läuft – und du den Server
nicht mit niedrigeren Rechten. Starte ggf. die PowerShell als Administrator.

**Q: Wie stoppe ich alles?**
Das PowerShell-Fenster schließen oder `Strg+C` drücken. Das Skript beendet dann
sowohl den Python-Server als auch `cloudflared`.

**Q: Die Cloudflare-URL ändert sich bei jedem Start?**
Ja – das ist normal bei kostenlosen *Quick Tunnels*. Wenn du eine feste Subdomain
willst, kannst du einen benannten Tunnel via `cloudflared tunnel login` +
`cloudflared tunnel create <name>` anlegen und in `start-mcp.ps1` eintragen.

**Q: Port 8787 ist belegt?**
Ändere `$Port` in `start-mcp.ps1` und nutze den entsprechenden `--port`-Parameter.

---

## 📝 Lizenz

MIT – mach damit was du willst. Pull-Requests sind willkommen!

---

*Viel Spaß beim Steuern deines Windows-PCs mit deinen KI-Agenten! 🤖✨*
