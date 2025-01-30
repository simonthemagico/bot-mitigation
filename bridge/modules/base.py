from utils.chrome_manager import ChromeManager
from utils.proxy_manager import ProxyManager

import random
import socket

class BaseBypass:
    def __init__(self, proxy_pool: str, url: str, headless: bool = True):
        self.proxy_pool = proxy_pool
        self.url = url
        self.headless = headless
        self.proxy_port = None
        self.chrome_port = None
        
    def generate_unique_ports(self):
        _safety_count = 0
        while True:
            proxy_port = random.randint(1024, 65535) & ~1 # even port
            chrome_port = proxy_port + 1
            if self.is_port_available(proxy_port) and self.is_port_available(chrome_port):
                return proxy_port, chrome_port# Move your port generation logic here
            _safety_count += 1
            if _safety_count > 50000: 
                raise Exception
    
    def is_port_available(self,port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return True
            except OSError:
                return False
        
    def bypass(self):
        raise NotImplementedError("Each bypass module must implement this method")