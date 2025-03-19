import pychrome

# Connect to Chrome DevTools
browser = pychrome.Browser(url="http://127.0.0.1:7778")

# List available tabs
tabs = browser.list_tab()

# Print tab info
if tabs:
    print("✅ Connected! Available tabs:", tabs)
    tab = tabs[0]
    print("🔹 Using Tab:", tab.id)
    
    # Start the tab session
    tab.start()
    print("🟢 Tab started!")
    
    # Enable Network & Page
    tab.Network.enable()
    tab.Page.enable()
    
    # Navigate to test page
    print("🌍 Navigating to https://www.google.com")
    tab.Page.navigate(url="https://www.google.com")

else:
    print("⚠️ No tabs found!")

# Cleanup
tab.stop()
