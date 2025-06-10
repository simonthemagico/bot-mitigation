import subprocess
import os
import signal
import shutil
import tempfile
import platform
import time
import pychrome
import requests

from .proxy_manager import ProxyManager

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
            extension_path="extensions/capsolver",
            # adblock_extension_path="extensions/ublock",
            adblock_extension_path=None,
            disable_images=True,
            user_data_dir=None,
            headless=False, 
            disable_http2=False,
            use_proxy=True,
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
        self.user_data_dir = user_data_dir
        self.disable_images = disable_images
        self.disable_http2 = disable_http2
        self.use_proxy = use_proxy

        self.proxy_port = proxy_port
        self.chrome_port = chrome_port

        # Get bridge root directory (two levels up from chrome_manager.py)
        self.bridge_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if command is None:
            self._setup_chrome_command(
                proxy_port, 
                chrome_port, 
                extension_path, 
                adblock_extension_path, 
                user_data_dir
            )
        else:
            self.command = command

    def _setup_chrome_command(
            self, 
            proxy_port, 
            chrome_port, 
            extension_path, 
            adblock_extension_path,
            user_data_dir
        ):
        """Set up Chrome command with all necessary arguments"""
        chrome_path = get_chrome_path()

        self.command = [
            chrome_path,
            f"--remote-debugging-port={chrome_port}",
            # f"--proxy-server=127.0.0.1:{proxy_port}",
            "--no-first-run",
            "--no-default-browser-check", 
            "--disable-gpu", 
            "--password-store=basic",
            # "--new-window",
        ]

        if self.use_proxy: 
            self.command.append(f"--proxy-server=127.0.0.1:{proxy_port}")
        else: 
            self.command.append("--no-proxy-server")

        # Apply image disabling settings if enabled
        if self.disable_images:
            self.command.extend([
                # Disable images to save bandwidth
                "--blink-settings=imagesEnabled=false",
                "--disable-image-loading",
                "--disable-images",
            ])

        # Handle profile directory
        if user_data_dir:
            paths = get_default_paths()
            if not os.path.isabs(user_data_dir):
                user_data_dir = os.path.join(paths['profiles'], user_data_dir)
                os.makedirs(user_data_dir, exist_ok=True)
            self.command.append(f"--user-data-dir={user_data_dir}")
        else:
            self.command.append("--incognito")

        # Add performance flags
        self.command.extend([
            "--disable-renderer-accessibility", 
            "--disable-translate",
            "--disable-infobars",
            "--disable-notifications",
            "--disable-popup-blocking",
            "--disable-save-password-bubble",
            
            # NEW: Prevent massive cache writes
            "--disk-cache-size=10485760",         # 10 MB
            "--media-cache-size=1048576",         # 1 MB
            "--disable-application-cache",
            "--disable-cache",
            "--disable-dev-shm-usage"
        ])

        # Handle extensions - always resolve relative to bridge root
        extensions = []
        for path in [
            extension_path, 
            adblock_extension_path
        ]: 
            if path:
                if not os.path.isabs(path):
                    path = os.path.join(self.bridge_root, path)
                if os.path.exists(path):
                    extensions.append(path)
                else:
                    raise FileNotFoundError(f"Extension not found: {path}")
        if extensions:
            self.command.append(f"--load-extension={','.join(extensions)}")
            self.command.append(f"--disable-extensions-except={','.join(extensions)}")

        if self.headless:
            self.command.append("--headless")

        if self.disable_http2: 
            self.command.append("--disable-http2")

    def create_chrome(self):
        """Start Chrome process"""
        try:
            env = os.environ.copy()
            if not self.headless:
                env["DISPLAY"] = ":1"

            print("Starting Chrome with command:", " ".join(self.command))  # Debugging line
            
            self.chrome_process = subprocess.Popen(
                self.command,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, 
                text=True
            )

            time.sleep(5)
            
            print("Chrome started successfully!")

            # Check if process is still running
            if self.chrome_process.poll() is not None:
                stdout, stderr = self.chrome_process.communicate()
                print("\nChrome failed to start:")
                print("Exit code:", self.chrome_process.returncode)
                print("Stdout:", stdout)
                print("Stderr:", stderr)
                raise Exception("Chrome failed to start")
                
            print("\nChrome process started with PID:", self.chrome_process.pid)
            print(f"Expected DevTools URL: http://127.0.0.1:{self.chrome_port}")

            # Check if DevTools API is reachable
            for attempt in range(5):
                try:
                    response = requests.get(f"http://127.0.0.1:{self.chrome_port}/json", timeout=5)
                    print(f"✅ Chrome DevTools API response (attempt {attempt+1}):", response.json())
                    break  # Success!
                except requests.exceptions.RequestException as e:
                    print(f"❌ DevTools API not responding (attempt {attempt+1}): {e}")
                    time.sleep(3)  # Wait before retrying


        except Exception as e:
            print(f"Error during Chrome setup: {e}")
            raise

    def close_chrome(self):
        """Clean up Chrome process and temporary files"""
        try:
            # 1) Terminate Chrome if running
            if self.chrome_process:
                self.chrome_process.terminate()
                
                timeout = 5
                start_time = time.time()

                while time.time() - start_time < timeout:
                    if self.chrome_process.poll() is not None:
                        print(f"Chrome process {self.chrome_process.pid} exited successfully.")
                        break
                    time.sleep(0.5)
                
                # If Chrome is still running, force kill
                if self.chrome_process.poll() is None:
                    print(f"Chrome process {self.chrome_process.pid} did not exit, force killing...")
                    os.kill(self.chrome_process.pid, signal.SIGKILL)
                    print(f"Chrome process {self.chrome_process.pid} forcefully terminated.")

            # 2) If we used an explicit user_data_dir, remove it
            if self.user_data_dir and os.path.exists(self.user_data_dir):
                print(f"Removing profile directory: {self.user_data_dir}")
                shutil.rmtree(self.user_data_dir, ignore_errors=True)

            # If we used incognito mode, we might not need to do anything
            # because no persistent profile folder was created.

        except ProcessLookupError:
            print(f"Chrome process {self.chrome_process.pid} already exited.")

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
    proxy_server = ProxyManager(
        proxy_pool='http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004',
        proxy_port=8899
    )
    proxy_server.start_proxy_server()

    chrome_manager = ChromeManager(
        proxy_port=8899,
        chrome_port=7778,
        headless=False,  # Disable headless for testing
        user_data_dir="sasha", 
        use_proxy=False
    )

    browser = None
    tab = None

    try:
        # Start Chrome
        chrome_manager.create_chrome()
        
        print("\n⏳ Waiting for Chrome DevTools API to be ready...")
        time.sleep(5)  # Increased wait time
        
        print("\n🔍 Checking Chrome DevTools API availability...")
        for attempt in range(5):
            try:
                response = requests.get(f"http://127.0.0.1:7778/json", timeout=5)
                print(f"✅ DevTools API response (attempt {attempt+1}):", response.json())
                break  # Success!
            except requests.exceptions.RequestException as e:
                print(f"❌ DevTools API not responding (attempt {attempt+1}): {e}")
                time.sleep(3)  # Wait before retrying

        # Connect DevTools
        browser = pychrome.Browser(url="http://127.0.0.1:7778")
        print("📌 Browser connected!")

        tabs = browser.list_tab()
        if not tabs:
            print("⚠️ No tabs found! Creating a new one...")
            tab = browser.new_tab()
        else:
            tab = tabs[0]

        tab.start()
        print("🟢 Tab is now active!")

        # Enable Network and Page
        tab.Network.enable()
        tab.Page.enable()
        
        # Test proxy
        print("🌐 Navigating to IP check...")
        tab.Page.navigate(url="https://api.ipify.org")
        time.sleep(5)

        # Test extension
        # print("🌐 Navigating to Google reCAPTCHA demo page...")
        # tab.Page.navigate(url="https://www.google.com/recaptcha/api2/demo")
        # time.sleep(8)

        # Get IP
        result = tab.Runtime.evaluate(expression="document.documentElement.outerHTML")
        print(f"🔹 Proxy IP: {result['result']['value'].strip()}")

        input("Press Enter to quit...")

    finally:
        if tab:
            tab.stop()
        if browser and tab:
            browser.close_tab(tab)
        chrome_manager.close_chrome()
        proxy_server.stop_proxy_server()

if __name__ == "__main__":
    test_chrome()