"""
InventoryPro - Auto Updater Core
Checks for updates from a GitHub repository and applies changed files silently.
No zip extraction needed — downloads individual changed files from GitHub raw content.
"""
import os
import sys
import json
import hashlib
import threading
import requests
import subprocess
from typing import Optional, Callable

# ── Configuration ────────────────────────────────────────────────────────────
# These are set from the settings page / app_settings DB
_GITHUB_REPO  = ""   # e.g. "yourname/inventorypro"
_GITHUB_TOKEN = ""   # optional, for private repos

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(APP_ROOT, "version.txt")
MANIFEST_URL_TEMPLATE = "https://raw.githubusercontent.com/{repo}/main/update_manifest.json"
VERSION_URL_TEMPLATE  = "https://raw.githubusercontent.com/{repo}/main/version.txt"
EXE_RELEASE_URL_TEMPLATE = "https://github.com/{repo}/releases/latest/download/InventoryPRO.exe"

TIMEOUT = 8


def get_local_version() -> str:
    try:
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"


def set_config(github_repo: str, github_token: str = ""):
    global _GITHUB_REPO, _GITHUB_TOKEN
    _GITHUB_REPO  = github_repo.strip()
    _GITHUB_TOKEN = github_token.strip()


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if _GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {_GITHUB_TOKEN}"
    return h


def _version_tuple(v: str):
    """Convert '1.2.3' → (1, 2, 3) for comparison."""
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except Exception:
        return (0, 0, 0)


def check_for_update() -> Optional[str]:
    """
    Returns the latest version string if an update is available, else None.
    Runs quickly — just fetches a small text file.
    """
    if not _GITHUB_REPO:
        return None
    try:
        url = VERSION_URL_TEMPLATE.format(repo=_GITHUB_REPO)
        resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        latest = resp.text.strip()
        local  = get_local_version()
        if _version_tuple(latest) > _version_tuple(local):
            return latest
        return None
    except Exception as e:
        print(f"[Updater] Version check failed: {e}")
        return None


def apply_update(
    new_version: str,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
    on_done: Optional[Callable[[bool, str], None]] = None,
):
    """
    Downloads and applies the update.
    If running as an EXE, downloads the new EXE from GitHub Releases, swaps it, and restarts.
    If running as a script, uses the update manifest to update python files.
    """
    def _run():
        is_exe = getattr(sys, 'frozen', False)
        try:
            if is_exe:
                if on_progress: on_progress("Downloading new executable...", 0, 100)
                url = EXE_RELEASE_URL_TEMPLATE.format(repo=_GITHUB_REPO)
                resp = requests.get(url, stream=True, timeout=TIMEOUT)
                
                if resp.status_code != 200:
                    if on_done: on_done(False, f"Failed to download EXE (Status {resp.status_code})")
                    return
                
                total_size = int(resp.headers.get('content-length', 0))
                current_exe = sys.executable
                new_exe = current_exe + ".new"
                old_exe = current_exe + ".old"
                
                downloaded = 0
                with open(new_exe, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0 and on_progress:
                                percent = int((downloaded / total_size) * 100)
                                on_progress("Downloading new executable...", percent, 100)
                
                if on_progress: on_progress("Installing update...", 99, 100)
                
                # Windows allows renaming a running file, but not deleting it
                if os.path.exists(old_exe):
                    os.remove(old_exe)
                os.rename(current_exe, old_exe)
                os.rename(new_exe, current_exe)
                
                if on_progress: on_progress("Restarting application...", 100, 100)
                if on_done: on_done(True, "Update installed successfully.")
                
                # Restart the app
                subprocess.Popen([current_exe])
                os._exit(0)
                
            else:
                # Script mode updating
                if on_progress: on_progress("Fetching update manifest...", 0, 1)
                url = MANIFEST_URL_TEMPLATE.format(repo=_GITHUB_REPO)
                resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
                if resp.status_code != 200:
                    if on_done: on_done(False, "Could not fetch update manifest.")
                    return

                manifest = resp.json()
                files = manifest.get("files", [])
                
                for idx, fobj in enumerate(files):
                    path = fobj["path"]
                    furl = fobj["url"]
                    if on_progress: on_progress(f"Updating {path}...", idx, len(files))
                    
                    fresp = requests.get(furl, headers=_headers(), timeout=TIMEOUT)
                    if fresp.status_code == 200:
                        local_path = os.path.join(APP_ROOT, path)
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        with open(local_path, "wb") as f:
                            f.write(fresp.content)
                
                with open(VERSION_FILE, "w") as f:
                    f.write(new_version)
                    
                if on_progress: on_progress("Restarting application...", len(files), len(files))
                if on_done: on_done(True, "Update installed successfully.")
                
                subprocess.Popen([sys.executable, sys.argv[0]])
                os._exit(0)

        except Exception as e:
            print(f"[Updater] Update failed: {e}")
            if on_done: on_done(False, f"Update failed: {e}")

    threading.Thread(target=_run, daemon=True).start()

def cleanup_old_exe():
    """Removes the .old executable if it exists after a successful update."""
    is_exe = getattr(sys, 'frozen', False)
    if is_exe:
        old_exe = sys.executable + ".old"
        if os.path.exists(old_exe):
            try:
                os.remove(old_exe)
                print("[Updater] Cleaned up old executable.")
            except Exception:
                pass

def restart_app():
    """Restart the application process."""
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable])
    else:
        python = sys.executable
        script = os.path.join(APP_ROOT, "main.py")
        subprocess.Popen([python, script])
    sys.exit(0)


def check_async(on_result: Callable[[Optional[str]], None]):
    """Check for updates in a background thread and call on_result(version_or_None)."""
    def _run():
        result = check_for_update()
        on_result(result)
    threading.Thread(target=_run, daemon=True).start()
