"""
Windows MCP Server
==================
Gives AI agents full control over a Windows PC via the Model Context Protocol.
Exposes: mouse, keyboard, screenshots, screen info, clipboard, windows,
        processes, file system, and a shell command runner.

Run:  python -m windows_mcp          # stdio (for local MCP clients)
      python -m windows_mcp serve    # HTTP/SSE on port 8787 (for Cloudflare Tunnel)
"""

from __future__ import annotations

import asyncio
import base64
import io
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Optional Windows imports (degrade gracefully on non-Windows)
# ---------------------------------------------------------------------------
try:
    import pyautogui  # type: ignore
    pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort
    pyautogui.PAUSE = 0.05
except ImportError:
    pyautogui = None  # type: ignore

try:
    from PIL import ImageGrab  # type: ignore
except ImportError:
    ImageGrab = None  # type: ignore

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None  # type: ignore

try:
    import pyperclip  # type: ignore
except ImportError:
    pyperclip = None  # type: ignore

try:
    import win32gui  # type: ignore
    import win32con  # type: ignore
    import win32process  # type: ignore
except ImportError:
    win32gui = win32con = win32process = None  # type: ignore


# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
SCREENSHOT_DIR = Path(os.environ.get("MCP_SCREENSHOT_DIR", Path.home() / "Pictures" / "MCP-Screenshots"))
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
# Public directory served by the built-in static handler (for Cloudflare URLs)
PUBLIC_DIR = Path(os.environ.get("MCP_PUBLIC_DIR", SCREENSHOT_DIR / "public"))
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# MCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "windows-control",
    description="Full Windows PC control: mouse, keyboard, screenshots, windows, shell & more.",
)


