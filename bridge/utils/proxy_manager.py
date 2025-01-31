import subprocess
import time


class ProxyManager:
    def __init__(self, proxy_pool, proxy_port):
        self.proxy_pool = proxy_pool
        self.port = str(proxy_port)
        self.proxy_process = None
        self.command = [
            "python3", "-m", "proxy",
            "--proxy-pool", self.proxy_pool,
            "--port", self.port,
            "--plugins", "proxy.plugin.ProxyPoolPlugin"
        ]

    def start_proxy_server(self):
        try:
            # Kill any existing proxy on this port
            self.stop_proxy_server()

            print(f"Starting proxy server on port {self.port}...")
            self.proxy_process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait a bit for proxy to start
            time.sleep(2)

            # Check if process is still running
            if self.proxy_process.poll() is None:
                print(f"Proxy server started successfully on port {self.port}")
            else:
                stdout, stderr = self.proxy_process.communicate()
                raise Exception(f"Proxy failed to start: {stderr.decode()}")

        except Exception as e:
            print(f"Error during proxy server setup: {e}")
            raise

    def stop_proxy_server(self):
        try:
            if self.proxy_process:
                print("Stopping proxy server...")
                # Try graceful shutdown first
                self.proxy_process.terminate()
                try:
                    self.proxy_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop
                    self.proxy_process.kill()
                    self.proxy_process.wait()
                print("Proxy server stopped")
            
            # Clean up any remaining processes on this port
            try:
                subprocess.run(
                    ["lsof", "-ti", f":{self.port}"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                subprocess.run(
                    f"kill -9 $(lsof -ti:{self.port})", 
                    shell=True, 
                    check=False
                )
            except:
                pass

        except Exception as e:
            print(f"Error during proxy server cleanup: {e}")
            raise

def test(): 
    print("=== Testing Proxy Manager ===")
    
    proxy_manager = ProxyManager(
        proxy_pool='http://user-sp0e9f6467:08yf0pO2avT_mbiJNp@dc.smartproxy.com:20004',
        proxy_port=8899
    )
    
    try:
        print("\n1. Starting proxy server...")
        proxy_manager.start_proxy_server()
        
        print("\n2. Proxy running. Testing for 10 seconds...")
        time.sleep(10)

        input('Wanna stop proxy?')
        
        print("\n3. Stopping proxy server...")
        proxy_manager.stop_proxy_server()
        
        print("\n=== Proxy Test Complete ===")
        
    except Exception as e:
        print(f"\nError during test: {e}")
    finally:
        proxy_manager.stop_proxy_server()


if __name__ == "__main__":
    test()