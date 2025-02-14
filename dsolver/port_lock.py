import os
import socket
import json
import fcntl

ALLOC_FILE = os.path.join(os.path.abspath('.scratch'), 'port_alloc.json')

def ensure_alloc_file_exists():
    """Ensure that the allocation file exists."""
    os.makedirs(os.path.dirname(ALLOC_FILE), exist_ok=True)
    if not os.path.exists(ALLOC_FILE):
        with open(ALLOC_FILE, 'w') as f:
            json.dump([], f)

def is_port_free(port: int) -> bool:
    """Check if a port is free by attempting to bind a temporary socket."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False

def acquire_port(start_port: int = 9223, end_port: int = 9922):
    """
    Acquire a free debugging port and corresponding proxy port.
    
    Both ports are reserved by updating a file in the .scratch directory
    to prevent race conditions with concurrent processes.
    """
    ensure_alloc_file_exists()
    with open(ALLOC_FILE, 'r+') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                allocated = json.load(f)
            except json.decoder.JSONDecodeError:
                allocated = []
            for candidate in range(start_port, end_port + 1):
                proxy_port = candidate - 1000
                if proxy_port < 1024:
                    continue
                if candidate in allocated or proxy_port in allocated:
                    continue
                if is_port_free(candidate) and is_port_free(proxy_port):
                    allocated.append(candidate)
                    allocated.append(proxy_port)
                    f.seek(0)
                    json.dump(allocated, f)
                    f.truncate()
                    return candidate, proxy_port
            raise Exception("No free ports found")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

def release_port(debug_port: int, proxy_port: int):
    """
    Release the allocated ports so that they can be used by other tasks.
    """
    ensure_alloc_file_exists()
    with open(ALLOC_FILE, 'r+') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                allocated = json.load(f)
            except json.decoder.JSONDecodeError:
                allocated = []
            if debug_port in allocated:
                allocated.remove(debug_port)
            if proxy_port in allocated:
                allocated.remove(proxy_port)
            f.seek(0)
            json.dump(allocated, f)
            f.truncate()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
