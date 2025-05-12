#!/usr/bin/env python3

import os
import time
import shutil
from datetime import datetime

PROFILE_PREFIXES = ("sasha_", "andrew_")
PROFILE_AGE_DAYS = 1
LOG_AGE_DAYS = 1

freed_bytes = 0  # Track total space freed

def log(msg): 
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def get_size(path):
    """Get total size of a file or directory in bytes."""
    total = 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            try:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
            except FileNotFoundError:
                continue
    return total

def remove_if_old(path: str, cutoff: float) -> bool:
    """Delete directory if it's older than cutoff."""
    global freed_bytes
    if not os.path.isdir(path):
        return False
    try:
        mtime = os.path.getmtime(path)
        if mtime < cutoff:
            size = get_size(path)
            log(f"🗑️ Removing directory: {path} ({size / 1e9:.2f} GB)")
            shutil.rmtree(path, ignore_errors=True)
            freed_bytes += size
            return True
    except Exception as e:
        log(f"⚠️ Failed to check/remove {path}: {e}")
    return False

def remove_all_cache(cache_base):
    """Aggressively remove all Chrome cache folders to reclaim space."""
    global freed_bytes
    log(f"🧹 Force-clearing Chrome cache folders in {cache_base}...")
    if not os.path.isdir(cache_base):
        return
    for name in os.listdir(cache_base):
        path = os.path.join(cache_base, name)
        if os.path.isdir(path):
            try:
                size = get_size(path)
                shutil.rmtree(path, ignore_errors=True)
                freed_bytes += size
                log(f"   🔥 Removed {path} ({size / 1e9:.2f} GB)")
            except Exception as e:
                log(f"⚠️ Failed to remove cache {path}: {e}")

def cleanup_chrome_profiles():
    now = time.time()
    cutoff = now - (PROFILE_AGE_DAYS * 86400)

    profiles_base = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    caches_base = os.path.expanduser("~/Library/Caches/Google/Chrome")

    log(f"🔍 Looking for Chrome profiles older than {PROFILE_AGE_DAYS} days...")

    if not os.path.isdir(profiles_base):
        log(f"⚠️ Chrome profile base directory not found: {profiles_base}")
        return

    for name in os.listdir(profiles_base):
        if not name.startswith(PROFILE_PREFIXES):
            continue

        profile_path = os.path.join(profiles_base, name)
        cache_path = os.path.join(caches_base, name)

        removed = remove_if_old(profile_path, cutoff)
        if removed:
            remove_if_old(cache_path, cutoff)

    # Clear remaining cache folders
    remove_all_cache(caches_base)

def cleanup_code_sign_clones():
    log("🔍 Scanning for Chrome code_sign_clone junk...")
    base = "/private/var/folders"
    for root, dirs, files in os.walk(base):
        for d in dirs:
            if d == "com.google.Chrome.code_sign_clone":
                full_path = os.path.join(root, d)
                try:
                    size = get_size(full_path)
                    log(f"🗑️ Removing clone: {full_path} ({size / 1e9:.2f} GB)")
                    shutil.rmtree(full_path, ignore_errors=True)
                    global freed_bytes
                    freed_bytes += size
                except Exception as e:
                    log(f"⚠️ Failed to remove {full_path}: {e}")

def cleanup_logs():
    now = time.time()
    cutoff = now - (LOG_AGE_DAYS * 86400)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.abspath(os.path.join(script_dir, "..", "logs"))

    log(f"🔍 Looking for logs older than {LOG_AGE_DAYS} days in {logs_dir}")

    if not os.path.isdir(logs_dir):
        log(f"⚠️ Logs directory not found: {logs_dir}")
        return

    for filename in os.listdir(logs_dir):
        file_path = os.path.join(logs_dir, filename)
        if os.path.isfile(file_path):
            try:
                mtime = os.path.getmtime(file_path)
                if mtime < cutoff:
                    size = os.path.getsize(file_path)
                    log(f"🗑️ Removing log file: {file_path} ({size / 1e6:.2f} MB)")
                    os.remove(file_path)
                    global freed_bytes
                    freed_bytes += size
            except Exception as e:
                log(f"⚠️ Failed to check/remove log file {file_path}: {e}")

def main():
    log("🚀 === START CLEANUP ===")
    cleanup_chrome_profiles()
    cleanup_code_sign_clones()
    cleanup_logs()
    log(f"✅ Total space freed: {freed_bytes / 1e9:.2f} GB")
    log("✅ === DONE ===")

if __name__ == "__main__":
    main()
