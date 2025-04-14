#!/usr/bin/env python3

import os
import time
import shutil

PROFILE_PREFIXES = ("sasha_", "andrew_")
AGE_THRESHOLD_DAYS = 2

def remove_if_old(path: str, cutoff: float):
    if not os.path.isdir(path):
        return False

    mtime = os.path.getmtime(path)
    if mtime < cutoff:
        print(f"Removing: {path}")
        shutil.rmtree(path, ignore_errors=True)
        return True
    return False

def main():
    now = time.time()
    cutoff = now - (AGE_THRESHOLD_DAYS * 24 * 60 * 60)

    profiles_base = "/System/Volumes/Data/Users/administrator/Library/Application Support/Google/Chrome"
    caches_base = "/System/Volumes/Data/Users/administrator/Library/Caches/Google/Chrome"

    print(f"Scanning for Chrome profiles older than {AGE_THRESHOLD_DAYS} days...")

    if not os.path.isdir(profiles_base):
        print("Chrome profiles directory not found.")
        return

    for name in os.listdir(profiles_base):
        if not name.startswith(PROFILE_PREFIXES):
            continue

        profile_path = os.path.join(profiles_base, name)
        cache_path = os.path.join(caches_base, name)

        removed_profile = remove_if_old(profile_path, cutoff)
        if removed_profile:
            remove_if_old(cache_path, cutoff)

if __name__ == "__main__":
    main()