# ===========================================================================
# Screenshot / vision tools
# ===========================================================================
@mcp.tool()
def take_screenshot(filename: Optional[str] = None, region: Optional[str] = None) -> str:
    """Take a screenshot of the desktop.

    Args:
        filename: Optional name (without extension). If omitted a timestamp is used.
        region: Optional "left,top,right,bottom" in pixels to crop.

    Returns:
        JSON with the saved path, public URL (if available), and image dimensions.
    """
    if ImageGrab is None:
        return "ERROR: Pillow not installed (pip install Pillow)"

    bbox = None
    if region:
        try:
            parts = [int(x.strip()) for x in region.split(",")]
            bbox = tuple(parts[:4])
        except Exception:
            return "ERROR: region must be 'left,top,right,bottom'"

    img = ImageGrab.grab(bbox=bbox, all_screens=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    name = filename or f"screenshot_{ts}"
    if not name.lower().endswith(".png"):
        name += ".png"

    # Save private copy
    private_path = SCREENSHOT_DIR / name
    img.save(private_path, "PNG")

    # Also save to public dir so Cloudflare can serve it
    public_path = PUBLIC_DIR / name
    img.save(public_path, "PNG")

    # Build public URL when tunnel is known
    tunnel = os.environ.get("MCP_TUNNEL_URL", "").rstrip("/")
    public_url = f"{tunnel}/files/{name}" if tunnel else None

    return {
        "ok": True,
        "path": str(private_path),
        "public_path": str(public_path),
        "public_url": public_url,
        "size": img.size,
        "mode": img.mode,
    }


@mcp.tool()
def screenshot_base64(region: Optional[str] = None) -> str:
    """Take a screenshot and return it as a base64 data-URI (for direct chat display)."""
    if ImageGrab is None:
        return "ERROR: Pillow not installed"
    bbox = None
    if region:
        parts = [int(x.strip()) for x in region.split(",")]
        bbox = tuple(parts[:4])
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


@mcp.tool()
def list_screenshots(limit: int = 20) -> list[dict]:
    """List recent screenshots saved locally."""
    files = sorted(SCREENSHOT_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for f in files[:limit]:
        out.append({
            "name": f.name,
            "path": str(f),
            "size_bytes": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return out


# ===========================================================================
# Mouse tools
# ===========================================================================
@mcp.tool()
def get_screen_size() -> dict:
    """Return the primary screen resolution."""
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    w, h = pyautogui.size()
    pos = pyautogui.position()
    return {"width": w, "height": h, "cursor": {"x": pos.x, "y": pos.y}}


@mcp.tool()
def get_mouse_position() -> dict:
    """Return current mouse coordinates."""
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    p = pyautogui.position()
    return {"x": p.x, "y": p.y}


@mcp.tool()
def move_mouse(x: int, y: int, duration: float = 0.2) -> dict:
    """Move the mouse to (x, y) smoothly."""
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    pyautogui.moveTo(x, y, duration=duration)
    return {"ok": True, "x": x, "y": y}


@mcp.tool()
def click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1, duration: float = 0.0) -> dict:
    """Click at (x, y). If coordinates omitted, click at current position."""
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    pyautogui.click(x=x, y=y, button=button, clicks=clicks, duration=duration)
    return {"ok": True, "x": x, "y": y, "button": button, "clicks": clicks}


@mcp.tool()
def double_click(x: Optional[int] = None, y: Optional[int] = None) -> dict:
    """Double-click at given position (or current)."""
    return click(x=x, y=y, clicks=2, button="left")


@mcp.tool()
def right_click(x: Optional[int] = None, y: Optional[int] = None) -> dict:
    return click(x=x, y=y, button="right")


@mcp.tool()
def drag_mouse(x: int, y: int, duration: float = 0.3, button: str = "left") -> dict:
    """Drag the mouse (hold button) from current position to (x,y)."""
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    pyautogui.dragTo(x, y, duration=duration, button=button)
    return {"ok": True, "to": {"x": x, "y": y}}


@mcp.tool()
def scroll(clicks: int = 3, x: Optional[int] = None, y: Optional[int] = None) -> dict:
    """Scroll mouse wheel (positive=up, negative=down)."""
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    pyautogui.scroll(clicks, x=x, y=y)
    return {"ok": True, "clicks": clicks}


# ===========================================================================
# Keyboard tools
# ===========================================================================
@mcp.tool()
def type_text(text: str, interval: float = 0.02) -> dict:
    """Type text as if from keyboard."""
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    pyautogui.write(text, interval=interval)
    return {"ok": True, "length": len(text)}


@mcp.tool()
def press_key(key: str, presses: int = 1) -> dict:
    """Press a keyboard key (e.g. 'enter', 'tab', 'esc', 'a', 'f5', 'volumeup')."""
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    pyautogui.press(key, presses=presses)
    return {"ok": True, "key": key}


@mcp.tool()
def hotkey(*keys: str) -> dict:
    """Press key combination, e.g. hotkey('ctrl','c'), hotkey('win','d')."""
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    pyautogui.hotkey(*keys)
    return {"ok": True, "keys": list(keys)}


@mcp.tool()
def key_down(key: str) -> dict:
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    pyautogui.keyDown(key)
    return {"ok": True, "key": key}


@mcp.tool()
def key_up(key: str) -> dict:
    if pyautogui is None:
        return {"error": "pyautogui not installed"}
    pyautogui.keyUp(key)
    return {"ok": True, "key": key}


# ===========================================================================
# Clipboard
# ===========================================================================
@mcp.tool()
def get_clipboard() -> str:
    """Read text from the Windows clipboard."""
    if pyperclip is None:
        return "ERROR: pyperclip not installed"
    try:
        return pyperclip.paste() or ""
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def set_clipboard(text: str) -> dict:
    """Write text to the Windows clipboard."""
    if pyperclip is None:
        return {"error": "pyperclip not installed"}
    pyperclip.copy(text)
    return {"ok": True, "length": len(text)}


# ===========================================================================
# Window management
# ===========================================================================
def _list_windows_windows() -> list[dict]:
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                rect = win32gui.GetWindowRect(hwnd)
                out.append({
                    "hwnd": hwnd,
                    "title": title,
                    "rect": {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3]},
                })
    win32gui.EnumWindows(cb, None)
    return out


@mcp.tool()
def list_windows() -> list[dict]:
    """List visible windows with handles, titles and positions."""
    if win32gui is not None:
        return _list_windows_windows()
    if psutil is not None:
        return [{"pid": p.info["pid"], "name": p.info["name"]} for p in psutil.process_iter(["pid", "name"]) if p.info["name"]]
    return []


@mcp.tool()
def focus_window(title_contains: str) -> dict:
    """Bring a window to front by substring match on its title."""
    if win32gui is None:
        return {"error": "win32gui not available (requires Windows)"}
    target = None
    def cb(hwnd, _):
        nonlocal target
        if win32gui.IsWindowVisible(hwnd) and title_contains.lower() in win32gui.GetWindowText(hwnd).lower():
            target = hwnd
    win32gui.EnumWindows(cb, None)
    if target is None:
        return {"error": f"no window matching '{title_contains}'"}
    win32gui.ShowWindow(target, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(target)
    return {"ok": True, "hwnd": target, "title": win32gui.GetWindowText(target)}


@mcp.tool()
def minimize_window(title_contains: str) -> dict:
    if win32gui is None:
        return {"error": "win32gui not available"}
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and title_contains.lower() in win32gui.GetWindowText(hwnd).lower():
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    win32gui.EnumWindows(cb, None)
    return {"ok": True}


@mcp.tool()
def close_window(title_contains: str) -> dict:
    if win32gui is None:
        return {"error": "win32gui not available"}
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and title_contains.lower() in win32gui.GetWindowText(hwnd).lower():
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    win32gui.EnumWindows(cb, None)
    return {"ok": True}


# ===========================================================================
# Process / system info
# ===========================================================================
@mcp.tool()
def list_processes(limit: int = 30) -> list[dict]:
    """List running processes sorted by CPU usage."""
    if psutil is None:
        return [{"error": "psutil not installed"}]
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            procs.append({
                "pid": info["pid"],
                "name": info["name"],
                "cpu": info["cpu_percent"] or 0.0,
                "mem_mb": round(info["memory_info"].rss / 1024 / 1024, 1) if info["memory_info"] else 0,
            })
        except Exception:
            pass
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    return procs[:limit]


@mcp.tool()
def kill_process(pid: int) -> dict:
    if psutil is None:
        return {"error": "psutil not installed"}
    try:
        psutil.Process(pid).terminate()
        return {"ok": True, "pid": pid}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def system_info() -> dict:
    """Return basic system information."""
    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "python": sys.version,
    }
    if psutil is not None:
        info.update({
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "ram_total_gb": round(psutil.virtual_memory().total / 1024**3, 2),
            "ram_used_gb": round(psutil.virtual_memory().used / 1024**3, 2),
            "disk_free_gb": round(psutil.disk_usage(".").free / 1024**3, 2),
            "uptime_sec": round(time.time() - psutil.boot_time()),
        })
    return info


@mcp.tool()
def battery() -> dict:
    """Return battery status (laptops)."""
    if psutil is None:
        return {"error": "psutil not installed"}
    try:
        b = psutil.sensors_battery()
        if b is None:
            return {"error": "no battery"}
        return {"percent": b.percent, "plugged": b.power_plugged, "secs_left": b.secsleft}
    except Exception as e:
        return {"error": str(e)}


# ===========================================================================
# Shell / file system
# ===========================================================================
@mcp.tool()
def run_command(cmd: str, timeout: int = 30, shell: bool = True, cwd: Optional[str] = None) -> dict:
    """Run a shell command and return stdout, stderr, exit code."""
    try:
        proc = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True, timeout=timeout, cwd=cwd,
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-4000:],
            "cmd": cmd,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s", "cmd": cmd}
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": cmd}


@mcp.tool()
def read_file(path: str, max_chars: int = 10000) -> dict:
    """Read a text file from disk."""
    try:
        p = Path(path).expanduser()
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            data = f.read(max_chars)
        return {"ok": True, "path": str(p), "content": data, "truncated": len(data) == max_chars}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def write_file(path: str, content: str, append: bool = False) -> dict:
    """Write text content to a file."""
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": str(p), "bytes": len(content.encode("utf-8"))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def list_dir(path: str = ".", limit: int = 200) -> list[dict]:
    """List files and folders in a directory."""
    try:
        p = Path(path).expanduser().resolve()
        out = []
        for i, entry in enumerate(sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))):
            if i >= limit:
                break
            try:
                out.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if entry.is_file() else None,
                    "modified": datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
                })
            except Exception:
                pass
        return out
    except Exception as e:
        return [{"error": str(e)}]


