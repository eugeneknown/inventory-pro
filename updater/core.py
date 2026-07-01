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
    Downloads and applies changed files from the update manifest.
    on_progress(message, current, total)
    on_done(success, message)
    Runs in a background thread automatically.
    """
    def _run():
        try:
            # Step 1: Fetch manifest
            if on_progress: on_progress("Fetching update manifest...", 0, 1)
            url = MANIFEST_URL_TEMPLATE.format(repo=_GITHUB_REPO)
            resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
            if resp.status_code != 200:
                if on_done: on_done(False, "Could not fetch update manifest.")
                return

            manifest = resp.json()  # { "version": "1.0.1", "files": [{"path": "...", "url": "...", "sha256": "..."}] }
            files = manifest.get("files", [])
            total = len(files)

            # Step 2: Download changed files
            updated = 0
            for i, entry in enumerate(files):
                rel_path = entry["path"]            # e.g. "ui/dashboard.py"
                raw_url  = entry["url"]             # raw.githubusercontent.com URL
                expected_hash = entry.get("sha256") # optional integrity check

                if on_progress:
                    on_progress(f"Updating {rel_path}...", i, total)

                file_resp = requests.get(raw_url, headers=_headers(), timeout=30)
                if file_resp.status_code != 200:
                    print(f"[Updater] Failed to download {rel_path}, skipping.")
                    continue

                content = file_resp.content

                # Verify hash if provided
                if expected_hash:
                    actual_hash = hashlib.sha256(content).hexdigest()
                    if actual_hash != expected_hash:
                        print(f"[Updater] Hash mismatch for {rel_path}, skipping.")
                        continue

                # Write file
                full_path = os.path.join(APP_ROOT, rel_path.replace("/", os.sep))
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "wb") as f:
                    f.write(content)
                updated += 1

            # Step 3: Update local version.txt
            with open(VERSION_FILE, "w") as f:
                f.write(new_version + "\n")

            if on_progress: on_progress("Update complete!", total, total)
            if on_done: on_done(True, f"Updated {updated}/{total} files to v{new_version}.")

        except Exception as e:
            print(f"[Updater] Update failed: {e}")
            if on_done: on_done(False, f"Update failed: {e}")

    threading.Thread(target=_run, daemon=True).start()


def restart_app():
    """Restart the application process."""
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
