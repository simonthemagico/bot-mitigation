from typing import Dict, Any
import subprocess
import signal
import os
import tempfile
import traceback
from browser import create_browser_tab
from config import CHROME_PATH, previous_dir, ALLOWED_HOSTS

tasks: Dict[str, Dict[str, Any]] = {}

def handle_captcha(url: str, cid: str, port: int, task: Dict):
    try:
        tab, browser = create_browser_tab(url, cid, port)
        for _ in range(30):
            if task['status'] == 'ready':
                break
            tab.wait(1)
        if task['status'] != 'ready':
            task['status'] = 'error'
            task['value'] = 'timeout'
    except Exception as e:
        print(traceback.format_exc())
        task['status'] = 'error'
        task['value'] = str(e)
        raise e
    finally:
        tab.stop()
        browser.close_tab(tab)

def process_url(task_id: str, cid: str, proxy: str):
    tmpdirname = tempfile.mkdtemp()
    port = 9223
    while True:
        try:
            subprocess.check_output(f'lsof -i:{port}', shell=True)
            port += 1
        except:
            break
        if port > 9322:
            raise Exception('No open ports found')

    task = tasks[task_id]
    url = task['url']
    
    proxy_command = [
        'proxy',
        '--proxy-pool', proxy,
        '--port', str(port-1000),
        '--plugins', 'restrict_by_host_upstream.RestrictHostUpstream,proxy.plugin.ProxyPoolPlugin',
        '--restrict-by-host-upstream', '.*('+"|".join(ALLOWED_HOSTS)+').*',
    ]
    
    process = subprocess.Popen(proxy_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        commands = [
            CHROME_PATH,
            f'--remote-debugging-port={port}',
            f'--load-extension={previous_dir}/extensionv2',
            f'--user-data-dir={tmpdirname}',
            f'--proxy-server=http://127.0.0.1:{port-1000}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-default-apps',
        ]
        p = subprocess.Popen(commands, start_new_session=True)
        try:
            handle_captcha(url, cid, port, task)
        except Exception as e:
            print(e)
            task['status'] = 'error'
        finally:
            p.kill()
        if process.poll() is None:
            os.kill(process.pid, signal.SIGINT)
            process.communicate()
    finally:
        process.terminate()
        process.wait()
    os.system(f'rm -rf {tmpdirname}') 