# ===========================================================================
# Special helpers
# ===========================================================================
@mcp.tool()
def wait(seconds: float = 1.0) -> dict:
    """Pause execution for N seconds (useful between actions)."""
    time.sleep(max(0.0, seconds))
    return {"ok": True, "waited": seconds}


@mcp.tool()
def alert(text: str, title: str = "MCP Agent") -> dict:
    """Show a Windows message box."""
    if platform.system() == "Windows":
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
        return {"ok": True}
    return {"ok": False, "note": "only supported on Windows"}


@mcp.tool()
def say(text: str) -> dict:
    """Speak the text via Windows SAPI (text-to-speech)."""
    if platform.system() == "Windows":
        import win32com.client  # type: ignore
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak(text)
        return {"ok": True}
    return {"ok": False, "note": "TTS is Windows-only"}


@mcp.tool()
def open_url(url: str) -> dict:
    """Open a URL in the default browser."""
    import webbrowser
    webbrowser.open(url)
    return {"ok": True, "url": url}


# ===========================================================================
# Entry point
# ===========================================================================
def main() -> None:
    """CLI entry point.

    No args   -> stdio transport (use with local MCP clients like Claude Desktop)
    serve     -> HTTP/SSE transport on port 8787 (for Cloudflare tunnel)
    """
    import argparse
    parser = argparse.ArgumentParser(prog="windows-mcp")
    sub = parser.add_subparsers(dest="cmd")
    srv = sub.add_parser("serve", help="Run HTTP/SSE server")
    srv.add_argument("--host", default="0.0.0.0")
    srv.add_argument("--port", type=int, default=8787)
    srv.add_argument("--public-dir", default=str(PUBLIC_DIR), help="Directory to serve at /files/")
    args = parser.parse_args()

    if args.cmd == "serve":
        # Run the MCP server with SSE/HTTP and a static file handler for screenshots.
        import uvicorn
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        from starlette.requests import Request
        from starlette.responses import FileResponse, Response, JSONResponse
        from starlette.staticfiles import StaticFiles

        sse = SseServerTransport("/mcp/messages")

        async def handle_sse(request: Request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as (read_stream, write_stream):
                await mcp.run(read_stream, write_stream, mcp.create_initialization_options())

        async def health(request: Request):
            return JSONResponse({
                "ok": True,
                "service": "windows-mcp",
                "version": __import__("windows_mcp").__version__,
                "tunnel_url": os.environ.get("MCP_TUNNEL_URL"),
                "mcp_sse": "/mcp/sse",
                "files": "/files/",
            })

        routes = [
            Route("/mcp/sse", endpoint=handle_sse),
            Mount("/mcp/messages", app=sse.handle_post_message),
            Route("/health", endpoint=health),
            Route("/", endpoint=health),
            Mount("/files", app=StaticFiles(directory=args.public_dir, html=False, check_dir=False)),
        ]
        app = Starlette(routes=routes)
        print(f"[windows-mcp] HTTP/SSE listening on http://{args.host}:{args.port}")
        print(f"[windows-mcp]   MCP SSE endpoint : /mcp/sse")
        print(f"[windows-mcp]   Static files     : /files/  (-> {args.public_dir})")
        print(f"[windows-mcp]   Public tunnel URL: {os.environ.get('MCP_TUNNEL_URL','<not set>')}")
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    else:
        # stdio transport (default)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
