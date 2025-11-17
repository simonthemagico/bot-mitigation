# Chrome Extension Setup Guide

## Overview

This document explains how to configure Chrome extensions (like Capsolver) for the bot-mitigation bypass scripts.

## Problem: Why `--load-extension` Doesn't Work on Fresh Profiles

Chrome 137+ silently ignores the `--load-extension` flag for **unpacked extensions on brand new profiles** for security reasons. The extension will only load if:

1. The profile has **Developer mode** enabled in `chrome://extensions`
2. The extension has been loaded at least once in that profile

## Solution: Template Profile Cloning

Instead of creating a completely fresh profile for each task (which would require manual setup every time), we use a **template profile** that gets cloned for each automation run.

### How It Works

1. You create and configure a **template profile** once (manually)
2. The template has:
   - Developer mode enabled
   - Capsolver extension loaded and configured
   - Any other settings/extensions you need
3. Each time your script runs, it **clones** the template to a fresh profile with a unique name (e.g., `google_search_{task_id}`)
4. The cloned profile inherits all settings from the template
5. After the task completes, the cloned profile is deleted (cleanup)
6. Next run creates a new clone (fresh fingerprint, but with extension working)

## Initial Setup (One-Time)

### Step 1: Create the Template Profile

Launch Chrome with the template profile path (no extension flag yet):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="/Users/m1/Library/Application Support/Google/Chrome/_template_capsolver"
```

### Step 2: Enable Developer Mode and Load Extension

In the Chrome window that opens:

1. Navigate to `chrome://extensions`
2. Toggle **Developer mode** ON (top-right corner)
3. Click **"Load unpacked"**
4. Select the extension directory:
   ```
   /Users/m1/bot-mitigation/bridge/extensions/pgojnojmmhpofjgdmaebadhbocahppod/1.17.0_0
   ```
5. Verify "Captcha Solver: Auto captcha solving service" appears in the list
6. Configure any extension settings (API keys, timeouts, etc.)
7. Close Chrome

### Step 3: Verify the Template Works

Test that `--load-extension` now works with the template:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="/Users/m1/Library/Application Support/Google/Chrome/_template_capsolver" \
  --load-extension="/Users/m1/bot-mitigation/bridge/extensions/pgojnojmmhpofjgdmaebadhbocahppod/1.17.0_0"
```

Open `chrome://extensions` and confirm the extension is loaded.

## Updating the Template Profile

Whenever you need to change extension settings, add new extensions, or modify Chrome preferences:

1. **Launch the template profile**:
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --user-data-dir="/Users/m1/Library/Application Support/Google/Chrome/_template_capsolver" \
     --load-extension="/Users/m1/bot-mitigation/bridge/extensions/pgojnojmmhpofjgdmaebadhbocahppod/1.17.0_0"
   ```

2. **Make your changes**:
   - Update Capsolver API keys
   - Configure extension timeouts
   - Install additional extensions
   - Change Chrome preferences

3. **Close Chrome**

4. **All future automation runs** will inherit these updated settings

## How the Python Script Uses This

The `ChromeManager` class automatically handles template cloning:

```python
# In ChromeManager._setup_chrome_command():

template_profile = os.path.join(paths['profiles'], "_template_capsolver")
if os.path.exists(template_profile) and not os.path.exists(user_data_dir):
    print(f"Cloning template profile from {template_profile} to {user_data_dir}")
    shutil.copytree(template_profile, user_data_dir, dirs_exist_ok=True)
```

When you run your script:

1. `GoogleSearchBypass` creates a unique profile name: `google_search_{task_id}`
2. `ChromeManager` checks if `_template_capsolver` exists
3. If yes, it clones the template to the new profile directory
4. Chrome launches with the cloned profile + `--load-extension` flag
5. Extension loads successfully (because Developer mode is inherited from template)
6. After cleanup, the task profile is deleted

## Extension Directory Structure

The Capsolver extension is stored at:

```
/Users/m1/bot-mitigation/bridge/extensions/
└── pgojnojmmhpofjgdmaebadhbocahppod/
    └── 1.17.0_0/
        ├── manifest.json
        ├── background.js
        ├── icons/
        └── ...
```

**Important**: Chrome's `--load-extension` flag must point to the **version directory** (`1.17.0_0`), which directly contains `manifest.json`, not the parent ID folder.

## What Gets Inherited from Template

When a profile is cloned from the template, it inherits:

- ✅ Developer mode enabled state
- ✅ Extension configurations (API keys, settings)
- ✅ Other installed extensions
- ✅ Chrome preferences (stored in `Preferences` file)
- ✅ Bookmarks, history (if any)
- ✅ Cookies and local storage (if you want seed data)

## What Doesn't Get Inherited

- ❌ Active browser sessions (each clone starts fresh)
- ❌ Cached data (if `--disable-cache` is used in launch flags)

## Fingerprinting Considerations

Using a template profile for cloning provides a good balance:

- **Fresh profile per task**: Each run gets a unique profile directory name
- **Consistent baseline**: All runs start from the same "golden image"
- **Automatic cleanup**: Per-task profiles are deleted after use
- **No cross-contamination**: Each task is isolated

To minimize fingerprinting:
- Keep the template minimal (only essential extensions/settings)
- Avoid storing persistent cookies in the template
- Use unique `task_id` values to ensure profile directories don't collide

## Troubleshooting

### Extension doesn't appear in `chrome://extensions`

1. Verify Developer mode is enabled in the template:
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --user-data-dir="/Users/m1/Library/Application Support/Google/Chrome/_template_capsolver"
   ```
   Check `chrome://extensions` and ensure the toggle is ON.

2. Verify the extension path is correct:
   ```bash
   ls "/Users/m1/bot-mitigation/bridge/extensions/pgojnojmmhpofjgdmaebadhbocahppod/1.17.0_0/manifest.json"
   ```
   This file must exist.

3. Check Chrome version:
   - Chrome 137+ has restrictions on `--load-extension`
   - The template cloning approach works around this

### Extension loads but doesn't work

1. Check extension configuration in the template profile
2. Verify API keys are set correctly
3. Check extension console logs:
   - Go to `chrome://extensions`
   - Click "Inspect views: background page" or "service worker"
   - Look for errors in the console

### Template profile not being cloned

Check that the template exists:
```bash
ls -la "/Users/m1/Library/Application Support/Google/Chrome/_template_capsolver"
```

If missing, re-run the Initial Setup steps.

## Related Files

- `bridge/utils/chrome_manager.py` - Contains template cloning logic
- `bridge/modules/google_search.py` - Example usage with `GoogleSearchBypass`
- `bridge/extensions/pgojnojmmhpofjgdmaebadhbocahppod/1.17.0_0/` - Capsolver extension directory

## Summary

1. **One-time**: Create and configure `_template_capsolver` profile manually
2. **Every run**: Script clones template → fresh profile with extension working
3. **After cleanup**: Task profile deleted, template preserved
4. **To update settings**: Launch template manually, make changes, close Chrome

