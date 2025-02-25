#!/usr/bin/env python3

import os
import time

def main():
    # Calculate the time cutoff (3 days ago)
    now = time.time()
    three_days_ago = now - (3 * 24 * 60 * 60)  # 3 days in seconds

    # Get the absolute path to the logs directory
    # e.g. relative to this script's directory: ../logs
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "..", "logs")
    logs_dir = os.path.abspath(logs_dir)

    if not os.path.exists(logs_dir):
        print(f"Logs directory does not exist: {logs_dir}")
        return

    print(f"Cleaning up logs older than 3 days in: {logs_dir}")

    # Loop through log files
    for filename in os.listdir(logs_dir):
        file_path = os.path.join(logs_dir, filename)

        # If it's a file (not a directory)
        if os.path.isfile(file_path):
            # Check last modification time
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < three_days_ago:
                # Delete it
                print(f"Removing old log file: {filename}")
                os.remove(file_path)

if __name__ == "__main__":
    main()
