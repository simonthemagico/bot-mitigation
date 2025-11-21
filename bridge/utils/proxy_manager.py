import subprocess
import time
import sys

try:
    import resource
except ImportError:  # pragma: no cover
    resource = None


class ProxyManager:
    _fd_limit_adjusted = False
    _min_fd_limit = 8192

    def __init__(self, proxy_pool, proxy_port):
        self.proxy_pool = proxy_pool
        self.port = str(proxy_port)
        self.proxy_process = None

        if resource and not ProxyManager._fd_limit_adjusted:
            try:
                soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
                desired_soft = min(max(soft, self._min_fd_limit), hard)
                if soft < desired_soft:
                    resource.setrlimit(resource.RLIMIT_NOFILE, (desired_soft, hard))
                    print(f"Raised RLIMIT_NOFILE from {soft} to {desired_soft}")
                ProxyManager._fd_limit_adjusted = True
            except (ValueError, OSError):
                # Best-effort; if we can't raise the limit we proceed anyway
                ProxyManager._fd_limit_adjusted = True

        # Use the same interpreter that is running this process, so we
        # always hit the environment where the `proxy` module is installed.
        self.command = [
            sys.executable,
            "-m",
            "proxy",
            "--proxy-pool",
            self.proxy_pool,
            "--port",
            self.port,
            "--plugins",
            "proxy.plugin.ProxyPoolPlugin",
        ]

    def start_proxy_server(self):
        # Kill any existing proxy on this port
        self.stop_proxy_server()

        print(f"Starting proxy server on port {self.port}...")
        self.proxy_process = subprocess.Popen(
            self.command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        
        # Wait a bit for proxy to start
        time.sleep(2)

        # Check if process is still running
        if self.proxy_process.poll() is None:
            print(f"Proxy server started successfully on port {self.port}")
            if self.proxy_process.stderr:
                self.proxy_process.stderr.close()
                self.proxy_process.stderr = None
        else:
            _, stderr = self.proxy_process.communicate()
            raise Exception(f"Proxy failed to start: {stderr.decode()}")

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
                if self.proxy_process.stdout:
                    self.proxy_process.stdout.close()
                if self.proxy_process.stderr:
                    self.proxy_process.stderr.close()
                self.proxy_process = None
            
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