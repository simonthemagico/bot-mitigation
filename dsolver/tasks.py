from typing import Dict
import subprocess
import signal
import os
import tempfile
import traceback
from browser import create_browser_tab
from config import CHROME_PATH, previous_dir, ALLOWED_HOSTS
from port_lock import acquire_port, release_port


def handle_captcha(url: str, cid: str, port: int, task: Dict):
    task_id = task['task_id']
    try:
        print(f"Starting captcha handling for URL: {url}")
        tab, browser = create_browser_tab(url, cid, port)
        
        for attempt in range(30):
            if task['status'] == 'ready':
                print("Task completed successfully")
                break
            tab.wait(1)
            if (attempt + 1) % 5 == 0:
                print(f"Waiting for task completion... Attempt {attempt + 1}/30")
                
        if task['status'] != 'ready':
            print("Task timed out")
            task['status'] = 'error'
            task['value'] = 'timeout'
    except Exception as e:
        print(f"Error handling captcha: {str(e)}")
        print(traceback.format_exc())
        task['status'] = 'error'
        task['value'] = str(e)
        raise e
    finally:
        # Clean up browser resources
        print("Cleaning up browser tab")
        tab.stop()
        browser.close_tab(tab)

def process_url(proxy: str, task: Dict):
    cid = task['cid']
    task_id = task['task_id']
    print(f"Starting URL processing for task {task_id}")
    print(f"Using proxy: {proxy}")
    
    tmpdirname = tempfile.mkdtemp()
    print(f"Created temporary directory: {tmpdirname}")
    
    port, proxy_port = None, None
    proxy_proc = None
    chrome_proc = None
    
    try:
        port, proxy_port = acquire_port()
        print(f"Allocated debugging port: {port} and proxy port: {proxy_port}")
        
        proxy_command = [
            'proxy',
            '--proxy-pool', proxy,
            '--port', str(proxy_port),
            '--plugins', 'restrict_by_host_upstream.RestrictHostUpstream,proxy.plugin.ProxyPoolPlugin',
            '--restrict-by-host-upstream', '.*(' + "|".join(ALLOWED_HOSTS) + ').*',
        ]
        
        print("Starting proxy process")
        proxy_proc = subprocess.Popen(proxy_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        commands = [
            CHROME_PATH,
            f'--remote-debugging-port={port}',
            f'--load-extension={previous_dir}/extensionv2',
            f'--disable-extensions-except={previous_dir}/extensionv2',
            f'--user-data-dir={tmpdirname}',
            f'--proxy-server=http://127.0.0.1:{proxy_port}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-default-apps',
        ]
        print("Starting Chrome process")
        chrome_proc = subprocess.Popen(commands, start_new_session=True)
        
        try:
            handle_captcha(task['url'], cid, port, task)
        except Exception as e:
            print(f"Error during captcha handling: {str(e)}")
            print(traceback.format_exc())
            task['status'] = 'error'
        finally:
            print("Terminating Chrome process")
            chrome_proc.kill()
            
        if proxy_proc and proxy_proc.poll() is None:
            print("Terminating proxy process")
            os.kill(proxy_proc.pid, signal.SIGINT)
            proxy_proc.communicate()
    finally:
        print("Cleaning up processes")
        if proxy_proc:
            try:
                proxy_proc.terminate()
            except Exception:
                pass
            try:
                proxy_proc.wait()
            except Exception:
                pass
        release_port(port, proxy_port)
        print(f"Removing temporary directory: {tmpdirname}")
        os.system(f'rm -rf {tmpdirname}') 