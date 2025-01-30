import subprocess
import time


class ProxyManager:
    def __init__(self, proxy_pool, proxy_port):
        self.proxy_pool = proxy_pool
        self.screen_name = f"proxy_server_{proxy_port}"
        self.port = str(proxy_port)
        self.command = [
            "python3", "-m", "proxy",
            "--proxy-pool", self.proxy_pool,
            "--port", self.port,
            "--plugins", "proxy.plugin.ProxyPoolPlugin"
        ]

    def start_proxy_server(self):
        try:
            result = subprocess.run(['screen', '-list'], capture_output=True, text=True)
            if self.screen_name in result.stdout:
                print(f"Screen session '{self.screen_name}' already exists.")
                subprocess.run(['screen', '-S', self.screen_name, '-X', 'quit'], check=True)
                print(f"Terminated existing screen session '{self.screen_name}'")

            time.sleep(2)

            print(f"Creating new screen session: {self.screen_name}")
            subprocess.run(['screen', '-S', self.screen_name, '-dm', 'bash', '-c', 'cd ~ && exec bash'])
            print(f"Created new screen session: {self.screen_name}")

            time.sleep(2)
            print("Waiting for screen session to start...")

            subprocess.run(
                ["screen", "-S", self.screen_name, "-X", "stuff", f"{' '.join(self.command)}\n"],
                check=True
            )
            print(f"Command sent to screen session '{self.screen_name}'")

        except subprocess.CalledProcessError as e:
            print(f"Error during proxy server setup: {e}")

    def stop_proxy_server(self):
        try:
            result = subprocess.run(['screen', '-list'], capture_output=True, text=True)
            if self.screen_name in result.stdout:
                print(f"Terminating screen session '{self.screen_name}'...")
                subprocess.run(['screen', '-S', self.screen_name, '-X', 'quit'], check=True)
                print(f"Screen session '{self.screen_name}' terminated.")
            else:
                print(f"Screen session '{self.screen_name}' does not exist.")

        except subprocess.CalledProcessError as e:
            print(f"Error during proxy server closure: {e}")

if __name__ == "__main__":
    manager = ProxyManager(proxy_pool='http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004', proxy_port=8899)
    manager.start_proxy_server()
    input("Press Enter to close Proxy server...")
    manager.stop_proxy_server()