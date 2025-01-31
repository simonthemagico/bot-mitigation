import subprocess
import os
import shutil
import tempfile
import platform

def get_chrome_path():
    """Get the Chrome executable path based on OS"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
    elif system == "Linux":
        paths = [
            "google-chrome",
            "google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable"
        ]
    else:
        raise OSError(f"Unsupported operating system: {system}")

    # Try each path
    for path in paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            return expanded_path
        if system == "Linux" and shutil.which(path):
            return path
            
    raise FileNotFoundError(f"Chrome not found in standard locations for {system}")

def get_default_paths():
    """Get default paths for macOS Chrome profiles and extensions"""
    home = os.path.expanduser("~")
    return {
        'profiles': os.path.join(home, 'Library/Application Support/Google/Chrome'),
        'extensions': os.path.join(home, 'Library/Application Support/Google/Chrome/Extensions')
    }

class ChromeManager:
    def __init__(
            self, 
            proxy_port, 
            chrome_port, 
            extension_path=None,
            user_data_dir=None,
            headless=True, 
            command=None
        ):
        """Initialize Chrome manager
        
        Args:
            proxy_port: Port number for proxy
            chrome_port: Port for Chrome debugging
            extension_path: Path to Chrome extension
            user_data_dir: Chrome profile directory
            headless: Run in headless mode
            command: Custom Chrome command
        """
        self.temp_dir_prefix = ".com.google.Chrome."
        self.temp_dir_path = tempfile.gettempdir()
        self.headless = headless
        self.chrome_process = None

        if command is None:
            self._setup_chrome_command(proxy_port, chrome_port, extension_path, user_data_dir)
        else:
            self.command = command

    def _setup_chrome_command(self, proxy_port, chrome_port, extension_path, user_data_dir):
        """Set up Chrome command with all necessary arguments"""
        chrome_path = get_chrome_path()
        self.command = [
            chrome_path,
            f"--remote-debugging-port={chrome_port}",
            f"--proxy-server=127.0.0.1:{proxy_port}",
            "--no-first-run",
            "--no-default-browser-check", 
            "--disable-gpu", 
            "--password-store=basic"
        ]

        # Handle profile directory
        if user_data_dir:
            paths = get_default_paths()
            if not os.path.isabs(user_data_dir):
                user_data_dir = os.path.join(paths['profiles'], user_data_dir)
                os.makedirs(user_data_dir, exist_ok=True)
            self.command.append(f"--user-data-dir={user_data_dir}")
        else:
            self.command.append("--incognito")

        # Handle extension
        if extension_path:
            if not os.path.isabs(extension_path):
                extension_path = os.path.abspath(extension_path)
            if os.path.exists(extension_path):
                self.command.extend([
                    f"--load-extension={extension_path}",
                    f"--disable-extensions-except={extension_path}"
                ])
            else:
                raise FileNotFoundError(f"Extension not found: {extension_path}")

        if self.headless:
            self.command.append("--headless")

    def create_chrome(self):
        """Start Chrome process"""
        try:
            env = os.environ.copy()
            if not self.headless:
                env["DISPLAY"] = ":1"
            
            self.chrome_process = subprocess.Popen(
                self.command,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("Chrome started successfully!")

        except Exception as e:
            print(f"Error during Chrome setup: {e}")
            raise

    def close_chrome(self):
        """Clean up Chrome process and temporary files"""
        try:
            if self.chrome_process:
                self.chrome_process.terminate()
                self.chrome_process.wait(timeout=5)

            if "--incognito" in self.command:
                for user_dir in self._get_chrome_user_dirs():
                    shutil.rmtree(user_dir, ignore_errors=True)
            
            subprocess.run(["pkill", "-f", "google-chrome"], check=False)

        except Exception as e:
            print(f"Error during cleanup: {e}")
            raise

    def _get_chrome_user_dirs(self):
        """Get Chrome temporary user directories"""
        return [
            os.path.join(self.temp_dir_path, d)
            for d in os.listdir(self.temp_dir_path)
            if d.startswith(self.temp_dir_prefix)
        ]

def test_chrome():
    """Test Chrome manager with proxy"""
    chrome_manager = ChromeManager(
        proxy_port=8899,
        chrome_port=7778,
        headless=False,
        user_data_dir="test_profile"
    )

    browser = None
    tab = None
    
    try:
        # Start Chrome
        chrome_manager.create_chrome()
        time.sleep(2)
        
        # Connect DevTools
        browser = pychrome.Browser(url="http://localhost:7778")
        tab = browser.list_tab()[0] if browser.list_tab() else browser.new_tab()
        tab.start()
        
        # Enable domains
        tab.Network.enable()
        tab.Page.enable()
        
        # Test proxy
        tab.Page.navigate(url="https://api.ipify.org")
        time.sleep(5)
        
        # Get IP
        result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
        print(f"Proxy IP: {result['result']['value'].strip()}")
        
        input("Press Enter to quit...")
        
    finally:
        # Cleanup
        if tab:
            tab.stop()
        if browser and tab:
            browser.close_tab(tab)
        chrome_manager.close_chrome()

if __name__ == "__main__":
    test_chrome()