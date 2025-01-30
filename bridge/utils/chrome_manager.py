import subprocess
import os
import shutil
import tempfile


class ChromeManager:
    def __init__(
            self, 
            proxy_port, 
            chrome_port, 
            # extension_path="/home/sasha/extensions/capsolver",
            extension_path=None,
            # user_data_dir="/home/sasha/chrome_profiles/mac_profile",
            user_data_dir=None,
            headless=True, 
            command=None
        ):

        self.screen_name = f"chrome_browser_{chrome_port}"
        self.temp_dir_prefix = ".com.google.Chrome."
        self.temp_dir_path = tempfile.gettempdir()
        self.extension_path = extension_path
        self.headless = headless
        
        if command is None: 
            self.command = [
                "google-chrome",
                f"--remote-debugging-port={chrome_port}",
                f"--proxy-server=127.0.0.1:{proxy_port}",
                "--no-first-run",
                "--no-default-browser-check", 
                "--disable-gpu", 
                "--password-store=basic"
            ]

            if self.extension_path: 
                self.command.append(f"--disable-extensions-except={self.extension_path}")
                self.command.append(f"--load-extension={self.extension_path}")

            if user_data_dir: 
                self.command.append(f"--user-data-dir={user_data_dir}")
            else: 
                self.command.append("--incognito")

            if headless: 
                self.command.append("--headless")
        
        else: 
            self.command = command

    def _get_chrome_user_dirs(self):
        """Get the list of Chrome user data directories in the temp directory."""
        return [
            os.path.join(self.temp_dir_path, d)
            for d in os.listdir(self.temp_dir_path)
            if d.startswith(self.temp_dir_prefix)
        ]

    def create_chrome(self):
        try:

            result = subprocess.run(['screen', '-list'], capture_output=True, text=True)
            if self.screen_name in result.stdout:
                print(f"Screen session '{self.screen_name}' already exists.")
                subprocess.run(['screen', '-S', self.screen_name, '-X', 'quit'], check=True)
                print(f"Terminated existing screen session '{self.screen_name}'")

            print(f"Creating new screen session: {self.screen_name}")
            subprocess.run(['screen', '-S', self.screen_name, '-dm', 'bash', '-c', 'cd ~ && exec bash'])
            print(f"Created new screen session: {self.screen_name}")

            env = os.environ.copy()

            # 1. Set DISPLAY if headless is False
            if not self.headless:
                subprocess.run(
                    ["screen", "-S", self.screen_name, "-X", "stuff", "export DISPLAY=:1\n"],
                    env=env,
                    check=True
                )
                print("Set DISPLAY=:1 for non-headless mode.")
            
            # 2. Run Chrome in the screen session
            subprocess.run(
                [
                    "screen", 
                    "-S", 
                    self.screen_name, 
                    "-X", 
                    "stuff", 
                    f"{' '.join(self.command)}\n"
                ],
                check=True, 
                env=env
            )
            print(f"Chrome started successfully in screen session '{self.screen_name}'!")

        except subprocess.CalledProcessError as e:
            print(f"Error during Chrome setup: {e}")

    def close_chrome(self):
        try:

            result = subprocess.run(['screen', '-list'], capture_output=True, text=True)

            # Kill from screen
            if self.screen_name in result.stdout:
                print(f"Terminating screen session '{self.screen_name}'...")
                subprocess.run(['screen', '-S', self.screen_name, '-X', 'quit'], check=True)
                print(f"Screen session '{self.screen_name}' terminated.")
            
            if "--incognito" in self.command:
                user_dirs = self._get_chrome_user_dirs()
                for user_dir in user_dirs:
                    shutil.rmtree(user_dir, ignore_errors=False)
                    print(f"Removing Chrome user data directory: {user_dir}")
            
            # Kill from process
            subprocess.run(["pkill", "-f", "google-chrome"], check=False)

        except Exception as e:
            print(f"Error during cleanup: {e}")


if __name__ == "__main__":
    manager = ChromeManager(
        proxy_port=8899, 
        chrome_port=7778, 
        # user_data_dir="/home/sasha/chrome_profiles/mac_profile", 
        headless=False, 
        command=None
    )
    manager.create_chrome()
    input("Press Enter to close Chrome...")
    manager.close_chrome()
