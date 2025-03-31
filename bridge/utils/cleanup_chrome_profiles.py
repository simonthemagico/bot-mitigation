#!/usr/bin/env python3

import os
import time
import shutil

def main():
    # Time threshold (3 days ago, in seconds)
    now = time.time()
    three_days_ago = now - (3 * 24 * 60 * 60)

    # This is where Chrome profiles typically are on macOS
    chrome_profiles_dir = os.path.expanduser(
        "~/Library/Application Support/Google/Chrome"
    )

    print(f"Scanning for 'sasha_' or 'andrew_' profiles older than 3 days in {chrome_profiles_dir}...")

    if not os.path.isdir(chrome_profiles_dir):
        print("Chrome directory not found, nothing to do.")
        return

    for name in os.listdir(chrome_profiles_dir):
        # We're looking for folder names starting with "sasha_"
        if not name.startswith("sasha_") and not name.startswith("andrew_"):
            continue

        full_path = os.path.join(chrome_profiles_dir, name)
        if os.path.isdir(full_path):
            # Check last modification time
            mtime = os.path.getmtime(full_path)
            if mtime < three_days_ago:
                print(f"Removing old ephemeral profile: {full_path}")
                shutil.rmtree(full_path, ignore_errors=True)

if __name__ == "__main__":
    main()
