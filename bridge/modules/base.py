from utils.chrome_manager import ChromeManager
from utils.proxy_manager import ProxyManager

import random
import socket
import os
from datetime import datetime

class BaseBypass:
    def __init__(
            self,
            proxy_pool: str,
            url: str,
            task_id: str,
            headless: bool = False,
            user_data_dir = "/Users/m1/chrome-data-dir",
            extension_path = None,
            disable_images: bool = True,
            disable_http2 : bool = False,
            profile_template_dir: str = "_template_capsolver"
        ):

        self.proxy_pool = proxy_pool
        self.url = url
        self.task_id = task_id
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.extension_path = extension_path
        self.disable_images = disable_images
        self.disable_http2 = disable_http2
        self.profile_template_dir = profile_template_dir

        self.proxy_port = None
        self.chrome_port = None

        self.proxy_server = None
        self.chrome = None

    def generate_unique_ports(self):
        max_attempts = 1000
        attempt = 0

        while attempt < max_attempts:
            proxy_port = random.randint(1024, 65535) & ~1 # even port
            chrome_port = proxy_port + 1
            if self.is_port_available(proxy_port) and self.is_port_available(chrome_port):
                return proxy_port, chrome_port

            attempt += 1

        raise RuntimeError(f"Could not find available port pair after {max_attempts} attempts")

    def is_port_available(self,port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return True
            except OSError:
                return False

    def initialize(self):

        if not self.proxy_port or not self.chrome_port:
            self.proxy_port, self.chrome_port = self.generate_unique_ports()

        self.proxy_server = ProxyManager(
            proxy_pool=self.proxy_pool,
            proxy_port=self.proxy_port
        )

        self.chrome = ChromeManager(
            proxy_port=self.proxy_port,
            chrome_port=self.chrome_port,
            headless=self.headless,
            user_data_dir=self.user_data_dir,
            extension_path=self.extension_path,
            disable_images=self.disable_images,
            disable_http2=self.disable_http2,
            profile_template_dir=self.profile_template_dir
        )

    def cleanup(self):
        if self.chrome:
            self.chrome.close_chrome()
        if self.proxy_server:
            self.proxy_server.stop_proxy_server()

    def save_page_content(self, content: str, prefix: str = "bypass"):

        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{self.task_id}_{timestamp}.html"
        filepath = os.path.join(logs_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Page content saved to '{filepath}'")

        return filepath

    def bypass(self):
        raise NotImplementedError("Each bypass module must implement this method")
